# Pre-release versions with a number in them sort the wrong way round

**Component:** `semver` / `compare`
**Severity:** medium

## What happens

I use `compare()` to order a batch of pre-release tags and some pairs come out
reversed. It happens when one identifier is a plain number and the other is a
word: the number ends up sorting *after* the word.

```python
>>> import semver
>>> semver.compare("1.0.0-alpha.1", "1.0.0-alpha.beta")
1        # I expected -1 — "alpha.1" should come before "alpha.beta"
```

Same when the number is the first identifier:

```python
>>> semver.compare("1.0.0-1", "1.0.0-alpha")
1        # expected -1
```

Per semver.org, a numeric identifier has lower precedence than a non-numeric
one, so `1.0.0-alpha.1` < `1.0.0-alpha.beta`. This is coming back the other way.

## What I expected

`compare("1.0.0-alpha.1", "1.0.0-alpha.beta")` should return `-1` (and the
reverse call `1`).

## Notes

- Two numeric identifiers compare fine: `compare("1.0.0-beta.2",
  "1.0.0-beta.11")` correctly gives `-1` (compared as numbers, not text).
- A pre-release still sorts below the plain release:
  `compare("1.0.0-rc.1", "1.0.0")` gives `-1`.
- A shorter tag that is a prefix of a longer one sorts correctly too:
  `compare("1.0.0-alpha", "1.0.0-alpha.1")` gives `-1`.
- It is specifically the mixed number-vs-word case that is wrong.
