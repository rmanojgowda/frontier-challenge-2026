# Ground truth — bug_12 (real bug: humanize.intword magnitude carry-on-round)

**Scoring reference only. Not given to the agent.**

## Provenance

- **Repository:** [jmoiron/humanize](https://github.com/jmoiron/humanize) — MIT
  License, `Copyright (c) 2010-2020 Jason Moiron and Contributors`.
- **Reported in:** issues [#59](https://github.com/jmoiron/humanize/issues/59)
  ("999999999 should be '1 billion' but is not") and #64.
- **Fixed by:** [PR #113](https://github.com/jmoiron/humanize/pull/113)
  (`Jasarin-V-patch-1`), merged 2020-03-05.
- **Buggy commit (this fixture's source):**
  `b28d9ad895a1b2ef066c0b689b96bc50498554ba` — the first parent of the fix
  merge.
- **Fix merge commit:** `86447e1b661dabdf888449e9e4a447ae59f495f3`.

`repo/humanize/number.py` and `repo/humanize/i18n.py` are the **verbatim**
module sources at `b28d9ad` (sha1 of `number.py`:
`3d388d4b9fb3393a7123497df32430d39328920c`). `repo/humanize/__init__.py` is a
minimal shim replacing the upstream `__init__` (which imports `pkg_resources`
and compiled locale catalogs unrelated to this bug); it only re-exports
`intword`.

## Root cause

`intword` (`number.py`) picks the magnitude bucket from the **unrounded** value
but formats the mantissa with rounding, so the mantissa can round up to
`1000.0` while the unit word stays one tier too low:

```python
if value < powers[0]:
    return str(value)
for ordinal, power in enumerate(powers[1:], 1):
    if value < power:
        chopped = value / float(powers[ordinal - 1])
        return (" ".join([format, _(human_powers[ordinal - 1])])) % chopped   # BUG
return str(value)
```

`powers = [10**6, 10**9, 10**12, …]`, `human_powers = ("million", "billion",
"trillion", …)`. For `value = 999_999_999`: the loop stops at `ordinal = 1`
(`value < 10**9`), so the unit is `human_powers[0]` = "million" and
`chopped = 999_999_999 / 10**6 = 999.999999`. `"%.1f" % 999.999999` is
`"1000.0"`, giving `"1000.0 million"`. The same happens at every tier
(`"1000.0 billion"` for `999_999_999_999`, etc.) and for any value whose
mantissa *rounds* to `1000.0` (`999_950_000` → `999.95` → `"1000.0"`), even
though it is numerically below the threshold.

## Correct fix (the historical one)

PR #113's change to `intword` — detect the post-format carry and move up a
tier:

```python
for ordinal, power in enumerate(powers[1:], 1):
    if value < power:
        chopped = value / float(powers[ordinal - 1])
        if float(format % chopped) == float(10 ** 3):
            chopped = value / float(powers[ordinal])
            return (" ".join([format, _(human_powers[ordinal])])) % chopped
        else:
            return (" ".join([format, _(human_powers[ordinal - 1])])) % chopped
return str(value)
```

The carry test is done on the **formatted** mantissa (`float(format % chopped)`),
not on `chopped` directly, and it is applied at **every** tier of the loop.

(PR #113 also bundled unrelated cleanup — removing a `scientific()` helper,
reformatting docstrings. Only the `intword` hunk above is the bug fix.)

## Tempting partial fixes and the tests that catch them

| Partial fix | Passes reported case? | Fails |
|---|---|---|
| Guard on the raw quotient: `if chopped >= 1000:` carry | yes for `999_999_999` | `test_intword_carry_just_below_boundary` — `999_950_000` gives `chopped = 999.95 < 1000`, so no carry, still `"1000.0 million"` |
| Special-case only the first tier (million → billion) | yes | `test_intword_carry_into_trillions` — `999_999_999_999` still yields `"1000.0 billion"` |
| Post-process the string (`"1000.0 million"` → `"1.0 billion"`) | maybe | brittle; typically also breaks the exact-boundary sanity tests once the mantissa/word mapping drifts |

The correct fix must (a) test the *rounded* mantissa and (b) apply at all
tiers.

## Tests

Fail before the fix:

- `test_number.py::test_intword_reported_case_rounds_into_billions` —
  `999_999_999` → `"1000.0 million"`, expected `"1.0 billion"`
- `test_number.py::test_intword_carry_just_below_boundary` — `999_950_000` →
  `"1000.0 million"`, expected `"1.0 billion"`
- `test_number.py::test_intword_carry_into_trillions` — `999_999_999_999` →
  `"1000.0 billion"`, expected `"1.0 trillion"`

Pass before and after (must not regress):

- `test_number.py::test_intword_million`
- `test_number.py::test_intword_fractional_million`
- `test_number.py::test_intword_exact_billion`
- `test_number.py::test_intword_below_million_unchanged`

## Location

- File: `eval/bugs/bug_12/repo/humanize/number.py`
- Function: `intword`
- Line: `return (" ".join([format, _(human_powers[ordinal - 1])])) % chopped`
  (inside the `if value < power:` branch)

## Difficulty

Medium. The reported symptom points almost directly at the formatting line, and
the one-tier fix is easy to see. The subtleties that separate a real fix from a
plausible one: the carry must key off the *rounded* mantissa (not `chopped >=
1000`), and it must work at every magnitude, not just million→billion. A
verbatim third-party module (with unrelated helpers and gettext calls) also
means slightly more to read than the synthetic single-file cases.
