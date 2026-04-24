"""Status reporter: aggregates container health and metrics into a summary report."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from deploy_sentinel.health_check import ContainerHealth, HealthStatus
from deploy_sentinel.metrics import DeploymentMetric


@dataclass
class ContainerStatusEntry:
    container_id: str
    name: str
    image: str
    health: HealthStatus
    health_failures: int
    rollback_count: int
    last_rollback_image: Optional[str] = None

    def is_degraded(self) -> bool:
        return self.health != HealthStatus.HEALTHY or self.health_failures > 0

    def to_dict(self) -> dict:
        return {
            "container_id": self.container_id,
            "name": self.name,
            "image": self.image,
            "health": self.health.value,
            "health_failures": self.health_failures,
            "rollback_count": self.rollback_count,
            "last_rollback_image": self.last_rollback_image,
            "degraded": self.is_degraded(),
        }


@dataclass
class StatusReport:
    generated_at: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    entries: List[ContainerStatusEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def degraded_count(self) -> int:
        return sum(1 for e in self.entries if e.is_degraded())

    @property
    def healthy_count(self) -> int:
        return self.total - self.degraded_count

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "total": self.total,
            "healthy": self.healthy_count,
            "degraded": self.degraded_count,
            "containers": [e.to_dict() for e in self.entries],
        }


class StatusReporter:
    """Builds a StatusReport from health and metrics data."""

    def build_report(
        self,
        health_results: List[ContainerHealth],
        metrics: List[DeploymentMetric],
    ) -> StatusReport:
        metrics_by_id = {m.container_id: m for m in metrics}
        entries: List[ContainerStatusEntry] = []

        for ch in health_results:
            metric = metrics_by_id.get(ch.container_id)
            entries.append(
                ContainerStatusEntry(
                    container_id=ch.container_id,
                    name=ch.name,
                    image=ch.image,
                    health=ch.status,
                    health_failures=metric.health_failures if metric else 0,
                    rollback_count=metric.rollback_count if metric else 0,
                    last_rollback_image=metric.last_rollback_image if metric else None,
                )
            )

        return StatusReport(entries=entries)
