# intword() returns "1000.0 million" instead of rolling over to "1.0 billion"

**Component:** `humanize` / `intword`
**Severity:** medium

## What happens

`intword` turns a large number into a short phrase — `1000000` becomes
`"1.0 million"`, `1200000000` becomes `"1.2 billion"`. But a value that sits
just under a power-of-1000 boundary comes back with a unit that doesn't make
sense:

```python
>>> from humanize import intword
>>> intword(999_999_999)
'1000.0 million'      # expected '1.0 billion'
```

The number part is even rounded up to `1000.0` — the function just leaves the
word "million" attached to it. Nobody writes "1000.0 million"; at that point it
is a billion.

## What I expected

`intword(999_999_999)` should be `"1.0 billion"`.

## Notes

- Exact boundaries are fine: `intword(1_000_000)` → `"1.0 million"`,
  `intword(1_000_000_000)` → `"1.0 billion"`.
- It is not only billions. `intword(999_999_999_999)` gives `"1000.0 billion"`
  where I expect `"1.0 trillion"`. Any value that rounds up to 1000 of one unit
  should tip into the next unit.
- It tracks the displayed rounding, not the raw value: `intword(999_950_000)`
  also prints `"1000.0 million"`, even though 999,950,000 is comfortably under a
  billion — `999.95` shows as `1000.0` at one decimal place.
- Values below a million (e.g. `intword(100)`) are returned unchanged, which is
  correct.
