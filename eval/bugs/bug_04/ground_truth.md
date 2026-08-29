# Ground truth — bug_04 (Regex parser, greedy quantifier)

**Scoring reference only. Not given to the agent.**

## Root cause

`logparse._KV_RE` is:

```python
re.compile(r'(\w+)="(.*)"')
```

`.*` is greedy, so on a line with several pairs it consumes as much as possible
and backtracks only to the **last** `"` in the whole line. The result is a
single match whose value spans from the first opening quote to the final
closing quote, swallowing the intervening `" key="` text.

`test_parse_single_pair` passes because there is only one quote pair to match.

## Correct fix

Make the value match stop at the first closing quote. Either works:

```python
re.compile(r'(\w+)="([^"]*)"')      # preferred: explicit "not a quote"
```

or

```python
re.compile(r'(\w+)="(.*?)"')        # lazy quantifier
```

`[^"]*` is the better choice — it can't backtrack across quotes and handles the
"value with spaces" case correctly (`msg="disk almost full"` stays intact
because spaces are not quotes).

## Tests that should fail before the fix

- `test_logparse.py::test_parse_multiple_pairs` — returns one merged entry
- `test_logparse.py::test_parse_pair_among_other_text` — merged / wrong keys
- `test_logparse.py::test_value_with_spaces_is_kept_whole` — merges the two pairs

Pass before and after: `test_parse_single_pair`, `test_get_level`, `test_is_error`.

## Location

- File: `eval/bugs/bug_04/repo/logparse.py`
- Line: `_KV_RE = re.compile(r'(\w+)="(.*)"')`

## Difficulty

Easy–medium. Classic greedy-vs-lazy regex bug. The agent needs to recognise
that the value capture group is the problem and that `[^"]*` / `.*?` fixes it
without breaking the legitimate spaces-in-value case.
