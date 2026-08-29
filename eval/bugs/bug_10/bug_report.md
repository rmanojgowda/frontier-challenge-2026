# height() blows the stack on any tree

**Component:** `tree`
**Severity:** high

## What happens

Calling `height()` on anything - even a single leaf node - raises
`RecursionError`:

```python
>>> from tree import height
>>> height({"value": 42, "children": []})
RecursionError: maximum recursion depth exceeded
```

A tree with actual depth also fails, because it recurses forever as soon as it
reaches a leaf.

## What I expected

- `height` of a single leaf node should be `0`.
- `height` of a tree where the deepest leaf is 2 edges from the root should be
  `2`.

## Notes

- `sum_values` and `count_nodes` work fine on the same trees, so the tree data
  itself is well-formed (leaves have `"children": []`).
- It's specifically the leaf case that seems to spin.
