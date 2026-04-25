"""Tests for deploy_sentinel.deployment_lock."""
import time

import pytest

from deploy_sentinel.deployment_lock import DeploymentLock, LockEntry


# ---------------------------------------------------------------------------
# LockEntry
# ---------------------------------------------------------------------------

class TestLockEntry:
    def test_not_expired_immediately(self):
        entry = LockEntry(owner="svc", ttl=60.0)
        assert not entry.is_expired()

    def test_expired_after_ttl(self):
        entry = LockEntry(owner="svc", ttl=0.01)
        time.sleep(0.02)
        assert entry.is_expired()


# ---------------------------------------------------------------------------
# DeploymentLock
# ---------------------------------------------------------------------------

@pytest.fixture()
def lock() -> DeploymentLock:
    return DeploymentLock()


class TestDeploymentLock:
    def test_acquire_succeeds_when_free(self, lock):
        assert lock.acquire("worker-1") is True

    def test_second_acquire_fails_when_held(self, lock):
        lock.acquire("worker-1")
        assert lock.acquire("worker-2") is False

    def test_same_owner_cannot_reacquire(self, lock):
        lock.acquire("worker-1")
        assert lock.acquire("worker-1") is False

    def test_release_by_owner_succeeds(self, lock):
        lock.acquire("worker-1")
        assert lock.release("worker-1") is True

    def test_release_by_non_owner_fails(self, lock):
        lock.acquire("worker-1")
        assert lock.release("worker-2") is False

    def test_release_when_free_returns_false(self, lock):
        assert lock.release("worker-1") is False

    def test_is_locked_true_when_held(self, lock):
        lock.acquire("worker-1")
        assert lock.is_locked() is True

    def test_is_locked_false_when_free(self, lock):
        assert lock.is_locked() is False

    def test_is_locked_false_after_release(self, lock):
        lock.acquire("worker-1")
        lock.release("worker-1")
        assert lock.is_locked() is False

    def test_expired_lock_is_not_locked(self, lock):
        lock.acquire("worker-1", ttl=0.01)
        time.sleep(0.02)
        assert lock.is_locked() is False

    def test_acquire_after_expiry_succeeds(self, lock):
        lock.acquire("worker-1", ttl=0.01)
        time.sleep(0.02)
        assert lock.acquire("worker-2") is True

    def test_current_owner_returns_owner(self, lock):
        lock.acquire("worker-1")
        assert lock.current_owner() == "worker-1"

    def test_current_owner_none_when_free(self, lock):
        assert lock.current_owner() is None

    def test_force_release_clears_lock(self, lock):
        lock.acquire("worker-1")
        lock.force_release()
        assert lock.is_locked() is False
        assert lock.acquire("worker-2") is True
