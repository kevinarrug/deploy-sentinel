"""Lifecycle hook support for pre/post deploy actions."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class HookPhase(str, Enum):
    PRE_DEPLOY = "pre_deploy"
    POST_DEPLOY = "post_deploy"
    PRE_ROLLBACK = "pre_rollback"
    POST_ROLLBACK = "post_rollback"


@dataclass
class HookResult:
    phase: HookPhase
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


@dataclass
class LifecycleHook:
    phase: HookPhase
    command: str
    timeout: int = 30
    ignore_failure: bool = False


@dataclass
class HookRunner:
    hooks: List[LifecycleHook] = field(default_factory=list)

    def run_phase(self, phase: HookPhase) -> List[HookResult]:
        results: List[HookResult] = []
        for hook in self.hooks:
            if hook.phase != phase:
                continue
            result = self._execute(hook)
            results.append(result)
            if not result.success and not hook.ignore_failure:
                logger.error(
                    "Hook failed (phase=%s, cmd=%s, rc=%d)",
                    phase.value,
                    hook.command,
                    result.returncode,
                )
                break
            elif not result.success:
                logger.warning(
                    "Hook failed but ignored (phase=%s, cmd=%s)",
                    phase.value,
                    hook.command,
                )
        return results

    def _execute(self, hook: LifecycleHook) -> HookResult:
        logger.debug("Running hook: phase=%s cmd=%s", hook.phase.value, hook.command)
        try:
            proc = subprocess.run(
                hook.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=hook.timeout,
            )
            return HookResult(
                phase=hook.phase,
                command=hook.command,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            logger.error("Hook timed out: %s", hook.command)
            return HookResult(
                phase=hook.phase,
                command=hook.command,
                returncode=-1,
                stdout="",
                stderr="timeout",
            )

    def add(self, hook: LifecycleHook) -> None:
        self.hooks.append(hook)

    def hooks_for(self, phase: HookPhase) -> List[LifecycleHook]:
        return [h for h in self.hooks if h.phase == phase]
