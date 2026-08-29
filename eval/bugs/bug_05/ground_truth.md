# Ground truth — bug_05 (Cache layer, missing invalidation on write)

**Scoring reference only. Not given to the agent.**

## Root cause

`UserRepo.get_user` populates `self._cache[user_id]` with a **copy** of the DB
record. `UserRepo.update_name` mutates the DB record but never touches the
cache:

```python
def update_name(self, user_id, new_name):
    self._db[user_id]["name"] = new_name
    # <-- nothing evicts / refreshes self._cache[user_id]
```

So any user that was read before the update keeps serving the stale cached copy
forever. `delete_user` *does* call `self._cache.pop(...)`, which is why deletes
behave correctly and why an un-read user updates fine (nothing cached yet) —
both matching the report.

## Correct fix

Invalidate (or refresh) the cache entry on write:

```python
def update_name(self, user_id, new_name):
    self._db[user_id]["name"] = new_name
    self._cache.pop(user_id, None)
```

Acceptable alternatives:
- refresh in place: `self._cache.pop(user_id, None)` then let the next
  `get_user` repopulate (same thing), or
- write-through: update both `self._db` and `self._cache[user_id]`.

Removing the cache entirely also makes the tests pass but throws away the
feature; a good grader should prefer the one-line eviction.

## Tests that should fail before the fix

- `test_userrepo.py::test_update_then_get_returns_new_name` — returns `"Alice"`, expected `"Alicia"`

Pass before and after: `test_get_user_returns_record`,
`test_get_unknown_user_is_none`, `test_update_without_prior_read`,
`test_delete_evicts_cache`.

## Location

- File: `eval/bugs/bug_05/repo/userrepo.py`
- Function: `update_name`

## Difficulty

Medium. Only one failing test, and the failure is state-dependent (needs a read
*before* the write to reproduce). The agent has to understand the cache
lifecycle and notice `delete_user` already does the eviction that `update_name`
is missing — that asymmetry is the tell.
