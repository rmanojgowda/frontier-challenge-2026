# Ground truth — bug_08 (Ranking, inverted sort key)

**Scoring reference only. Not given to the agent.**

## Root cause

`ranking.rank_by_time` negates the sort key:

```python
ordered = sorted(racers, key=lambda r: -r["time"])
```

`time` is "lower is better", so sorting ascending by `time` gives fastest first.
The unary minus flips it to descending, so the slowest racer ends up first and
gets `rank = 1`. `fastest` and `podium` both read from index 0 / the head of
this list, so they inherit the inversion.

The single-racer case passes because order is irrelevant with one element.

## Correct fix

Sort by the key directly, ascending:

```python
ordered = sorted(racers, key=lambda r: r["time"])
```

Equivalent acceptable fixes: `sorted(racers, key=lambda r: r["time"],
reverse=False)` explicitly, or `sorted(..., key=itemgetter("time"))`. Do **not**
"fix" it by also reversing the enumerate / rank assignment — that would double
up. One change, remove the `-`.

## Tests that should fail before the fix

- `test_ranking.py::test_rank_order_is_fastest_first`
- `test_ranking.py::test_rank_numbers_start_at_one_for_fastest`
- `test_ranking.py::test_fastest`
- `test_ranking.py::test_podium`

Pass before and after: `test_single_racer`.

## Location

- File: `eval/bugs/bug_08/repo/ranking.py`
- Function: `rank_by_time`
- Line: `ordered = sorted(racers, key=lambda r: -r["time"])`

## Difficulty

Easy. Very visible once the agent reads `rank_by_time`. The only trap is
"fixing" it in two places (key *and* slice/enumerate) and re-inverting.
