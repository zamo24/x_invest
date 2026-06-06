from app.core.rate_limit import FixedWindowRateLimiter


def test_fixed_window_rate_limiter_blocks_until_window_resets() -> None:
    limiter = FixedWindowRateLimiter()

    first = limiter.check("chat:subject", limit=2, window_seconds=10, now=100.0)
    second = limiter.check("chat:subject", limit=2, window_seconds=10, now=101.0)
    third = limiter.check("chat:subject", limit=2, window_seconds=10, now=102.0)
    after_reset = limiter.check("chat:subject", limit=2, window_seconds=10, now=111.0)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert third.allowed is False
    assert third.reset_after_seconds == 8
    assert after_reset.allowed is True
    assert after_reset.remaining == 1


def test_fixed_window_rate_limiter_is_scoped_by_key() -> None:
    limiter = FixedWindowRateLimiter()

    assert limiter.check("chat:alice", limit=1, window_seconds=10, now=100.0).allowed is True
    assert limiter.check("chat:alice", limit=1, window_seconds=10, now=101.0).allowed is False
    assert limiter.check("chat:bob", limit=1, window_seconds=10, now=101.0).allowed is True
