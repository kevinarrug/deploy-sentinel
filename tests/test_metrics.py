"""Tests for deploy_sentinel.metrics."""
import pytest

from deploy_sentinel.metrics import DeploymentMetric, MetricsCollector

CONTAINER_A = "abc123"
CONTAINER_B = "def456"
IMAGE = "myapp:1.0"


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


class TestDeploymentMetric:
    def test_has_failures_false_by_default(self):
        m = DeploymentMetric(container_id=CONTAINER_A, image=IMAGE)
        assert m.has_failures is False

    def test_has_failures_true_when_health_failure(self):
        m = DeploymentMetric(container_id=CONTAINER_A, image=IMAGE, health_check_failures=1)
        assert m.has_failures is True

    def test_has_failures_true_when_rollback(self):
        m = DeploymentMetric(container_id=CONTAINER_A, image=IMAGE, rollback_count=2)
        assert m.has_failures is True


class TestMetricsCollector:
    def test_get_returns_none_for_unknown_container(self, collector):
        assert collector.get(CONTAINER_A) is None

    def test_record_health_failure_creates_metric(self, collector):
        collector.record_health_failure(CONTAINER_A, IMAGE, "unhealthy")
        metric = collector.get(CONTAINER_A)
        assert metric is not None
        assert metric.health_check_failures == 1
        assert metric.last_failure_reason == "unhealthy"

    def test_record_health_failure_increments(self, collector):
        collector.record_health_failure(CONTAINER_A, IMAGE, "timeout")
        collector.record_health_failure(CONTAINER_A, IMAGE, "crash")
        assert collector.get(CONTAINER_A).health_check_failures == 2
        assert collector.get(CONTAINER_A).last_failure_reason == "crash"

    def test_record_rollback_increments(self, collector):
        collector.record_rollback(CONTAINER_A, IMAGE)
        collector.record_rollback(CONTAINER_A, IMAGE)
        assert collector.get(CONTAINER_A).rollback_count == 2

    def test_reset_removes_metric(self, collector):
        collector.record_rollback(CONTAINER_A, IMAGE)
        collector.reset(CONTAINER_A)
        assert collector.get(CONTAINER_A) is None

    def test_reset_unknown_container_is_noop(self, collector):
        collector.reset("nonexistent")  # should not raise

    def test_all_metrics_returns_all(self, collector):
        collector.record_health_failure(CONTAINER_A, IMAGE, "err")
        collector.record_rollback(CONTAINER_B, "myapp:2.0")
        assert len(collector.all_metrics()) == 2

    def test_summary_aggregates_correctly(self, collector):
        collector.record_health_failure(CONTAINER_A, IMAGE, "err1")
        collector.record_health_failure(CONTAINER_A, IMAGE, "err2")
        collector.record_rollback(CONTAINER_A, IMAGE)
        collector.record_rollback(CONTAINER_B, "myapp:2.0")
        summary = collector.summary()
        assert summary["containers_tracked"] == 2
        assert summary["total_health_failures"] == 2
        assert summary["total_rollbacks"] == 2

    def test_summary_empty_collector(self, collector):
        summary = collector.summary()
        assert summary == {
            "containers_tracked": 0,
            "total_health_failures": 0,
            "total_rollbacks": 0,
        }
