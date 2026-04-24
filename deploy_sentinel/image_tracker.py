"""Tracks deployed image versions per container for audit and rollback support."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ImageRecord:
    """A single record of an image deployed to a container."""

    container_id: str
    container_name: str
    image: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "container_id": self.container_id,
            "container_name": self.container_name,
            "image": self.image,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageRecord":
        return cls(
            container_id=data["container_id"],
            container_name=data["container_name"],
            image=data["image"],
            timestamp=data["timestamp"],
        )


class ImageTracker:
    """Maintains a history of images seen per container."""

    def __init__(self, max_history: int = 10) -> None:
        self._max_history = max_history
        self._history: Dict[str, List[ImageRecord]] = {}

    def record(self, container_id: str, container_name: str, image: str) -> None:
        """Record a new image for the given container."""
        records = self._history.setdefault(container_id, [])
        if records and records[-1].image == image:
            return
        records.append(ImageRecord(container_id, container_name, image))
        if len(records) > self._max_history:
            self._history[container_id] = records[-self._max_history :]

    def latest(self, container_id: str) -> Optional[ImageRecord]:
        """Return the most recently recorded image for a container."""
        records = self._history.get(container_id)
        return records[-1] if records else None

    def previous(self, container_id: str) -> Optional[ImageRecord]:
        """Return the image recorded before the current one, if any."""
        records = self._history.get(container_id)
        return records[-2] if records and len(records) >= 2 else None

    def history(self, container_id: str) -> List[ImageRecord]:
        """Return full image history for a container (oldest first)."""
        return list(self._history.get(container_id, []))

    def clear(self, container_id: str) -> None:
        """Remove all history for a container."""
        self._history.pop(container_id, None)
