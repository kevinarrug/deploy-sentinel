"""Tests for deploy_sentinel.lifecycle_hook."""
import pytest
from unittest.mock import patch, MagicMock
import subprocess

from deploy_sentinel.lifecycle_hook import (
    HookPhase,
    HookResult,
    LifecycleHook,
    HookRunner,
)


@pytest.fixture()
def runner() -> HookRunner:
    return HookRunner()


def _make_hook(
    phase: HookPhase = HookPhase.POST_DEPLOY,
    command: str = "echo ok",
    ignore_failure: bool = False,
) -> LifecycleHook:
    return LifecycleHook(phase=phase, command=command, ignore_failure=ignore_failure)


class TestHookResult:
    def test_success_true_when_zero_returncode(self):
        r = HookResult(phase=HookPhase.POST_DEPLOY, command="x", returncode=0, stdout="", stderr="")
        assert r.success is True

    def test_success_false_when_nonzero_returncode(self):
        r = HookResult(phase=HookPhase.POST_DEPLOY, command="x", returncode=1, stdout="", stderr="")
        assert r.success is False


class TestHookRunnerAdd:
    def test_add_appends_hook(self, runner):
        hook = _make_hook()
        runner.add(hook)
        assert hook in runner.hooks

    def test_hooks_for_filters_by_phase(self, runner):
        runner.add(_make_hook(phase=HookPhase.PRE_DEPLOY))
        runner.add(_make_hook(phase=HookPhase.POST_DEPLOY))
        result = runner.hooks_for(HookPhase.PRE_DEPLOY)
        assert len(result) == 1
        assert result[0].phase == HookPhase.PRE_DEPLOY


class TestHookRunnerRunPhase:
    def _mock_proc(self, returncode=0, stdout="ok", stderr=""):
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_successful_hook_returns_result(self, runner):
        runner.add(_make_hook(phase=HookPhase.POST_DEPLOY, command="echo ok"))
        with patch("subprocess.run", return_value=self._mock_proc()) as mock_run:
            results = runner.run_phase(HookPhase.POST_DEPLOY)
        assert len(results) == 1
        assert results[0].success is True

    def test_no_hooks_for_phase_returns_empty(self, runner):
        runner.add(_make_hook(phase=HookPhase.PRE_DEPLOY))
        results = runner.run_phase(HookPhase.POST_DEPLOY)
        assert results == []

    def test_failing_hook_stops_execution(self, runner):
        runner.add(_make_hook(command="fail1"))
        runner.add(_make_hook(command="fail2"))
        with patch("subprocess.run", return_value=self._mock_proc(returncode=1)):
            results = runner.run_phase(HookPhase.POST_DEPLOY)
        assert len(results) == 1

    def test_ignore_failure_continues_execution(self, runner):
        runner.add(_make_hook(command="fail1", ignore_failure=True))
        runner.add(_make_hook(command="ok2"))
        side_effects = [
            self._mock_proc(returncode=1),
            self._mock_proc(returncode=0),
        ]
        with patch("subprocess.run", side_effect=side_effects):
            results = runner.run_phase(HookPhase.POST_DEPLOY)
        assert len(results) == 2

    def test_timeout_returns_failure_result(self, runner):
        runner.add(_make_hook(command="sleep 100", phase=HookPhase.PRE_ROLLBACK))
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 100", timeout=1)):
            results = runner.run_phase(HookPhase.PRE_ROLLBACK)
        assert len(results) == 1
        assert results[0].returncode == -1
        assert results[0].stderr == "timeout"
