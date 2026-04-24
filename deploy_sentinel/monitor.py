"""Deployment monitor: health-checks containers and triggers rollbacks."""
from __future__ import annotations

import logging
from typing import Optional

import docker  # type: ignore

from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.metrics import MetricsCollector
from deploy_sentinel.notifier import DeployEvent, EventType, NotificationChannel
from deploy_sentinel.rollback import RollbackManager

logger = logging.getLogger(__name__)


class DeployMonitor:
    """Watches a Docker container and rolls back on sustained health failures."""

    def __init__(
        self,
        container_id: str,
        client: Optional[docker.DockerClient] = None,
        failure_threshold: int = 3,
        channel: Optional[NotificationChannel] = None,
    ) -> None:
        self.container_id = container_id
        self._client = client or docker.from_env()
        self._checker = HealthChecker(self._client)
        self._rollback_mgr = RollbackManager(self._client)
        self._metrics = MetricsCollector()
        self._failure_threshold = failure_threshold
        self._channel = channel

    def check_and_act(self) -> bool:
        """Perform a health check and roll back if threshold is exceeded.

        Returns True if the container is healthy, False otherwise.
        """
        container = self._client.containers.get(self.container_id)
        health = self._checker.check(container)

        if health.is_healthy:
            self._metrics.reset(self.container_id)
            return True

        reason = health.status.value
        image = container.image.tags[0] if container.image.tags else container.image.id
        self._metrics.record_health_failure(self.container_id, image, reason)

        metric = self._metrics.get(self.container_id)
        logger.warning(
            "Container %s unhealthy (%s). Failures: %d/%d",
            self.container_id,
            reason,
            metric.health_check_failures,
            self._failure_threshold,
        )

        if metric.health_check_failures >= self._failure_threshold:
            self._trigger_rollback(container, image)

        return False

    def _trigger_rollback(self, container, current_image: str) -> None:
        """Attempt rollback and notify via channel if configured."""
        logger.error(
            "Failure threshold reached for %s. Initiating rollback.",
            self.container_id,
        )
        success = self._rollback_mgr.rollback(container)
        self._metrics.record_rollback(self.container_id, current_image)

        if self._channel is not None:
            event = DeployEvent(
                event_type=EventType.ROLLBACK_SUCCESS if success else EventType.ROLLBACK_FAILED,
                container_id=self.container_id,
                image=current_image,
                message=(
                    f"Rollback {'succeeded' if success else 'failed'} for {self.container_id}"
                ),
            )
            self._channel.send(event)
