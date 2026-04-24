"""Restart policy evaluation for containers under sentinel monitoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class RestartRecord:
    container_id: str
    restart_count: int = 0
    first_restart: Optional[datetime] = None
    last_restart: Optional[datetime] = None

    def record(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.utcnow()
        if self.first_restart is None:
            self.first_restart = now
        self.last_restart = now
        self.restart_count += 1

    def reset(self) -> None:
        self.restart_count = 0
        self.first_restart = None
        self.last_restart = None


@dataclass
class RestartPolicy:
    max_restarts: int = 3
    window_seconds: int = 300  # 5 minutes

    def is_valid(self) -> bool:
        return self.max_restarts > 0 and self.window_seconds > 0

    def should_restart(self, record: RestartRecord, now: Optional[datetime] = None) -> bool:
        """Return True if another restart attempt is permitted."""
        if not self.is_valid():
            return False
        now = now or datetime.utcnow()
        if record.first_restart is not None:
            window_start = now - timedelta(seconds=self.window_seconds)
            if record.first_restart < window_start:
                record.reset()
        return record.restart_count < self.max_restarts


class RestartPolicyStore:
    """Tracks per-container restart records against a shared policy."""

    def __init__(self, policy: Optional[RestartPolicy] = None) -> None:
        self._policy: RestartPolicy = policy or RestartPolicy()
        self._records: Dict[str, RestartRecord] = {}

    def _get_record(self, container_id: str) -> RestartRecord:
        if container_id not in self._records:
            self._records[container_id] = RestartRecord(container_id=container_id)
        return self._records[container_id]

    def should_restart(self, container_id: str, now: Optional[datetime] = None) -> bool:
        record = self._get_record(container_id)
        return self._policy.should_restart(record, now=now)

    def record_restart(self, container_id: str, now: Optional[datetime] = None) -> None:
        self._get_record(container_id).record(now=now)

    def reset(self, container_id: str) -> None:
        if container_id in self._records:
            self._records[container_id].reset()

    def restart_count(self, container_id: str) -> int:
        return self._records.get(container_id, RestartRecord(container_id=container_id)).restart_count
