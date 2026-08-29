# parse_kv() merges everything between the first and last quote into one value

**Component:** `logparse`
**Severity:** medium

## What happens

When a log line has more than one `key="value"` pair, `parse_kv` only returns
the first key, and its value is a giant blob containing all the other pairs.

```python
>>> from logparse import parse_kv
>>> parse_kv('user="alice" action="login" result="ok"')
{'user': 'alice" action="login" result="ok'}
```

I expected:

```python
{'user': 'alice', 'action': 'login', 'result': 'ok'}
```

## What I expected

Each quoted value should stop at its own closing quote, and I should get one
dict entry per pair.

## Notes

- A line with exactly one pair works fine: `parse_kv('user="alice"')` is
  correct.
- A single value that legitimately contains spaces (e.g. `msg="disk almost
  full"`) should still come back whole — I'm not asking it to split on spaces,
  just to not run past the closing quote.
- `get_level()` and `is_error()` are unaffected.
