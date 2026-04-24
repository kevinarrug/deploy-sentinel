"""Tests for deploy_sentinel.rollback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from deploy_sentinel.rollback import RollbackManager, RollbackRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_container(
    name: str = "web",
    image: str = "myapp:v2",
    previous_image: str = "myapp:v1",
    env: list[str] | None = None,
    port_bindings: dict | None = None,
) -> MagicMock:
    container = MagicMock()
    container.name = name
    container.image.tags = [image]
    container.labels = {"deploy-sentinel.previous-image": previous_image}
    container.attrs = {
        "Config": {"Env": env or []},
        "HostConfig": {"PortBindings": port_bindings or {}},
    }
    return container


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def manager(mock_client: MagicMock) -> RollbackManager:
    return RollbackManager(client=mock_client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetPreviousImage:
    def test_returns_label_value(self, manager: RollbackManager) -> None:
        container = _make_container(previous_image="myapp:v1")
        assert manager.get_previous_image(container) == "myapp:v1"

    def test_returns_none_when_label_missing(self, manager: RollbackManager) -> None:
        container = _make_container()
        container.labels = {}
        assert manager.get_previous_image(container) is None


class TestRollback:
    def test_successful_rollback(self, manager: RollbackManager, mock_client: MagicMock) -> None:
        container = _make_container(name="web", previous_image="myapp:v1")
        mock_client.containers.get.return_value = container

        record = manager.rollback("web")

        assert record.success is True
        assert record.previous_image == "myapp:v1"
        assert record.error is None
        container.stop.assert_called_once_with(timeout=10)
        container.remove.assert_called_once()
        mock_client.containers.run.assert_called_once()

    def test_rollback_fails_without_previous_image_label(
        self, manager: RollbackManager, mock_client: MagicMock
    ) -> None:
        container = _make_container()
        container.labels = {}
        mock_client.containers.get.return_value = container

        record = manager.rollback("web")

        assert record.success is False
        assert record.error is not None
        container.stop.assert_not_called()

    def test_rollback_records_added_to_history(
        self, manager: RollbackManager, mock_client: MagicMock
    ) -> None:
        container = _make_container(name="api", previous_image="api:v3")
        mock_client.containers.get.return_value = container

        manager.rollback("api")
        manager.rollback("api")

        assert len(manager.history()) == 2

    def test_history_returns_copy(self, manager: RollbackManager, mock_client: MagicMock) -> None:
        container = _make_container()
        mock_client.containers.get.return_value = container
        manager.rollback("web")

        history = manager.history()
        history.clear()

        assert len(manager.history()) == 1
