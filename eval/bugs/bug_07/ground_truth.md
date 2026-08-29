# Ground truth — bug_07 (Date/time, timezone offset ignored)

**Scoring reference only. Not given to the agent.**

## Root cause

`localtime.event_day` ignores its `tz_offset_hours` argument entirely:

```python
def event_day(ts_utc, tz_offset_hours):
    return ts_utc.date()
```

It takes the date of the raw UTC timestamp. Whenever the local time is on a
different calendar day than UTC (evenings in behind-UTC zones, early mornings in
ahead-of-UTC zones), the returned date is off by one. Midday events happen to
land on the same date in both zones, which is why only near-midnight events look
wrong.

`to_local` is correct and already does the needed shift — `event_day` just
doesn't use it. `is_weekend` is wrong only as a downstream consequence of
`event_day`.

## Correct fix

Apply the offset before taking the date:

```python
def event_day(ts_utc, tz_offset_hours):
    return to_local(ts_utc, tz_offset_hours).date()
```

or inline: `return (ts_utc + timedelta(hours=tz_offset_hours)).date()`.

A timezone-aware implementation (attach `timezone.utc`, convert with
`astimezone(timezone(timedelta(hours=offset)))`, then `.date()`) is also
acceptable and arguably better, but the minimal correct fix is to route through
`to_local`.

## Tests that should fail before the fix

- `test_localtime.py::test_event_day_before_local_midnight` — returns 03-11, expected 03-10
- `test_localtime.py::test_event_day_after_local_midnight_ahead_zone` — returns 03-10, expected 03-11
- `test_localtime.py::test_is_weekend_uses_local_day` — returns `False`, expected `True`

Pass before and after: `test_to_local_shifts_by_offset`,
`test_event_day_same_day_in_both_zones`.

## Location

- File: `eval/bugs/bug_07/repo/localtime.py`
- Function: `event_day`

## Difficulty

Medium. The unused parameter is the giveaway once the agent looks at the
function, but it has to reason about calendar-day arithmetic to trust the fix,
and confirm `is_weekend`'s failure is downstream (no separate fix needed there).
