"""Guards notification dispatch with per-container rate limiting."""
from __future__ import annotations

from typing import Optional

from deploy_sentinel.notifier import DeployEvent, NotificationChannel
from deploy_sentinel.rate_limiter import RateLimiter


class GuardedNotifier:
    """Wraps a :class:`NotificationChannel` and enforces a :class:`RateLimiter`.

    Notifications that exceed the rate limit are silently dropped and the
    method returns ``False`` so callers can record the suppression.

    Args:
        channel: The underlying notification channel to delegate to.
        limiter: Rate limiter instance; a default one is created if omitted.
    """

    def __init__(
        self,
        channel: NotificationChannel,
        limiter: Optional[RateLimiter] = None,
    ) -> None:
        self._channel = channel
        self._limiter = limiter or RateLimiter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, event: DeployEvent) -> bool:
        """Send *event* through the channel if the rate limit permits.

        Returns:
            ``True`` if the notification was dispatched successfully,
            ``False`` if it was rate-limited or the channel reported failure.
        """
        key = self._rate_key(event)
        if not self._limiter.is_allowed(key):
            return False
        return self._channel.send(event)

    def reset(self, container_id: Optional[str] = None) -> None:
        """Reset the rate-limit state for *container_id* or all containers."""
        self._limiter.reset(container_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rate_key(event: DeployEvent) -> str:
        """Derive a stable string key from the event for rate-limit tracking."""
        return f"{event.container_id}:{event.event_type.value}"
