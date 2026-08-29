# event_day() reports the wrong date for events near midnight

**Component:** `localtime`
**Severity:** medium

## What happens

`event_day(ts_utc, tz_offset_hours)` is supposed to tell me which local
calendar day an event happened on. For events in the evening (local time) it
returns tomorrow's date.

```python
>>> from datetime import datetime
>>> from localtime import event_day
>>> event_day(datetime(2023, 3, 11, 2, 0, 0), -5)   # 02:00 UTC = 21:00 on the 10th local
datetime.date(2023, 3, 11)      # expected 2023-03-10
```

Our daily activity report is bucketing these evening events into the wrong day,
so the day boundaries in the report are all shifted.

## What I expected

`event_day(datetime(2023, 3, 11, 2, 0, 0), -5)` should be `2023-03-10`, because
2 AM UTC is 9 PM the previous day in a UTC-5 zone.

## Notes

- `to_local(ts, -5)` returns the correct shifted datetime, so the offset value
  itself is being passed in fine.
- Events in the middle of the local day are bucketed correctly; it's only the
  ones close to local midnight that land on the wrong date.
- Same problem in the other direction for zones ahead of UTC.
