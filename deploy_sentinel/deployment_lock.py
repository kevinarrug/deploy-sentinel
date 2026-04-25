"""Deployment lock to prevent concurrent rollbacks or deploys."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LockEntry:
    owner: str
    acquired_at: float = field(default_factory=time.monotonic)
    ttl: float = 60.0  # seconds

    def is_expired(self) -> bool:
        return (time.monotonic() - self.acquired_at) > self.ttl


class DeploymentLock:
    """Thread-safe deployment lock with TTL-based expiry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entry: Optional[LockEntry] = None

    def acquire(self, owner: str, ttl: float = 60.0) -> bool:
        """Try to acquire the lock for *owner*. Returns True on success."""
        with self._lock:
            if self._entry is not None and not self._entry.is_expired():
                return False
            self._entry = LockEntry(owner=owner, ttl=ttl)
            return True

    def release(self, owner: str) -> bool:
        """Release the lock if *owner* holds it. Returns True on success."""
        with self._lock:
            if self._entry is None:
                return False
            if self._entry.owner != owner:
                return False
            self._entry = None
            return True

    def is_locked(self) -> bool:
        """Return True if the lock is currently held (and not expired)."""
        with self._lock:
            if self._entry is None:
                return False
            if self._entry.is_expired():
                self._entry = None
                return False
            return True

    def current_owner(self) -> Optional[str]:
        """Return the owner of the current lock, or None."""
        with self._lock:
            if self._entry is None or self._entry.is_expired():
                return None
            return self._entry.owner

    def force_release(self) -> None:
        """Unconditionally clear the lock (admin / test use)."""
        with self._lock:
            self._entry = None
