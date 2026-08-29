# Ground truth — bug_13 (real bug: python-semver pre-release precedence direction)

**Scoring reference only. Not given to the agent.**

## Provenance

- **Repository:** [python-semver/python-semver](https://github.com/python-semver/python-semver)
  — BSD-3-Clause, `Copyright (c) 2013, Konstantine Rybnikov` (`repo/LICENSE.txt`).
- **Reported in:** issue [#45](https://github.com/python-semver/python-semver/issues/45)
  ("Version comparison does not conform to semver spec for prerelease tags",
  opened 2017-01-12).
- **Fixed by:** PR [#46](https://github.com/python-semver/python-semver/pull/46)
  ("fix version comparisons"), merged 2017-01-16, released in v2.7.4.
- **Buggy commit (this fixture's source):**
  `41a071595cdb400e625f366838b35d61d538ac7e` (v2.7.3 — the first parent of the
  fix merge).
- **Fix branch tip:** `e1a633cc445ba63a9fbf23b679994d5fa0554cf7`.
- **Fix merge commit:** `4cac6fff9d7a530f358b65385658915e4f2a5caa`.

`repo/semver.py` is the **verbatim** module at `41a0715` (sha1
`3a9ee799fc72901e8f27f2581184adf720c2d778`). It is stdlib-only (`collections`,
`re`, `sys`) and carries a `cmp` shim (`if not hasattr(__builtins__, 'cmp')`),
so it runs unmodified on Python 3.

## Root cause

`compare()` → `nat_cmp()` → `convert()` in the buggy revision:

```python
def convert(text):
    return (2, int(text)) if re.match('[0-9]+', text) else (1, text)
```

Each dot-separated pre-release identifier becomes a 2-tuple whose first element
is a "type tag" — this keeps Python 3 from trying to compare an `int` to a `str`
directly (which raises). Numeric identifiers are tagged `2`, alphanumeric ones
`1`. Tuples compare element-wise, so `(1, "beta") < (2, 1)` — a **text**
identifier sorts before a **numeric** one, giving numeric identifiers the
*higher* precedence.

SemVer §11.4.3 requires the opposite: *"Numeric identifiers always have lower
precedence than non-numeric identifiers."* So `1.0.0-alpha.1` must sort **below**
`1.0.0-alpha.beta`; the buggy code returns the reverse. Every failing vector
traces to this single line:

- `compare("1.0.0-alpha.1", "1.0.0-alpha.beta")` → `1` (spec: `-1`)
- `compare("1.0.0-1", "1.0.0-alpha")` → `1` (spec: `-1`)

### What is *not* broken at this revision

- **Numeric-vs-numeric** is correct: `beta.2` vs `beta.11` compares `int("2")`
  to `int("11")` → `-1`.
- **Any-prerelease-below-release** is handled separately in `compare_by_keys`
  (`if not rc2: return -1`) and is correct.
- **The field-count / prefix rule** is correct *by accident of Python list
  semantics*: `cmp(split_key(a), split_key(b))` compares the two lists of
  tuples, and a shorter list that is a prefix of a longer one sorts lower on
  its own. `1.0.0-alpha` < `1.0.0-alpha.1` already works.

(An earlier draft of this case was scoped around `beta.2` vs `beta.11`; that
vector already passes at `41a0715` — an earlier PR fixed the pure-lexicographic
comparison — so the case was re-scoped to the numeric-vs-text direction, which
is what actually regresses here.)

## Correct fix (the historical one, PR #46)

PR #46 rewrites `nat_cmp` so identifiers keep their natural type and are
compared through an explicit helper that encodes the §11 rules:

```python
def convert(text):
    return int(text) if re.match('[0-9]+', text) else text

def cmp_prerelease_tag(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return cmp(a, b)
    elif isinstance(a, int):
        return -1          # numeric < non-numeric
    elif isinstance(b, int):
        return 1
    else:
        return cmp(a, b)

a_parts, b_parts = split_key(a), split_key(b)
for sub_a, sub_b in zip(a_parts, b_parts):
    cmp_result = cmp_prerelease_tag(sub_a, sub_b)
    if cmp_result != 0:
        return cmp_result
else:
    return cmp(len(a), len(b))
```

The trailing `cmp(len(a), len(b))` re-adds the shorter-sorts-lower tiebreak that
was implicit in `cmp(list, list)` and is lost once the comparison is a manual
`zip` loop. (It uses the *string* lengths — a crude stand-in for field count,
but it is what shipped and it satisfies the spec's chained examples.)

**Acceptable smaller fix:** just flip the tag ordering in `convert` — `(1,
int(text))` for numeric, `(2, text)` for text. This passes every reported vector
and regresses none of the protected ones. It keeps the type-tag trick, so it
does not need `cmp_prerelease_tag`.

## Tests

Fail before the fix:

- `test_semver.py::test_numeric_prerelease_identifier_sorts_below_text`
  (`alpha.1` vs `alpha.beta`)
- `test_semver.py::test_numeric_prerelease_identifier_sorts_below_text_first_field`
  (`1` vs `alpha`)
- `test_semver.py::test_semver_org_precedence_chain` (fails only on the
  `alpha.1` < `alpha.beta` link)

Pass before and after (must not regress):

- `test_semver.py::test_numeric_identifiers_compare_numerically`
  (`beta.2` < `beta.11`)
- `test_semver.py::test_any_prerelease_sorts_below_the_release`
  (`rc.1` < `1.0.0`)
- `test_semver.py::test_shorter_prerelease_sorts_below_its_longer_prefix`
  (`alpha` < `alpha.1`)

## Location

- File: `eval/bugs/bug_13/repo/semver.py`
- Function: `nat_cmp` (the inner comparator inside `compare`; the buggy line is
  in its nested `convert` helper)
- Line: `return (2, int(text)) if re.match('[0-9]+', text) else (1, text)`

## Difficulty

Medium. The report names the rule and the buggy line is short, but the traps
are real:

1. If you drop the type-tag tuple and return the raw `int` / `str`, comparisons
   like `alpha` vs `1` raise `TypeError` on Python 3 — the real fix compensates
   with an explicit `cmp_prerelease_tag`; a naive "return the natural type"
   patch crashes.
2. Comparing the numeric identifiers as strings (e.g. sorting `("2", "11")`
   lexically) regresses `test_numeric_identifiers_compare_numerically`.
3. Reworking the loop can silently drop the shorter-prefix tiebreak and
   regress `test_shorter_prerelease_sorts_below_its_longer_prefix`.

The module is a verbatim 342-line third-party file (doctests in the docstring, a
`cmp` shim) — more to read than the synthetic single-purpose cases.
