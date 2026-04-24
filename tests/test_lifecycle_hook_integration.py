"""Integration-style tests: HookRunner built from hook_config helpers."""
import json
import subprocess
from unittest.mock import patch, MagicMock

from deploy_sentinel.lifecycle_hook import HookPhase, HookRunner
from deploy_sentinel.hook_config import hooks_from_list


def _proc(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode, m.stdout, m.stderr = returncode, stdout, stderr
    return m


class TestHookRunnerFromConfig:
    def test_runner_executes_hooks_loaded_from_config(self):
        raw = [
            {"phase": "post_deploy", "command": "echo deployed"},
            {"phase": "pre_rollback", "command": "echo rolling"},
        ]
        hooks = hooks_from_list(raw)
        runner = HookRunner(hooks=hooks)
        with patch("subprocess.run", return_value=_proc(returncode=0, stdout="deployed")) as mock_run:
            results = runner.run_phase(HookPhase.POST_DEPLOY)
        assert len(results) == 1
        assert results[0].success
        assert results[0].stdout == "deployed"

    def test_pre_rollback_hook_not_run_for_post_deploy_phase(self):
        raw = [{"phase": "pre_rollback", "command": "echo rb"}]
        hooks = hooks_from_list(raw)
        runner = HookRunner(hooks=hooks)
        with patch("subprocess.run") as mock_run:
            results = runner.run_phase(HookPhase.POST_DEPLOY)
        mock_run.assert_not_called()
        assert results == []

    def test_all_phases_can_be_registered_and_run(self):
        raw = [{"phase": p.value, "command": f"echo {p.value}"} for p in HookPhase]
        hooks = hooks_from_list(raw)
        runner = HookRunner(hooks=hooks)
        for phase in HookPhase:
            with patch("subprocess.run", return_value=_proc()) as mock_run:
                results = runner.run_phase(phase)
            assert len(results) == 1
            mock_run.assert_called_once()
