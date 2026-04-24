"""Container state snapshot — captures and persists container image tags
so the monitor can detect image changes between polling cycles."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContainerSnapshot:
    """Immutable record of a container's image at a point in time."""

    container_id: str
    container_name: str
    image: str
    image_id: str

    def has_changed(self, other: "ContainerSnapshot") -> bool:
        """Return True when the image tag or digest differs from *other*."""
        return self.image != other.image or self.image_id != other.image_id


@dataclass
class SnapshotStore:
    """Persist snapshots to a JSON file so state survives process restarts."""

    path: str
    _data: Dict[str, dict] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, container_id: str) -> Optional[ContainerSnapshot]:
        """Return the stored snapshot for *container_id*, or ``None``."""
        raw = self._data.get(container_id)
        if raw is None:
            return None
        return ContainerSnapshot(**raw)

    def save(self, snapshot: ContainerSnapshot) -> None:
        """Upsert *snapshot* and flush to disk."""
        self._data[snapshot.container_id] = asdict(snapshot)
        self._flush()

    def remove(self, container_id: str) -> None:
        """Delete the snapshot for *container_id* if it exists."""
        if container_id in self._data:
            del self._data[container_id]
            self._flush()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self.path):
            logger.debug("Snapshot file %s not found; starting empty.", self.path)
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
            logger.debug("Loaded %d snapshot(s) from %s.", len(self._data), self.path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load snapshot file %s: %s", self.path, exc)

    def _flush(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError as exc:
            logger.error("Failed to write snapshot file %s: %s", self.path, exc)
