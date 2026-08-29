# Leaderboard is upside down - slowest racer shown as rank 1

**Component:** `ranking`
**Severity:** high

## What happens

`rank_by_time()` puts the **slowest** racer at the top with rank 1 and the
fastest at the bottom.

```python
>>> from ranking import rank_by_time
>>> racers = [
...     {"name": "Ada", "time": 42.0},
...     {"name": "Bo",  "time": 37.5},
...     {"name": "Cy",  "time": 55.1},
...     {"name": "Di",  "time": 40.2},
... ]
>>> [r["name"] for r in rank_by_time(racers)]
['Cy', 'Ada', 'Di', 'Bo']      # Cy (55.1s, slowest) is rank 1?!
```

Lower time = faster = should be rank 1. I expected `['Bo', 'Di', 'Ada', 'Cy']`.

## What I expected

- `fastest(racers)` should be `"Bo"` (37.5 s). It currently returns `"Cy"`.
- `podium(racers)` should be `["Bo", "Di", "Ada"]`.

## Notes

- The `rank` numbers themselves are 1..N in order, they're just attached to the
  wrong racers.
- With a single racer it looks fine (rank 1, obviously).
