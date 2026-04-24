"""Deployment monitor — polls containers and triggers rollback on failures."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import docker
from docker.models.containers import Container

from deploy_sentinel.alert_policy import PolicyStore
from deploy_sentinel.event_log import EventEntry, EventLog
from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.notifier import DeployEvent, EventType, NotificationChannel
from deploy_sentinel.rollback import RollbackManager
from deploy_sentinel.snapshot import SnapshotStore

logger = logging.getLogger(__name__)


class DeployMonitor:
    """Continuously monitors Docker containers and reacts to health changes."""

    def __init__(
        self,
        client: docker.DockerClient,
        interval: int = 30,
        enable_rollback: bool = True,
        label_filter: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        event_log: Optional[EventLog] = None,
    ) -> None:
        self._client = client
        self.interval = interval
        self.enable_rollback = enable_rollback
        self.label_filter: List[str] = label_filter or []
        self.channels: List[NotificationChannel] = channels or []
        self.event_log = event_log or EventLog()
        self._health_checker = HealthChecker(client)
        self._rollback_manager = RollbackManager(client)
        self._snapshot_store = SnapshotStore()
        self._policy_store = PolicyStore()
        self._metrics = MetricsCollector()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:  # pragma: no cover
        """Block forever, polling containers on each interval."""
        logger.info("DeployMonitor started (interval=%ds)", self.interval)
        while True:
            self.check_and_act()
            time.sleep(self.interval)

    def check_and_act(self) -> None:
        """Single monitoring pass across all relevant containers."""
        containers = self._list_containers()
        for container in containers:
            try:
                self._process_container(container)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error processing container %s: %s", container.name, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _list_containers(self) -> List[Container]:
        filters: dict = {"status": "running"}
        if self.label_filter:
            filters["label"] = self.label_filter
        return self._client.containers.list(filters=filters)  # type: ignore[return-value]

    def _process_container(self, container: Container) -> None:
        health = self._health_checker.check(container)
        policy = self._policy_store.get(container.name)

        if not health.healthy:
            self._metrics.record_health_failure(container.name)
            policy.record_failure()
            self._log_event("health_failure", container, detail=health.detail)
            logger.warning("Unhealthy: %s — %s", container.name, health.detail)

            if self.enable_rollback and not policy.is_valid():
                self._do_rollback(container)
        else:
            policy.reset()
            self._metrics.record_healthy(container.name)

    def _do_rollback(self, container: Container) -> None:
        logger.info("Initiating rollback for %s", container.name)
        success = self._rollback_manager.rollback(container)
        self._metrics.record_rollback(container.name, success=success)
        self._log_event("rollback", container, detail="success" if success else "failed")
        event = DeployEvent(
            event_type=EventType.ROLLBACK,
            container_name=container.name,
            image=container.image.tags[0] if container.image.tags else "unknown",
            success=success,
        )
        for ch in self.channels:
            ch.send(event)

    def _log_event(self, event_type: str, container: Container, detail: str = "") -> None:
        image_tag = container.image.tags[0] if container.image.tags else "unknown"
        entry = EventEntry.create(
            event_type=event_type,
            container_id=container.short_id,
            container_name=container.name,
            image=image_tag,
            detail=detail,
        )
        self.event_log.append(entry)
