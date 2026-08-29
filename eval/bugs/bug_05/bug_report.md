# get_user() keeps returning the old name after update_name()

**Component:** `userrepo`
**Severity:** high

## What happens

If I read a user, then rename them, then read again, I get the *old* name back:

```python
>>> repo.get_user(1)
{'id': 1, 'name': 'Alice'}
>>> repo.update_name(1, 'Alicia')
>>> repo.get_user(1)
{'id': 1, 'name': 'Alice'}      # still Alice!
```

If I rename a user I have **not** read yet, the next read is correct. It's only
users I've already loaded once that get stuck.

## What I expected

`get_user` should reflect the latest data. After `update_name(1, 'Alicia')`,
`get_user(1)` should return `{'id': 1, 'name': 'Alicia'}`.

## Impact

Our admin UI shows stale names/emails until the process restarts. Support has
been telling customers to "wait a bit and refresh", which obviously doesn't
help.

## Notes

- Deleting a user does correctly stop `get_user` from returning them.
- Restarting the process clears it up (until the next edit).
