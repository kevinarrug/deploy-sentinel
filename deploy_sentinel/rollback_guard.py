"""Guard that prevents repeated rollbacks for the same container within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RollbackGuardEntry:
    container_id: str
    rollback_count: int = 0
    last_rollback_at: float = 0.0
    blocked_until: float = 0.0

    def is_blocked(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.monotonic()
        return now < self.blocked_until


class RollbackGuard:
    """Tracks rollback attempts and blocks rapid repeated rollbacks.

    Args:
        max_rollbacks: Maximum number of rollbacks allowed within the window.
        window_seconds: Time window in seconds for counting rollbacks.
        cooldown_seconds: How long to block further rollbacks after limit is reached.
    """

    def __init__(
        self,
        max_rollbacks: int = 3,
        window_seconds: float = 300.0,
        cooldown_seconds: float = 600.0,
    ) -> None:
        if max_rollbacks < 1:
            raise ValueError("max_rollbacks must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")

        self.max_rollbacks = max_rollbacks
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._entries: Dict[str, RollbackGuardEntry] = {}

    def _entry(self, container_id: str) -> RollbackGuardEntry:
        if container_id not in self._entries:
            self._entries[container_id] = RollbackGuardEntry(container_id)
        return self._entries[container_id]

    def is_allowed(self, container_id: str, now: Optional[float] = None) -> bool:
        """Return True if a rollback is allowed for the given container."""
        now = now if now is not None else time.monotonic()
        entry = self._entry(container_id)

        if entry.is_blocked(now):
            return False

        if now - entry.last_rollback_at > self.window_seconds:
            entry.rollback_count = 0

        return entry.rollback_count < self.max_rollbacks

    def record_rollback(self, container_id: str, now: Optional[float] = None) -> None:
        """Record that a rollback occurred for the given container."""
        now = now if now is not None else time.monotonic()
        entry = self._entry(container_id)

        if now - entry.last_rollback_at > self.window_seconds:
            entry.rollback_count = 0

        entry.rollback_count += 1
        entry.last_rollback_at = now

        if entry.rollback_count >= self.max_rollbacks:
            entry.blocked_until = now + self.cooldown_seconds

    def reset(self, container_id: str) -> None:
        """Clear the rollback history for a container."""
        self._entries.pop(container_id, None)
