"""Tests for deploy_sentinel.rollback_guard."""

import pytest
from deploy_sentinel.rollback_guard import RollbackGuard, RollbackGuardEntry


@pytest.fixture()
def guard() -> RollbackGuard:
    return RollbackGuard(max_rollbacks=3, window_seconds=300.0, cooldown_seconds=600.0)


class TestRollbackGuardEntry:
    def test_not_blocked_by_default(self) -> None:
        entry = RollbackGuardEntry(container_id="abc")
        assert not entry.is_blocked()

    def test_blocked_when_blocked_until_is_future(self) -> None:
        import time
        entry = RollbackGuardEntry(container_id="abc", blocked_until=time.monotonic() + 100)
        assert entry.is_blocked()

    def test_not_blocked_after_expiry(self) -> None:
        entry = RollbackGuardEntry(container_id="abc", blocked_until=0.0)
        assert not entry.is_blocked(now=1.0)


class TestRollbackGuardInit:
    def test_invalid_max_rollbacks_raises(self) -> None:
        with pytest.raises(ValueError, match="max_rollbacks"):
            RollbackGuard(max_rollbacks=0)

    def test_invalid_window_raises(self) -> None:
        with pytest.raises(ValueError, match="window_seconds"):
            RollbackGuard(window_seconds=0)

    def test_invalid_cooldown_raises(self) -> None:
        with pytest.raises(ValueError, match="cooldown_seconds"):
            RollbackGuard(cooldown_seconds=-1)


class TestRollbackGuardIsAllowed:
    def test_first_rollback_is_allowed(self, guard: RollbackGuard) -> None:
        assert guard.is_allowed("c1", now=0.0)

    def test_within_limit_is_allowed(self, guard: RollbackGuard) -> None:
        guard.record_rollback("c1", now=0.0)
        guard.record_rollback("c1", now=1.0)
        assert guard.is_allowed("c1", now=2.0)

    def test_at_limit_is_blocked(self, guard: RollbackGuard) -> None:
        guard.record_rollback("c1", now=0.0)
        guard.record_rollback("c1", now=1.0)
        guard.record_rollback("c1", now=2.0)
        assert not guard.is_allowed("c1", now=3.0)

    def test_different_containers_are_independent(self, guard: RollbackGuard) -> None:
        for i in range(3):
            guard.record_rollback("c1", now=float(i))
        assert not guard.is_allowed("c1", now=4.0)
        assert guard.is_allowed("c2", now=4.0)

    def test_allowed_again_after_window_resets(self, guard: RollbackGuard) -> None:
        guard.record_rollback("c1", now=0.0)
        guard.record_rollback("c1", now=1.0)
        # Advance beyond window; count should reset
        assert guard.is_allowed("c1", now=400.0)

    def test_blocked_during_cooldown(self, guard: RollbackGuard) -> None:
        for i in range(3):
            guard.record_rollback("c1", now=float(i))
        # Still within cooldown window
        assert not guard.is_allowed("c1", now=500.0)

    def test_allowed_after_cooldown_expires(self, guard: RollbackGuard) -> None:
        for i in range(3):
            guard.record_rollback("c1", now=float(i))
        # Beyond cooldown_seconds (600) from last block trigger
        assert guard.is_allowed("c1", now=700.0)


class TestRollbackGuardReset:
    def test_reset_clears_entry(self, guard: RollbackGuard) -> None:
        for i in range(3):
            guard.record_rollback("c1", now=float(i))
        guard.reset("c1")
        assert guard.is_allowed("c1", now=5.0)

    def test_reset_unknown_container_is_noop(self, guard: RollbackGuard) -> None:
        guard.reset("unknown")  # should not raise
