"""Detect and summarize environment variable changes between container snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvDiff:
    """Result of comparing two sets of environment variables."""

    added: Dict[str, str] = field(default_factory=dict)
    removed: Dict[str, str] = field(default_factory=dict)
    changed: Dict[str, tuple] = field(default_factory=dict)  # key -> (old, new)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def summary(self) -> str:
        parts: List[str] = []
        if self.added:
            parts.append(f"added={list(self.added.keys())}")
        if self.removed:
            parts.append(f"removed={list(self.removed.keys())}")
        if self.changed:
            parts.append(f"changed={list(self.changed.keys())}")
        return "; ".join(parts) if parts else "no changes"


def _parse_env_list(env_list: Optional[List[str]]) -> Dict[str, str]:
    """Convert a list of 'KEY=VALUE' strings to a dict."""
    result: Dict[str, str] = {}
    for entry in (env_list or []):
        if "=" in entry:
            key, _, value = entry.partition("=")
            result[key.strip()] = value
        else:
            result[entry.strip()] = ""
    return result


def compute_env_diff(
    old_env: Optional[List[str]],
    new_env: Optional[List[str]],
) -> EnvDiff:
    """Compute the diff between two env-var lists."""
    old = _parse_env_list(old_env)
    new = _parse_env_list(new_env)

    added = {k: v for k, v in new.items() if k not in old}
    removed = {k: v for k, v in old.items() if k not in new}
    changed = {
        k: (old[k], new[k])
        for k in old
        if k in new and old[k] != new[k]
    }
    return EnvDiff(added=added, removed=removed, changed=changed)
