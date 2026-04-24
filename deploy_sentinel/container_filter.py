"""Filtering logic to select containers for monitoring based on labels and names."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Optional


@dataclass
class FilterConfig:
    """Criteria used to include or exclude containers from monitoring."""

    required_labels: List[str] = field(default_factory=list)
    """Container must have ALL of these label keys to be included."""

    name_patterns: List[str] = field(default_factory=list)
    """Glob patterns matched against container name; empty list means match all."""

    excluded_names: List[str] = field(default_factory=list)
    """Exact container names that should always be skipped."""


def _container_name(container) -> str:
    """Return the primary name of a Docker container object (strips leading slash)."""
    names = container.attrs.get("Name") or (container.attrs.get("Names") or [""])[0]
    if isinstance(names, list):
        names = names[0]
    return names.lstrip("/")


def matches_filter(container, config: FilterConfig) -> bool:
    """Return True if *container* satisfies every criterion in *config*."""
    name = _container_name(container)

    if name in config.excluded_names:
        return False

    labels: dict = container.labels if hasattr(container, "labels") else {}
    for required in config.required_labels:
        if required not in labels:
            return False

    if config.name_patterns:
        if not any(fnmatch(name, pat) for pat in config.name_patterns):
            return False

    return True


class ContainerFilter:
    """Applies a :class:`FilterConfig` to a list of Docker containers."""

    def __init__(self, config: Optional[FilterConfig] = None) -> None:
        self.config: FilterConfig = config or FilterConfig()

    def apply(self, containers: list) -> list:
        """Return only those containers that pass the filter."""
        return [c for c in containers if matches_filter(c, self.config)]
