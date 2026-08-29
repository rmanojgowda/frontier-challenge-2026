# Ground truth — bug_02 (Data validator, wrong exception type caught)

**Scoring reference only. Not given to the agent.**

## Root cause

`validators.is_in_range` guards the comparison with `except ValueError`:

```python
try:
    return low <= value <= high
except ValueError:
    return False
```

But comparing incompatible types in Python 3 (`0 <= "forty"`, `0 <= None`)
raises **`TypeError`**, not `ValueError`. The handler never catches it, so the
exception propagates out of `is_in_range` -> `validate_row` -> `filter_valid`
and aborts the whole batch. Bad data is neither reported nor skipped; instead it
takes the pipeline down.

`ValueError`-style failures (there are none on this path in practice) would be
handled; the type mismatch that actually occurs is not.

## Correct fix

Catch the exception that is actually raised. Minimal:

```python
try:
    return low <= value <= high
except (TypeError, ValueError):
    return False
```

Equivalent acceptable alternative — type-check first:

```python
if not isinstance(value, (int, float)) or isinstance(value, bool):
    return False
return low <= value <= high
```

Either makes `is_in_range("forty", 0, 130)` and `is_in_range(None, 0, 130)`
return `False`, so the bad row fails `validate_row` and is dropped by
`filter_valid`.

## Tests that should fail before the fix

- `test_validators.py::test_in_range_rejects_non_numeric_string` — raises `TypeError`, expected `False`
- `test_validators.py::test_in_range_rejects_none` — raises `TypeError`, expected `False`
- `test_validators.py::test_validate_row_flags_bad_age_type` — raises `TypeError`
- `test_validators.py::test_filter_valid_drops_row_with_mistyped_age` — raises `TypeError`

The remaining tests (email checks, numeric in-range checks) pass before and after.

## Location

- File: `eval/bugs/bug_02/repo/validators.py`
- Function: `is_in_range`
- Line: `except ValueError:`

## Difficulty

Easy–medium. The fix is one line, but the agent has to read the traceback,
notice the raised type (`TypeError`) differs from the caught type
(`ValueError`), and not be distracted by the `is_valid_email` path.
