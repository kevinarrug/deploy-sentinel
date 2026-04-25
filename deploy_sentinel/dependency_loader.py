"""Builds a DependencyGraph from Docker container labels.

Containers may declare dependencies via the label::

    deploy-sentinel.depends-on=db,cache
"""
from __future__ import annotations

from typing import List

from deploy_sentinel.dependency_graph import DependencyGraph, DependencyNode

_LABEL = "deploy-sentinel.depends-on"


def _container_name(container) -> str:
    names = getattr(container, "name", None)
    if names:
        return names.lstrip("/")
    attrs = getattr(container, "attrs", {})
    raw = attrs.get("Name", "") or ""
    return raw.lstrip("/")


def _parse_depends_on(label_value: str) -> List[str]:
    """Split a comma-separated depends-on label into a list of names."""
    if not label_value:
        return []
    return [part.strip() for part in label_value.split(",") if part.strip()]


def build_graph_from_containers(containers) -> DependencyGraph:
    """Inspect *containers* (Docker SDK objects) and return a DependencyGraph."""
    graph = DependencyGraph()
    for container in containers:
        labels: dict = getattr(container, "labels", {}) or {}
        depends_on = _parse_depends_on(labels.get(_LABEL, ""))
        node = DependencyNode(
            container_id=container.id,
            name=_container_name(container),
            depends_on=depends_on,
        )
        graph.register(node)
    return graph
