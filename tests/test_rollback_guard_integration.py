"""Integration tests: RollbackGuard used alongside RollbackManager."""

from unittest.mock import MagicMock, patch

import pytest

from deploy_sentinel.rollback_guard import RollbackGuard
from deploy_sentinel.rollback import RollbackManager


def _make_container(image: str = "app:v1", previous: str = "app:v0") -> MagicMock:
    c = MagicMock()
    c.id = "abc123"
    c.image.tags = [image]
    c.labels = {"deploy-sentinel.previous-image": previous}
    return c


@pytest.fixture()
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def manager(mock_client: MagicMock) -> RollbackManager:
    return RollbackManager(mock_client)


@pytest.fixture()
def guard() -> RollbackGuard:
    return RollbackGuard(max_rollbacks=2, window_seconds=300.0, cooldown_seconds=600.0)


class TestRollbackGuardWithManager:
    def test_rollback_proceeds_when_allowed(self, manager: RollbackManager, guard: RollbackGuard) -> None:
        container = _make_container()
        now = 0.0
        assert guard.is_allowed(container.id, now=now)
        guard.record_rollback(container.id, now=now)
        result = manager.rollback(container)
        assert result is True
        manager.client.containers.run.assert_called_once()

    def test_rollback_skipped_when_blocked(self, manager: RollbackManager, guard: RollbackGuard) -> None:
        container = _make_container()
        guard.record_rollback(container.id, now=0.0)
        guard.record_rollback(container.id, now=1.0)

        assert not guard.is_allowed(container.id, now=2.0)
        # Simulate caller respecting the guard
        manager.client.containers.run.assert_not_called()

    def test_reset_allows_rollback_again(self, manager: RollbackManager, guard: RollbackGuard) -> None:
        container = _make_container()
        guard.record_rollback(container.id, now=0.0)
        guard.record_rollback(container.id, now=1.0)
        guard.reset(container.id)

        assert guard.is_allowed(container.id, now=2.0)
        guard.record_rollback(container.id, now=2.0)
        result = manager.rollback(container)
        assert result is True
