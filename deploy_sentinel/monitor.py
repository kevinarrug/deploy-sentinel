"""DeployMonitor — polls Docker containers, checks health, and triggers
rollbacks when a deployment goes bad.

Now also detects image changes between polling cycles using
:class:`~deploy_sentinel.snapshot.SnapshotStore`.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import docker

from deploy_sentinel.config import SentinelConfig
from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.notifier import DeployEvent, EventType
from deploy_sentinel.rollback import RollbackManager
from deploy_sentinel.snapshot import ContainerSnapshot, SnapshotStore

logger = logging.getLogger(__name__)


class DeployMonitor:
    """Orchestrates health-checking, snapshot diffing, rollback, and metrics."""

    def __init__(
        self,
        config: SentinelConfig,
        client: Optional[docker.DockerClient] = None,
    ) -> None:
        self.config = config
        self.client = client or docker.from_env()
        self.health_checker = HealthChecker(self.client)
        self.rollback_manager = RollbackManager(self.client)
        self.metrics = MetricsCollector()
        self.snapshot_store = SnapshotStore(path=config.snapshot_path)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:  # pragma: no cover
        """Block forever, polling at *config.interval* seconds."""
        logger.info(
            "DeployMonitor started (interval=%ds, rollback=%s).",
            self.config.interval,
            not self.config.no_rollback,
        )
        while True:
            self.check_and_act()
            time.sleep(self.config.interval)

    def check_and_act(self) -> None:
        """Single polling cycle across all monitored containers."""
        containers = self.client.containers.list(
            filters={"name": self.config.container_names} if self.config.container_names else {}
        )
        for container in containers:
            self._process_container(container)

    # ------------------------------------------------------------------
    # Per-container logic
    # ------------------------------------------------------------------

    def _process_container(self, container) -> None:  # type: ignore[override]
        name = container.name
        cid = container.id

        # --- snapshot / image-change detection ---
        current = ContainerSnapshot(
            container_id=cid,
            container_name=name,
            image=container.image.tags[0] if container.image.tags else "",
            image_id=container.image.id,
        )
        previous = self.snapshot_store.get(cid)
        if previous is not None and previous.has_changed(current):
            logger.info(
                "Image change detected for %s: %s → %s",
                name,
                previous.image,
                current.image,
            )
            self.metrics.record_deploy(name, current.image)
        self.snapshot_store.save(current)

        # --- health check ---
        health = self.health_checker.check(container)
        self.metrics.record_health_check(name, healthy=health.healthy)

        if not health.healthy:
            logger.warning("Container %s is unhealthy: %s", name, health.reason)
            self.metrics.record_health_failure(name)
            if not self.config.no_rollback:
                self._trigger_rollback(container, health.reason)

    def _trigger_rollback(self, container, reason: str) -> None:  # type: ignore[override]
        name = container.name
        logger.info("Initiating rollback for %s (reason: %s).", name, reason)
        success = self.rollback_manager.rollback(container)
        self.metrics.record_rollback(name, success=success)
        event = DeployEvent(
            event_type=EventType.ROLLBACK_SUCCESS if success else EventType.ROLLBACK_FAILURE,
            container_name=name,
            detail=reason,
        )
        for channel in self.config.notification_channels:
            channel.send(event)
