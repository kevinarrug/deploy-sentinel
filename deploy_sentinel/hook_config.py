"""Parse lifecycle hooks from environment variables or dict config."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from deploy_sentinel.lifecycle_hook import HookPhase, LifecycleHook

_ENV_KEY = "SENTINEL_LIFECYCLE_HOOKS"


def _parse_hook(raw: Dict[str, Any]) -> LifecycleHook:
    """Parse a single hook definition from a dict."""
    phase_str = raw.get("phase", "")
    try:
        phase = HookPhase(phase_str)
    except ValueError:
        valid = [p.value for p in HookPhase]
        raise ValueError(f"Unknown hook phase '{phase_str}'. Valid: {valid}")

    command = raw.get("command", "")
    if not command:
        raise ValueError("Hook 'command' must be a non-empty string.")

    return LifecycleHook(
        phase=phase,
        command=command,
        timeout=int(raw.get("timeout", 30)),
        ignore_failure=bool(raw.get("ignore_failure", False)),
    )


def hooks_from_list(raw_list: List[Dict[str, Any]]) -> List[LifecycleHook]:
    """Parse a list of hook definitions."""
    return [_parse_hook(item) for item in raw_list]


def hooks_from_env(env_key: str = _ENV_KEY) -> List[LifecycleHook]:
    """Load hooks from a JSON-encoded environment variable.

    The variable should contain a JSON array of hook objects, e.g.::

        '[{"phase": "post_deploy", "command": "notify.sh"}]'
    """
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {env_key}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{env_key} must be a JSON array.")
    return hooks_from_list(data)
