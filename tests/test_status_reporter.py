"""Tests for StatusReporter and related dataclasses."""
from __future__ import annotations

import pytest

from deploy_sentinel.health_check import ContainerHealth, HealthStatus
from deploy_sentinel.metrics import DeploymentMetric
from deploy_sentinel.status_reporter import ContainerStatusEntry, StatusReport, StatusReporter


def _make_health(
    container_id: str = "abc123",
    name: str = "web",
    image: str = "nginx:latest",
    status: HealthStatus = HealthStatus.HEALTHY,
) -> ContainerHealth:
    return ContainerHealth(container_id=container_id, name=name, image=image, status=status)


def _make_metric(
    container_id: str = "abc123",
    health_failures: int = 0,
    rollback_count: int = 0,
    last_rollback_image: str | None = None,
) -> DeploymentMetric:
    m = DeploymentMetric(container_id=container_id)
    m.health_failures = health_failures
    m.rollback_count = rollback_count
    m.last_rollback_image = last_rollback_image
    return m


@pytest.fixture()
def reporter() -> StatusReporter:
    return StatusReporter()


class TestContainerStatusEntry:
    def test_is_degraded_false_when_healthy(self):
        entry = ContainerStatusEntry(
            container_id="x", name="n", image="i",
            health=HealthStatus.HEALTHY, health_failures=0, rollback_count=0
        )
        assert not entry.is_degraded()

    def test_is_degraded_true_when_unhealthy(self):
        entry = ContainerStatusEntry(
            container_id="x", name="n", image="i",
            health=HealthStatus.UNHEALTHY, health_failures=0, rollback_count=0
        )
        assert entry.is_degraded()

    def test_is_degraded_true_when_failures(self):
        entry = ContainerStatusEntry(
            container_id="x", name="n", image="i",
            health=HealthStatus.HEALTHY, health_failures=2, rollback_count=0
        )
        assert entry.is_degraded()

    def test_to_dict_contains_degraded_key(self):
        entry = ContainerStatusEntry(
            container_id="c1", name="svc", image="img:1",
            health=HealthStatus.HEALTHY, health_failures=0, rollback_count=0
        )
        d = entry.to_dict()
        assert "degraded" in d
        assert d["health"] == HealthStatus.HEALTHY.value


class TestStatusReport:
    def test_counts_are_correct(self):
        healthy = ContainerStatusEntry(
            container_id="a", name="a", image="i",
            health=HealthStatus.HEALTHY, health_failures=0, rollback_count=0
        )
        degraded = ContainerStatusEntry(
            container_id="b", name="b", image="i",
            health=HealthStatus.UNHEALTHY, health_failures=1, rollback_count=0
        )
        report = StatusReport(entries=[healthy, degraded])
        assert report.total == 2
        assert report.healthy_count == 1
        assert report.degraded_count == 1

    def test_to_dict_structure(self):
        report = StatusReport(entries=[])
        d = report.to_dict()
        assert "generated_at" in d
        assert d["total"] == 0
        assert d["containers"] == []


class TestStatusReporter:
    def test_build_report_merges_metrics(self, reporter):
        health = _make_health(container_id="c1")
        metric = _make_metric(container_id="c1", health_failures=3, rollback_count=1,
                              last_rollback_image="nginx:old")
        report = reporter.build_report([health], [metric])
        assert report.total == 1
        entry = report.entries[0]
        assert entry.health_failures == 3
        assert entry.rollback_count == 1
        assert entry.last_rollback_image == "nginx:old"

    def test_build_report_missing_metric_defaults_to_zero(self, reporter):
        health = _make_health(container_id="c2")
        report = reporter.build_report([health], [])
        entry = report.entries[0]
        assert entry.health_failures == 0
        assert entry.rollback_count == 0

    def test_build_report_empty_inputs(self, reporter):
        report = reporter.build_report([], [])
        assert report.total == 0
