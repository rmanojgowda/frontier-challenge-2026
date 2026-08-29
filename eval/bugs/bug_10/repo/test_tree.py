import pytest


from tree import sum_values, count_nodes, height


def leaf(value):
    return {"value": value, "children": []}


TREE = {
    "value": 1,
    "children": [
        leaf(2),
        {"value": 3, "children": [leaf(4), leaf(5)]},
    ],
}


def test_sum_values():
    assert sum_values(TREE) == 15


def test_count_nodes():
    assert count_nodes(TREE) == 5


def test_height_of_leaf():
    assert height(leaf(42)) == 0


def test_height_of_tree():
    assert height(TREE) == 2


def test_height_of_single_level():
    assert height({"value": 1, "children": [leaf(2), leaf(3)]}) == 1
