# Rate limiter lets one extra request through every window

**Component:** `ratelimiter`
**Severity:** medium

## What happens

I configured `RateLimiter(max_calls=3, window=10)` expecting at most 3 calls per
10-second window. It actually allows 4.

```python
rl = RateLimiter(max_calls=3, window=10)
rl.allow(now=0)   # True
rl.allow(now=1)   # True
rl.allow(now=2)   # True
rl.allow(now=3)   # True  <-- expected False, this is the 4th call
rl.allow(now=4)   # False
```

## What I expected

The 4th call within the window should return `False`. With `max_calls=N` I
should be able to get exactly `N` calls through per window, not `N + 1`.

## Impact

We're using this in front of a partner API that bills per call and enforces its
own hard limit. Our "3 per window" is actually sending 4 and we're getting
throttled on their side.

## Notes

- The sliding-window behaviour itself seems right — once the old calls age out,
  new ones are allowed again.
