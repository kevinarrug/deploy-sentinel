"""Notification system for deployment events and rollback alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Protocol

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    DEPLOY_SUCCESS = "deploy_success"
    DEPLOY_FAILURE = "deploy_failure"
    ROLLBACK_TRIGGERED = "rollback_triggered"
    ROLLBACK_SUCCESS = "rollback_success"
    ROLLBACK_FAILURE = "rollback_failure"
    HEALTH_CHECK_FAILED = "health_check_failed"


@dataclass
class DeployEvent:
    event_type: EventType
    container_id: str
    container_name: str
    image: str
    message: str
    previous_image: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class NotificationChannel(Protocol):
    """Protocol that all notification channels must implement."""

    def send(self, event: DeployEvent) -> bool:
        """Send a notification. Returns True on success."""
        ...


class LoggingChannel:
    """Notification channel that logs events using Python logging."""

    def __init__(self, level: int = logging.INFO) -> None:
        self.level = level

    def send(self, event: DeployEvent) -> bool:
        logger.log(
            self.level,
            "[%s] container=%s image=%s — %s",
            event.event_type.value,
            event.container_name,
            event.image,
            event.message,
        )
        return True


class Notifier:
    """Dispatches deployment events to one or more notification channels."""

    def __init__(self, channels: Optional[List[NotificationChannel]] = None) -> None:
        self._channels: List[NotificationChannel] = channels or [LoggingChannel()]

    def add_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    def notify(self, event: DeployEvent) -> List[bool]:
        """Send event to all channels. Returns list of per-channel success flags."""
        results: List[bool] = []
        for channel in self._channels:
            try:
                results.append(channel.send(event))
            except Exception as exc:  # noqa: BLE001
                logger.error("Notification channel %r raised: %s", channel, exc)
                results.append(False)
        return results

    def notify_rollback(self, container_name: str, container_id: str,
                        image: str, previous_image: str, success: bool) -> None:
        event_type = EventType.ROLLBACK_SUCCESS if success else EventType.ROLLBACK_FAILURE
        msg = (
            f"Rolled back to {previous_image}" if success
            else f"Rollback to {previous_image} FAILED"
        )
        self.notify(DeployEvent(
            event_type=event_type,
            container_id=container_id,
            container_name=container_name,
            image=image,
            previous_image=previous_image,
            message=msg,
        ))
