# Ground truth — bug_01 (String utils, off-by-one)

**Do not give this file to the agent. Scoring reference only.**

## Root cause

`stringutils.truncate` slices with `text[:length - 1]` on the overflow path.
The `- 1` is wrong: a slice of `text[:length]` already yields exactly `length`
characters. The extra decrement drops one legitimate character, so every
truncated result is one character shorter than requested.

```python
# buggy
return text[:length - 1]
```

The non-overflow path (`len(text) <= length: return text`) is correct, which is
why short and exactly-at-limit inputs are unaffected — matching the reporter's
observation.

## Correct fix

Remove the off-by-one:

```python
def truncate(text, length):
    if len(text) <= length:
        return text
    return text[:length]
```

After the fix, `text[:length]` is redundant with — but not broken by — the
length check, and all inputs return at most `length` characters with no loss.

## Failing test that pins the bug

`repo/test_stringutils.py::test_truncate_longer_than_limit`
also `::test_truncate_keeps_all_requested_characters`

Both currently fail:
- `truncate("hello world", 5)` returns `"hell"`, expected `"hello"`
- `truncate("abcdefgh", 3)` returns `"ab"`, expected `"abc"`

The other five tests in the file pass both before and after the fix.

## Location

- File: `eval/bugs/bug_01/repo/stringutils.py`
- Function: `truncate`
- Line: the `return text[:length - 1]` statement (last line of the function)

## Difficulty

Easy. Single-line fix, localized, one clear failing assertion. Good smoke-test
case for the agent's evidence loop: run tests -> read failure -> localize ->
one-line patch -> re-run tests green.
