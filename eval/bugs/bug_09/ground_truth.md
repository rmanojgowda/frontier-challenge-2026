# Ground truth — bug_09 (Rate limiter, off-by-one in threshold)

**Scoring reference only. Not given to the agent.**

## Root cause

`RateLimiter.allow` checks the count *before* recording the current call:

```python
if len(self._calls) <= self.max_calls:
    self._calls.append(now)
    return True
```

At the moment of the Nth+1 call there are already `N` timestamps in
`self._calls`, and `N <= max_calls` (`N <= N`) is `True`, so the call is
allowed and becomes the `(N+1)`th. The comparison should be strict `<`: allow
only while fewer than `max_calls` calls are already recorded.

## Correct fix

```python
if len(self._calls) < self.max_calls:
    self._calls.append(now)
    return True
return False
```

Equivalent: check `len(self._calls) + 1 <= self.max_calls`, or append first and
then compare `len(self._calls) <= self.max_calls` (append, test, pop-and-reject
on failure). The minimal fix is `<=` -> `<`.

## Tests that should fail before the fix

- `test_ratelimiter.py::test_rejects_the_call_that_exceeds_the_limit` — 4th call returns `True`
- `test_ratelimiter.py::test_exactly_max_calls_are_allowed_in_a_window` — 6 allowed, expected 5
- `test_ratelimiter.py::test_window_slides` — 3rd call in-window returns `True`

Pass before and after: `test_allows_up_to_the_limit`.

## Location

- File: `eval/bugs/bug_09/repo/ratelimiter.py`
- Function: `allow`
- Line: `if len(self._calls) <= self.max_calls:`

## Difficulty

Easy. One operator. The agent needs to reason about *when* the current call is
counted (before append) to see why `<=` is one too many.
