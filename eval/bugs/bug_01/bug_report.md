# truncate() is chopping off the last character of my strings

**Component:** `stringutils`
**Version:** current `main`
**Severity:** medium

## What happens

I'm using `truncate(text, length)` to shorten labels before showing them in a
table. Every truncated label is one character too short.

For example:

```python
>>> from stringutils import truncate
>>> truncate("hello world", 5)
'hell'
```

I asked for 5 characters and got 4 (`"hell"`). I expected `"hello"`.

## What I expected

`truncate("hello world", 5)` should return the first 5 characters, `"hello"`.

## Other observations

- Strings that are shorter than `length` come back fine, untouched.
- A string whose length is exactly `length` also seems to lose its last
  character when I add one more character to push it over... actually no — when
  it's exactly at the limit it's returned as-is. It's only when the input is
  *longer* than `length` that the result is one short.
- So `truncate("abcdefgh", 3)` gives me `"ab"` instead of `"abc"`.

## Impact

Column headers and IDs in our UI are missing their last character whenever they
overflow, which makes some IDs ambiguous.
