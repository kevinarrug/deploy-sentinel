"""Rate limiting for notifications and rollback actions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RateLimitEntry:
    """Tracks call count and window start for a single key."""

    window_start: float
    count: int = 0


@dataclass
class RateLimiter:
    """Token-bucket-style rate limiter keyed by an arbitrary string.

    Args:
        max_calls: Maximum number of calls allowed within *window_seconds*.
        window_seconds: Duration of the sliding window in seconds.
    """

    max_calls: int = 5
    window_seconds: float = 60.0
    _entries: Dict[str, RateLimitEntry] = field(default_factory=dict, init=False, repr=False)

    def is_allowed(self, key: str) -> bool:
        """Return True if the action identified by *key* is within the rate limit."""
        now = time.monotonic()
        entry = self._entries.get(key)

        if entry is None or (now - entry.window_start) >= self.window_seconds:
            self._entries[key] = RateLimitEntry(window_start=now, count=1)
            return True

        if entry.count < self.max_calls:
            entry.count += 1
            return True

        return False

    def remaining(self, key: str) -> int:
        """Return the number of calls still allowed in the current window."""
        now = time.monotonic()
        entry = self._entries.get(key)

        if entry is None or (now - entry.window_start) >= self.window_seconds:
            return self.max_calls

        return max(0, self.max_calls - entry.count)

    def reset(self, key: Optional[str] = None) -> None:
        """Clear rate-limit state for *key*, or all keys if *key* is None."""
        if key is None:
            self._entries.clear()
        else:
            self._entries.pop(key, None)
