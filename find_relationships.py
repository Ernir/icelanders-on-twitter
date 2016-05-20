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
        if looks_icelandic(tweet.user.location) and tweet.user.screen_name not in known_users:
            known_users.append(tweet.user.screen_name)
    return known_users


def create_new_users(api, relationships, screen_names, verbose=False):
    """
    Adds the usernames
    """
    for name in screen_names:
        if name not in relationships:
            user = api.get_user(screen_name=name)
            if looks_icelandic(user.location):
                if verbose:
                    print("Creating user {0}".format(name))
                    relationships[name] = []
    return relationships


def discover_followers(api, relationships, screen_name):
    """
    Uses the given Tweepy API object instance to find the followers of the user with the given screen_name.
    Updates and returns the given "relationships" dict.
    """
    try:
        for user in tweepy.Cursor(api.followers, screen_name=screen_name).items():
            if looks_icelandic(user.location):
                relationships = create_new_users(api, relationships, [user.screen_name])
                relationships[screen_name].append(user.screen_name)
    except tweepy.error.TweepError as error:
        print(str(error) + ", ignored")
        pass  # The API tends to emit the response "buffering", which Tweepy does not understand. Blissfully ignoring!
    return relationships


def looks_icelandic(location_string):
    """
    Returns True if the given string is something that could be taken to mean "Iceland", False otherwise.
    """
    return any(loc in location_string for loc in ["Iceland", "Ísland", "Island", "iceland", "ísland", "island"])


def main():
    # Some hard-coded variables that probably should be parameters
    json_filename = "relationships.json"
    verbose = True
    time_limit = 60*60*2

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
    icelandic_names = discover_icelanders(api, list(relationships.keys()))
    if verbose:
        print("Creating new users")
    relationships = create_new_users(api, relationships, icelandic_names, True)

    # Find users whose follower data we still haven't stored, and remedy the situation
    without_followers = [name for name in relationships.keys() if len(relationships[name]) == 0]
    for name in without_followers:
        if verbose:
            print("Looking for followers for {0}".format(name))
        relationships = discover_followers(api, relationships, name)
        # Store follower data on the fly
        with open(json_filename, "w") as relationship_file:
            json.dump(relationships, relationship_file, sort_keys=True, indent=4)

        print("Time elapsed: {0}".format(time()-start_time))
        if time() - start_time > time_limit:
            break


if __name__ == '__main__':
    main()
