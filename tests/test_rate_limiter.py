"""Tests for deploy_sentinel.rate_limiter."""
from __future__ import annotations

import time

import pytest

from deploy_sentinel.rate_limiter import RateLimiter, RateLimitEntry


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter(max_calls=3, window_seconds=60.0)


class TestRateLimiterIsAllowed:
    def test_first_call_is_allowed(self, limiter: RateLimiter) -> None:
        assert limiter.is_allowed("container_a") is True

    def test_calls_within_limit_are_allowed(self, limiter: RateLimiter) -> None:
        for _ in range(3):
            assert limiter.is_allowed("container_a") is True

    def test_call_exceeding_limit_is_denied(self, limiter: RateLimiter) -> None:
        for _ in range(3):
            limiter.is_allowed("container_a")
        assert limiter.is_allowed("container_a") is False

    def test_different_keys_are_independent(self, limiter: RateLimiter) -> None:
        for _ in range(3):
            limiter.is_allowed("container_a")
        assert limiter.is_allowed("container_b") is True

    def test_window_expiry_resets_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        base = 1_000.0
        calls = [base]

        def fake_monotonic() -> float:
            return calls[0]

        monkeypatch.setattr(time, "monotonic", fake_monotonic)

        lim = RateLimiter(max_calls=2, window_seconds=10.0)
        lim.is_allowed("k")
        lim.is_allowed("k")
        assert lim.is_allowed("k") is False

        calls[0] = base + 11.0
        assert lim.is_allowed("k") is True


class TestRateLimiterRemaining:
    def test_remaining_full_when_no_calls(self, limiter: RateLimiter) -> None:
        assert limiter.remaining("container_a") == 3

    def test_remaining_decreases_with_calls(self, limiter: RateLimiter) -> None:
        limiter.is_allowed("container_a")
        limiter.is_allowed("container_a")
        assert limiter.remaining("container_a") == 1

    def test_remaining_zero_when_exhausted(self, limiter: RateLimiter) -> None:
        for _ in range(3):
            limiter.is_allowed("container_a")
        assert limiter.remaining("container_a") == 0


class TestRateLimiterReset:
    def test_reset_specific_key(self, limiter: RateLimiter) -> None:
        for _ in range(3):
            limiter.is_allowed("container_a")
        limiter.reset("container_a")
        assert limiter.is_allowed("container_a") is True

    def test_reset_all_keys(self, limiter: RateLimiter) -> None:
        limiter.is_allowed("a")
        limiter.is_allowed("b")
        limiter.reset()
        assert limiter.remaining("a") == 3
        assert limiter.remaining("b") == 3

    def test_reset_nonexistent_key_is_safe(self, limiter: RateLimiter) -> None:
        limiter.reset("ghost")  # should not raise
