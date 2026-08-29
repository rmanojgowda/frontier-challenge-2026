# Ground truth — bug_10 (Recursion, missing base case)

**Scoring reference only. Not given to the agent.**

## Root cause

`tree.height` has a leaf branch that recurses on the *same node* instead of
returning:

```python
def height(node):
    if not node["children"]:
        return height(node)          # <-- should return 0
    return 1 + max(height(child) for child in node["children"])
```

When a node has no children, `not node["children"]` is `True` and the function
calls `height(node)` again with the identical argument — unbounded recursion,
`RecursionError`. Every path through any tree eventually hits a leaf, so every
call fails.

`sum_values` and `count_nodes` iterate over `node["children"]` and terminate
naturally on the empty list (the `for` / `sum()` over `[]` is the implicit base
case), which is why they are fine.

## Correct fix

The leaf is the base case — return `0`:

```python
def height(node):
    if not node["children"]:
        return 0
    return 1 + max(height(child) for child in node["children"])
```

Equivalent: `return max((height(c) for c in node["children"]), default=-1) + 1`.
The minimal fix is `return height(node)` -> `return 0`.

## Tests that should fail before the fix

- `test_tree.py::test_height_of_leaf` — `RecursionError`
- `test_tree.py::test_height_of_tree` — `RecursionError`
- `test_tree.py::test_height_of_single_level` — `RecursionError`

Pass before and after: `test_sum_values`, `test_count_nodes`.

## Location

- File: `eval/bugs/bug_10/repo/tree.py`
- Function: `height`
- Line: `return height(node)` in the `if not node["children"]:` branch

## Difficulty

Easy–medium. The `RecursionError` traceback points straight at `height`, and the
self-call with an unchanged argument is an obvious infinite-recursion smell. The
agent needs to know the intended leaf height is `0` (stated in the docstring and
the bug report) to pick the right return value.
