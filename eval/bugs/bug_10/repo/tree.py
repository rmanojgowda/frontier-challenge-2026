"""Recursive helpers over simple nested-dict trees.

A node is ``{"value": <number>, "children": [<node>, ...]}``. A leaf has an
empty ``children`` list.
"""


def sum_values(node):
    """Sum of ``value`` over the whole subtree rooted at ``node``."""
    total = node["value"]
    for child in node["children"]:
        total += sum_values(child)
    return total


def count_nodes(node):
    """Number of nodes in the subtree rooted at ``node``."""
    return 1 + sum(count_nodes(child) for child in node["children"])


def height(node):
    """Number of edges on the longest root-to-leaf path.

    A single leaf node has height 0.
    """
    if not node["children"]:
        return height(node)
    return 1 + max(height(child) for child in node["children"])
