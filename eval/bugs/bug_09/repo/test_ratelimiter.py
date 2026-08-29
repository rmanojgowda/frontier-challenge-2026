import pytest

from ratelimiter import RateLimiter


def test_allows_up_to_the_limit():
    rl = RateLimiter(max_calls=3, window=10)
    assert rl.allow(now=0) is True
    assert rl.allow(now=1) is True
    assert rl.allow(now=2) is True


def test_rejects_the_call_that_exceeds_the_limit():
    rl = RateLimiter(max_calls=3, window=10)
    rl.allow(now=0)
    rl.allow(now=1)
    rl.allow(now=2)
    # 4th call inside the same window must be rejected
    assert rl.allow(now=3) is False


def test_exactly_max_calls_are_allowed_in_a_window():
    rl = RateLimiter(max_calls=5, window=60)
    allowed = sum(1 for t in range(20) if rl.allow(now=t * 0.1))
    assert allowed == 5


def test_window_slides():
    rl = RateLimiter(max_calls=2, window=10)
    assert rl.allow(now=0) is True
    assert rl.allow(now=1) is True
    assert rl.allow(now=2) is False
    # after the window passes, calls are allowed again
    assert rl.allow(now=100) is True
