"""Tests for the health check module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import DockerException, NotFound

from deploy_sentinel.health_check import ContainerHealth, HealthChecker, HealthStatus


def _make_container(name="web", cid="abc123", state=None):
    container = MagicMock()
    container.id = cid
    container.name = name
    container.attrs = {"State": state or {"Running": True, "ExitCode": 0}}
    return container


@pytest.fixture()
def mock_client():
    return MagicMock()


@pytest.fixture()
def checker(mock_client):
    return HealthChecker(docker_client=mock_client)


class TestContainerHealth:
    def test_is_healthy_true(self):
        ch = ContainerHealth("id", "app", HealthStatus.HEALTHY)
        assert ch.is_healthy is True

    def test_is_healthy_false(self):
        ch = ContainerHealth("id", "app", HealthStatus.UNHEALTHY)
        assert ch.is_healthy is False

    def test_checked_at_defaults_to_now(self):
        before = datetime.utcnow()
        ch = ContainerHealth("id", "app", HealthStatus.HEALTHY)
        assert ch.checked_at >= before


class TestHealthChecker:
    def test_check_healthy_container(self, checker, mock_client):
        state = {"Running": True, "ExitCode": 0, "Health": {"Status": "healthy"}}
        mock_client.containers.get.return_value = _make_container(state=state)

        result = checker.check("web")

        assert result.status == HealthStatus.HEALTHY
        assert result.is_healthy is True

    def test_check_unhealthy_container(self, checker, mock_client):
        state = {"Running": True, "ExitCode": 0, "Health": {"Status": "unhealthy"}}
        mock_client.containers.get.return_value = _make_container(state=state)

        result = checker.check("web")

        assert result.status == HealthStatus.UNHEALTHY

    def test_check_starting_container(self, checker, mock_client):
        state = {"Running": True, "ExitCode": 0, "Health": {"Status": "starting"}}
        mock_client.containers.get.return_value = _make_container(state=state)

        result = checker.check("web")

        assert result.status == HealthStatus.STARTING

    def test_check_running_no_healthcheck(self, checker, mock_client):
        state = {"Running": True, "ExitCode": 0}
        mock_client.containers.get.return_value = _make_container(state=state)

        result = checker.check("web")

        assert result.status == HealthStatus.HEALTHY

    def test_check_stopped_container(self, checker, mock_client):
        state = {"Running": False, "ExitCode": 1}
        mock_client.containers.get.return_value = _make_container(state=state)

        result = checker.check("web")

        assert result.status == HealthStatus.UNHEALTHY
        assert result.exit_code == 1

    def test_check_not_found(self, checker, mock_client):
        mock_client.containers.get.side_effect = NotFound("not found")

        result = checker.check("missing")

        assert result.status == HealthStatus.NOT_FOUND
        assert result.error == "Container not found"

    def test_check_docker_exception(self, checker, mock_client):
        mock_client.containers.get.side_effect = DockerException("daemon error")

        result = checker.check("web")

        assert result.status == HealthStatus.UNKNOWN
        assert "daemon error" in result.error
