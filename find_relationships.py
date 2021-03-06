from pprint import pprint

import os
import json
from time import time
import tweepy


def get_tweepy_instance():
    """
    Reads credentials from environment variables and returns a Tweepy instance.
    """
    consumer_key = os.environ.get("ERNIRNET_TWITTER_APP_ID")
    consumer_secret = os.environ.get("ERNIRNET_TWITTER_APP_SECRET")
    access_token = os.environ.get("ERNIRNET_TWITTER_APP_ACCESS_TOKEN")
    access_secret = os.environ.get("ERNIRNET_TWITTER_APP_ACCESS_TOKEN_SECRET")

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.secure = True
    auth.set_access_token(access_token, access_secret)

    return tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


def discover_icelanders(api, known_users):
    """
    Searches for tweets in Iceland, and stores those users whose location is also assocated with Iceland.
    Updates the given list of known_users.
    """
    iceland_place_id = "c3932d3da7922986"  # Predefined by Twitter
    tweets = api.search(q="place:{0}".format(iceland_place_id), count=100)
    for tweet in tweets:
        if looks_icelandic(tweet.user.location) and tweet.user.id not in known_users:
            known_users.append(tweet.user.id)
    return known_users


def create_new_users(api, relationships, user_ids, verbose=False):
    """
    Adds the given user ids to the relationships dictionary if they are Icelanders.
    """
    known_foreigners = get_foreigners()

    curated_ids = [id for id in user_ids if id not in relationships and id not in known_foreigners]

    i = 0
    page_size = 100
    cache_hits = len(user_ids) - len(curated_ids)
    users_created = 0
    foreigners = 0

    while i < len(curated_ids):
        id_subset = curated_ids[i:i+page_size]
        if verbose:
            print("Creating {} users".format(len(id_subset)))
        try:
            users_list = api.lookup_users(user_ids=id_subset)
            i += page_size
            for user in users_list:
                user_id = str(user.id)
                if looks_icelandic(user.location):
                    users_created += 1
                    associate_id_with_name(user_id, user.screen_name)
                    relationships[user_id] = []
                else:
                    store_foreigner(user_id)
                    foreigners += 1
        except tweepy.error.TweepError as error:
            print(str(error) + ", retrying")
    if verbose:
        print("{0} cache hits, {1} foreigners found, {2} new users created".format(
                cache_hits, foreigners, users_created
        ))
    return relationships


def associate_id_with_name(user_id, user_name):
    """
    Stores an association between a given user id and an user name.
    """
    json_filename = "ids_to_names.json"
    with open(json_filename) as association_file:
        associations = json.load(association_file)
    associations[user_id] = user_name
    with open(json_filename, "w") as association_file:
        json.dump(associations, association_file, indent=4)


def get_foreigners():
    """
    Returns a set of all currently recorded non-Icelanders
    """
    json_filename = "foreigners.json"
    with open(json_filename) as foreigners_file:
        foreigners = json.load(foreigners_file)
    return set(foreigners["foreigners"])


def store_foreigner(user_id):
    """
    Stores the given user ID in a file, so it can be skipped later on
    """
    json_filename = "foreigners.json"
    with open(json_filename) as foreigners_file:
        foreigners = json.load(foreigners_file)
    foreigners["foreigners"].append(int(user_id))
    with open(json_filename, "w") as foreigners_file:
        json.dump(foreigners, foreigners_file, indent=4)


def discover_followers(api, relationships, user_id, verbose=False):
    """
    Uses the given Tweepy API object instance to find the followers of the user with the given user_id.
    Updates and returns the given "relationships" dict.
    """
    new_relationships = []
    try:
        for many_users in tweepy.Cursor(api.followers_ids, user_id=user_id).pages():
            relationships = create_new_users(api, relationships, many_users, verbose=verbose)
            new_relationships.extend(many_users)
    except tweepy.error.TweepError as error:
        print(str(error) + ", ignored")
        pass  # The API tends to emit the response "buffering", which Tweepy does not understand. Blissfully ignoring!
    relationships[str(user_id)] = new_relationships
    return relationships


def looks_icelandic(location_string):
    """
    Returns True if the given string is something that could be taken to mean "Iceland", False otherwise.
    """
    return any(loc in location_string for loc in ["Iceland", "Ísland", "Island", "iceland", "ísland", "island"])


def main():
    # Some hard-coded variables that probably should be parameters
    json_filename = "relationships_by_id.json"
    verbose = True
    time_limit = 0 #60 * 60 * 16

    start_time = time()

    # Read all the connections we have already discovered:
    with open(json_filename) as relationship_file:
        if verbose:
            print("Reading previously recorded relationships")
        relationships = json.load(relationship_file)

    # Look for users we've never seen before, and record them
    api = get_tweepy_instance()
    if verbose:
        print("Searching for tweets in Iceland")
    icelanders = discover_icelanders(api, list(relationships.keys()))

    relationships = create_new_users(api, relationships, icelanders, True)

    # Find users whose follower data we still haven't stored, and remedy the situation
    without_followers = [user_id for user_id in relationships.keys() if len(relationships[user_id]) == 0]
    for user_id in without_followers:
        if verbose:
            print("Looking for followers for {0}".format(user_id))
        relationships = discover_followers(api, relationships, user_id, verbose)

        print("Time elapsed: {0}".format(time() - start_time))
        if time() - start_time > time_limit:
            break
    # Store the new data
    with open(json_filename, "w") as relationship_file:
        json.dump(relationships, relationship_file, indent=4)


if __name__ == '__main__':
    main()
