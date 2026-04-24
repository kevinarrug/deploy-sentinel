"""DeployMonitor: polls Docker containers and reacts to health changes."""
from __future__ import annotations

import logging
import time
from typing import List, Optional

import docker

from deploy_sentinel.alert_policy import PolicyStore
from deploy_sentinel.config import SentinelConfig
from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.notifier import DeployEvent, EventType
from deploy_sentinel.rollback import RollbackManager
from deploy_sentinel.snapshot import SnapshotStore

logger = logging.getLogger(__name__)


class DeployMonitor:
    def __init__(
        self,
        config: SentinelConfig,
        client: Optional[docker.DockerClient] = None,
    ) -> None:
        self.config = config
        self.client = client or docker.from_env()
        self.health_checker = HealthChecker(self.client)
        self.rollback_manager = RollbackManager(self.client)
        self.snapshot_store = SnapshotStore()
        self.metrics = MetricsCollector()
        self.policy_store = PolicyStore()
        self._channels = []

    # ------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover
        logger.info(
            "Starting DeployMonitor (interval=%ds)", self.config.check_interval
        )
        while True:
            self.check_and_act()
            time.sleep(self.config.check_interval)

    def check_and_act(self) -> None:
        try:
            containers = self.client.containers.list(
                filters={"label": self.config.label_filter}
                if self.config.label_filter
                else {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to list containers: %s", exc)
            return

        for container in containers:
            self._process_container(container)

    def _process_container(self, container) -> None:  # noqa: ANN001
        cid = container.id
        now = time.time()
        health = self.health_checker.check(container)

        if health.healthy:
            self.policy_store.reset(cid)
            self.metrics.record_health_ok(cid)
            return

        # --- unhealthy path ---
        self.policy_store.record_failure(cid)
        self.metrics.record_health_failure(cid)
        logger.warning(
            "Container %s unhealthy (consecutive=%d)",
            cid[:12],
            self.policy_store.failure_count(cid),
        )

        if self.policy_store.should_alert(cid, now):
            self.policy_store.mark_alerted(cid, now)
            self._notify(
                DeployEvent(
                    event_type=EventType.HEALTH_FAILURE,
                    container_id=cid,
                    image=health.image,
                    message=health.reason or "health check failed",
                )
            )
            if self.config.rollback_enabled:
                self._try_rollback(container, health.image)

    def _try_rollback(self, container, current_image: str) -> None:  # noqa: ANN001
        success = self.rollback_manager.rollback(container)
        self.metrics.record_rollback(container.id, success=success)
        event_type = EventType.ROLLBACK_SUCCESS if success else EventType.ROLLBACK_FAILURE
        self._notify(
            DeployEvent(
                event_type=event_type,
                container_id=container.id,
                image=current_image,
                message="rollback triggered by health failure",
            )
        )

    def _notify(self, event: DeployEvent) -> None:
        for channel in self._channels:
            try:
                channel.send(event)
            except Exception as exc:  # noqa: BLE001
                logger.error("Notification error (%s): %s", channel, exc)

    def add_channel(self, channel) -> None:  # noqa: ANN001
        self._channels.append(channel)
