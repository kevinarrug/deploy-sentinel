"""Orchestrates health checking and triggers rollback with notifications."""

from __future__ import annotations

import logging
from typing import Optional

from deploy_sentinel.health_check import HealthChecker
from deploy_sentinel.notifier import DeployEvent, EventType, Notifier
from deploy_sentinel.rollback import RollbackManager

logger = logging.getLogger(__name__)


class DeployMonitor:
    """Ties together health checking, rollback, and notifications."""

    def __init__(
        self,
        checker: HealthChecker,
        rollback_manager: RollbackManager,
        notifier: Optional[Notifier] = None,
        failure_threshold: int = 3,
    ) -> None:
        self._checker = checker
        self._rollback = rollback_manager
        self._notifier = notifier or Notifier()
        self.failure_threshold = failure_threshold
        self._consecutive_failures: dict[str, int] = {}

    def check_and_act(self, container_id: str) -> bool:
        """Check container health; trigger rollback when threshold is reached.

        Returns True if the container is healthy, False otherwise.
        """
        health = self._checker.check(container_id)
        name = health.name
        image = health.image

        if health.healthy:
            self._consecutive_failures[container_id] = 0
            logger.debug("Container %s is healthy.", name)
            return True

        count = self._consecutive_failures.get(container_id, 0) + 1
        self._consecutive_failures[container_id] = count
        logger.warning(
            "Container %s unhealthy (%d/%d).", name, count, self.failure_threshold
        )

        self._notifier.notify(DeployEvent(
            event_type=EventType.HEALTH_CHECK_FAILED,
            container_id=container_id,
            container_name=name,
            image=image,
            message=f"Health check failed ({count}/{self.failure_threshold})",
        ))

        if count >= self.failure_threshold:
            self._consecutive_failures[container_id] = 0
            self._trigger_rollback(container_id, name, image)

        return False

    def _trigger_rollback(self, container_id: str, name: str, image: str) -> None:
        self._notifier.notify(DeployEvent(
            event_type=EventType.ROLLBACK_TRIGGERED,
            container_id=container_id,
            container_name=name,
            image=image,
            message="Failure threshold reached — initiating rollback",
        ))
        previous = self._rollback.get_previous_image(container_id)
        success = self._rollback.rollback(container_id)
        self._notifier.notify_rollback(
            container_name=name,
            container_id=container_id,
            image=image,
            previous_image=previous or "unknown",
            success=success,
        )
