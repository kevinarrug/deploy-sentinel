"""Deployment metrics collection and reporting."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DeploymentMetric:
    """A single deployment event metric."""

    container_id: str
    image: str
    timestamp: float = field(default_factory=time.time)
    rollback_count: int = 0
    health_check_failures: int = 0
    last_failure_reason: Optional[str] = None

    @property
    def has_failures(self) -> bool:
        return self.health_check_failures > 0 or self.rollback_count > 0


class MetricsCollector:
    """Collects and stores deployment metrics per container."""

    def __init__(self) -> None:
        self._metrics: Dict[str, DeploymentMetric] = {}

    def record_health_failure(self, container_id: str, image: str, reason: str) -> None:
        """Increment health check failure count for a container."""
        metric = self._get_or_create(container_id, image)
        metric.health_check_failures += 1
        metric.last_failure_reason = reason

    def record_rollback(self, container_id: str, image: str) -> None:
        """Increment rollback count for a container."""
        metric = self._get_or_create(container_id, image)
        metric.rollback_count += 1

    def get(self, container_id: str) -> Optional[DeploymentMetric]:
        """Return the metric record for a container, or None."""
        return self._metrics.get(container_id)

    def all_metrics(self) -> List[DeploymentMetric]:
        """Return all collected metrics."""
        return list(self._metrics.values())

    def reset(self, container_id: str) -> None:
        """Remove metrics for a container (e.g. after successful deploy)."""
        self._metrics.pop(container_id, None)

    def _get_or_create(self, container_id: str, image: str) -> DeploymentMetric:
        if container_id not in self._metrics:
            self._metrics[container_id] = DeploymentMetric(
                container_id=container_id, image=image
            )
        return self._metrics[container_id]

    def summary(self) -> Dict[str, int]:
        """Return aggregate counts across all containers."""
        total_failures = sum(m.health_check_failures for m in self._metrics.values())
        total_rollbacks = sum(m.rollback_count for m in self._metrics.values())
        return {
            "containers_tracked": len(self._metrics),
            "total_health_failures": total_failures,
            "total_rollbacks": total_rollbacks,
        }
