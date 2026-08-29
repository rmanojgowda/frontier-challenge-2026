# Batch import crashes on a row with a non-numeric age instead of skipping it

**Component:** `validators`
**Severity:** high

## What happens

Our nightly import calls `filter_valid(rows)` to throw out bad rows before we
write them to the database. It works fine until a row shows up with `age` as a
string (someone typed `"forty"` into the source spreadsheet). Then the whole
import blows up:

```
TypeError: '<=' not supported between instances of 'int' and 'str'
```

The traceback points into `is_in_range`.

## What I expected

That row should just be reported as invalid (bad age) and dropped, like any
other row that fails validation. One malformed row shouldn't take down the
entire import and lose the thousands of good rows after it.

## Repro

```python
from validators import filter_valid

rows = [
    {"email": "a@b.com", "age": 30},
    {"email": "c@d.com", "age": "forty"},   # bad data
    {"email": "e@f.com", "age": 45},
]
filter_valid(rows)   # -> TypeError, instead of returning the two good rows
```

## Notes

- `is_in_range(200, 0, 130)` correctly returns `False`.
- `is_in_range("forty", 0, 130)` raises instead of returning `False`.
- Passing `age=None` (missing column) also raises.
