"""Tracks inter-container dependencies for ordered rollback and health checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyNode:
    container_id: str
    name: str
    depends_on: List[str] = field(default_factory=list)  # list of container names

    def to_dict(self) -> dict:
        return {
            "container_id": self.container_id,
            "name": self.name,
            "depends_on": list(self.depends_on),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyNode":
        return cls(
            container_id=data["container_id"],
            name=data["name"],
            depends_on=list(data.get("depends_on", [])),
        )


class CyclicDependencyError(Exception):
    """Raised when a cycle is detected in the dependency graph."""


class DependencyGraph:
    """Directed graph of container dependencies."""

    def __init__(self) -> None:
        self._nodes: Dict[str, DependencyNode] = {}

    def register(self, node: DependencyNode) -> None:
        self._nodes[node.name] = node

    def remove(self, name: str) -> None:
        self._nodes.pop(name, None)

    def get(self, name: str) -> Optional[DependencyNode]:
        return self._nodes.get(name)

    def dependents_of(self, name: str) -> List[str]:
        """Return names of containers that directly depend on *name*."""
        return [
            n.name for n in self._nodes.values() if name in n.depends_on
        ]

    def rollback_order(self) -> List[str]:
        """Return a topological order suitable for rollback (dependents first).

        Raises CyclicDependencyError if a cycle is detected.
        """
        visited: Set[str] = set()
        stack: Set[str] = set()
        order: List[str] = []

        def visit(name: str) -> None:
            if name in stack:
                raise CyclicDependencyError(f"Cycle detected at '{name}'")
            if name in visited:
                return
            stack.add(name)
            for dep in self._nodes.get(name, DependencyNode("", name)).depends_on:
                if dep in self._nodes:
                    visit(dep)
            stack.discard(name)
            visited.add(name)
            order.append(name)

        for node_name in list(self._nodes):
            visit(node_name)

        # Reverse so dependents come first
        order.reverse()
        return order

    def all_names(self) -> List[str]:
        return list(self._nodes.keys())
