"""Alert policy: defines thresholds and suppression rules for notifications."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AlertPolicy:
    """Controls when alerts are emitted for a container."""

    # Number of consecutive failures before an alert is sent
    failure_threshold: int = 3
    # Minimum seconds between repeated alerts for the same container
    cooldown_seconds: int = 300

    def is_valid(self) -> bool:
        return self.failure_threshold >= 1 and self.cooldown_seconds >= 0


@dataclass
class PolicyStore:
    """Holds per-container failure counts and last-alert timestamps."""

    policy: AlertPolicy = field(default_factory=AlertPolicy)
    _failure_counts: Dict[str, int] = field(default_factory=dict, init=False)
    _last_alerted: Dict[str, float] = field(default_factory=dict, init=False)

    def record_failure(self, container_id: str) -> None:
        """Increment the failure counter for *container_id*."""
        self._failure_counts[container_id] = (
            self._failure_counts.get(container_id, 0) + 1
        )

    def reset(self, container_id: str) -> None:
        """Clear failure state after a container recovers."""
        self._failure_counts.pop(container_id, None)
        self._last_alerted.pop(container_id, None)

    def should_alert(self, container_id: str, now: float) -> bool:
        """Return True when an alert should be emitted right now."""
        count = self._failure_counts.get(container_id, 0)
        if count < self.policy.failure_threshold:
            return False
        last = self._last_alerted.get(container_id)
        if last is not None and (now - last) < self.policy.cooldown_seconds:
            return False
        return True

    def mark_alerted(self, container_id: str, now: float) -> None:
        """Record that an alert was just sent for *container_id*."""
        self._last_alerted[container_id] = now

    def failure_count(self, container_id: str) -> int:
        return self._failure_counts.get(container_id, 0)
