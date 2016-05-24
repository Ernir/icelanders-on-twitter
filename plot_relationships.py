import json
import functools
from graphviz import Digraph


def main():
    """
    Plots the relationships defined by the JSON files below using Graphviz.
    """

    # Read the raw data
    relationship_filename = "relationships_by_id.json"
    name_map_filename = "ids_to_names.json"

    with open(relationship_filename) as relationship_file:
        relationships = json.load(relationship_file)

    with open(name_map_filename) as name_map_file:
        name_map = json.load(name_map_file)

    # Create nodes out of Twitter users, and directed edges representing follows.
    # Those users with very few followers (defined by importance_limit) are ignored.
    importance_limit = 10
    nodes = []
    edges = []
    for user, followers in relationships.items():
        if user in name_map and len(followers) > importance_limit:
            screen_name = name_map[user]
            nodes.append(screen_name)
            for follower in map(str, followers):
                if follower in name_map and len(relationships[follower]) > importance_limit:
                    edges.append((screen_name, name_map[follower]))

    # Draw the graph.
    digraph = functools.partial(Digraph, format='svg')
    add_edges(add_nodes(digraph(), nodes), edges).render('pics/g1')


def add_nodes(graph, nodes):
    """
    Helper function from http://matthiaseisen.com/articles/graphviz/
    """
    for n in nodes:
        if isinstance(n, tuple):
            graph.node(n[0], **n[1])
        else:
            graph.node(n)
    return graph


def add_edges(graph, edges):
    """
   Helper function from http://matthiaseisen.com/articles/graphviz/
   """
    for e in edges:
        if isinstance(e[0], tuple):
            graph.edge(*e[0], **e[1])
        else:
            graph.edge(*e)
    return graph


if __name__ == '__main__':
    main()
