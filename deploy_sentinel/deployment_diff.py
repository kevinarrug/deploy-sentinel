"""Compute and represent the diff between two container snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from deploy_sentinel.snapshot import ContainerSnapshot


@dataclass
class DeploymentDiff:
    """Describes what changed between two snapshots of the same container."""

    container_id: str
    container_name: str
    image_changed: bool = False
    previous_image: Optional[str] = None
    current_image: Optional[str] = None
    labels_added: Dict[str, str] = field(default_factory=dict)
    labels_removed: Dict[str, str] = field(default_factory=dict)
    labels_changed: Dict[str, tuple] = field(default_factory=dict)  # key -> (old, new)
    env_added: List[str] = field(default_factory=list)
    env_removed: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Return True if any field reports a change."""
        return (
            self.image_changed
            or bool(self.labels_added)
            or bool(self.labels_removed)
            or bool(self.labels_changed)
            or bool(self.env_added)
            or bool(self.env_removed)
        )

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        parts: List[str] = []
        if self.image_changed:
            parts.append(f"image {self.previous_image!r} -> {self.current_image!r}")
        if self.labels_added or self.labels_removed or self.labels_changed:
            parts.append("labels changed")
        if self.env_added or self.env_removed:
            parts.append("env changed")
        if not parts:
            return f"{self.container_name}: no changes"
        return f"{self.container_name}: " + ", ".join(parts)


def compute_diff(previous: ContainerSnapshot, current: ContainerSnapshot) -> DeploymentDiff:
    """Compute the diff between *previous* and *current* snapshots.

    Both snapshots must belong to the same container (same ``container_id``).
    """
    diff = DeploymentDiff(
        container_id=current.container_id,
        container_name=current.name,
    )

    if previous.image_tag != current.image_tag:
        diff.image_changed = True
        diff.previous_image = previous.image_tag
        diff.current_image = current.image_tag

    prev_labels: Dict[str, str] = previous.labels or {}
    curr_labels: Dict[str, str] = current.labels or {}

    for key, value in curr_labels.items():
        if key not in prev_labels:
            diff.labels_added[key] = value
        elif prev_labels[key] != value:
            diff.labels_changed[key] = (prev_labels[key], value)

    for key, value in prev_labels.items():
        if key not in curr_labels:
            diff.labels_removed[key] = value

    prev_env: List[str] = previous.env or []
    curr_env: List[str] = current.env or []
    prev_set = set(prev_env)
    curr_set = set(curr_env)
    diff.env_added = sorted(curr_set - prev_set)
    diff.env_removed = sorted(prev_set - curr_set)

    return diff
