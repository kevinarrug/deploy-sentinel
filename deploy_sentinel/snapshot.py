"""Container snapshot storage and change detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from deploy_sentinel.env_diff import EnvDiff, compute_env_diff


@dataclass
class ContainerSnapshot:
    container_id: str
    image: str
    image_tag: str
    labels: Dict[str, str] = field(default_factory=dict)
    env: List[str] = field(default_factory=list)
    status: str = "running"

    def __post_init__(self) -> None:
        self.container_id = self.container_id[:12]

    def has_changed(self, other: "ContainerSnapshot") -> bool:
        """Return True if any tracked field differs from *other*."""
        return (
            self.image != other.image
            or self.image_tag != other.image_tag
            or self.labels != other.labels
            or self.status != other.status
            or compute_env_diff(self.env, other.env).has_changes
        )

    def env_diff(self, other: "ContainerSnapshot") -> EnvDiff:
        """Return the env diff between this snapshot and *other*."""
        return compute_env_diff(self.env, other.env)


class SnapshotStore:
    """In-memory store for the most-recent snapshot of each container."""

    def __init__(self) -> None:
        self._store: Dict[str, ContainerSnapshot] = {}

    def get(self, container_id: str) -> Optional[ContainerSnapshot]:
        return self._store.get(container_id[:12])

    def save(self, snapshot: ContainerSnapshot) -> None:
        self._store[snapshot.container_id] = snapshot

    def delete(self, container_id: str) -> None:
        self._store.pop(container_id[:12], None)

    def all(self) -> List[ContainerSnapshot]:
        return list(self._store.values())

    def __len__(self) -> int:
        return len(self._store)
