"""Persistent event log for deployment and rollback events."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class EventEntry:
    timestamp: str
    event_type: str
    container_id: str
    container_name: str
    image: str
    detail: str

    @classmethod
    def create(
        cls,
        event_type: str,
        container_id: str,
        container_name: str,
        image: str,
        detail: str = "",
    ) -> "EventEntry":
        ts = datetime.now(tz=timezone.utc).isoformat()
        return cls(
            timestamp=ts,
            event_type=event_type,
            container_id=container_id,
            container_name=container_name,
            image=image,
            detail=detail,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EventEntry":
        return cls(**data)


class EventLog:
    """Append-only JSONL event log stored on disk."""

    def __init__(self, log_path: str = "deploy_sentinel_events.jsonl") -> None:
        self.log_path = Path(log_path)

    def append(self, entry: EventEntry) -> None:
        """Append a single event entry to the log file."""
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def read_all(self) -> List[EventEntry]:
        """Return all entries from the log file."""
        if not self.log_path.exists():
            return []
        entries: List[EventEntry] = []
        with self.log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(EventEntry.from_dict(json.loads(line)))
        return entries

    def filter_by_container(self, container_name: str) -> List[EventEntry]:
        """Return entries matching the given container name."""
        return [e for e in self.read_all() if e.container_name == container_name]

    def filter_by_type(self, event_type: str) -> List[EventEntry]:
        """Return entries matching the given event type."""
        return [e for e in self.read_all() if e.event_type == event_type]

    def clear(self) -> None:
        """Remove the log file entirely."""
        if self.log_path.exists():
            os.remove(self.log_path)
