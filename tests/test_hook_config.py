"""Tests for deploy_sentinel.hook_config."""
import json
import pytest

from deploy_sentinel.lifecycle_hook import HookPhase
from deploy_sentinel.hook_config import hooks_from_list, hooks_from_env


class TestHooksFromList:
    def test_parses_minimal_hook(self):
        hooks = hooks_from_list([{"phase": "post_deploy", "command": "echo hi"}])
        assert len(hooks) == 1
        assert hooks[0].phase == HookPhase.POST_DEPLOY
        assert hooks[0].command == "echo hi"

    def test_default_timeout_is_30(self):
        hooks = hooks_from_list([{"phase": "pre_deploy", "command": "ls"}])
        assert hooks[0].timeout == 30

    def test_custom_timeout_parsed(self):
        hooks = hooks_from_list([{"phase": "pre_deploy", "command": "ls", "timeout": 60}])
        assert hooks[0].timeout == 60

    def test_ignore_failure_default_false(self):
        hooks = hooks_from_list([{"phase": "post_rollback", "command": "x"}])
        assert hooks[0].ignore_failure is False

    def test_ignore_failure_parsed(self):
        hooks = hooks_from_list([{"phase": "post_rollback", "command": "x", "ignore_failure": True}])
        assert hooks[0].ignore_failure is True

    def test_unknown_phase_raises(self):
        with pytest.raises(ValueError, match="Unknown hook phase"):
            hooks_from_list([{"phase": "bad_phase", "command": "x"}])

    def test_missing_command_raises(self):
        with pytest.raises(ValueError, match="command"):
            hooks_from_list([{"phase": "post_deploy", "command": ""}])

    def test_multiple_hooks_parsed(self):
        raw = [
            {"phase": "pre_deploy", "command": "a"},
            {"phase": "post_deploy", "command": "b"},
        ]
        hooks = hooks_from_list(raw)
        assert len(hooks) == 2


class TestHooksFromEnv:
    def test_empty_env_returns_empty(self, monkeypatch):
        monkeypatch.delenv("SENTINEL_LIFECYCLE_HOOKS", raising=False)
        assert hooks_from_env() == []

    def test_valid_json_array_parsed(self, monkeypatch):
        data = json.dumps([{"phase": "post_deploy", "command": "notify.sh"}])
        monkeypatch.setenv("SENTINEL_LIFECYCLE_HOOKS", data)
        hooks = hooks_from_env()
        assert len(hooks) == 1
        assert hooks[0].command == "notify.sh"

    def test_invalid_json_raises(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_LIFECYCLE_HOOKS", "not-json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            hooks_from_env()

    def test_json_object_instead_of_array_raises(self, monkeypatch):
        monkeypatch.setenv("SENTINEL_LIFECYCLE_HOOKS", json.dumps({"phase": "post_deploy"}))
        with pytest.raises(ValueError, match="JSON array"):
            hooks_from_env()

    def test_custom_env_key(self, monkeypatch):
        data = json.dumps([{"phase": "pre_rollback", "command": "cleanup.sh"}])
        monkeypatch.setenv("MY_HOOKS", data)
        hooks = hooks_from_env(env_key="MY_HOOKS")
        assert hooks[0].phase == HookPhase.PRE_ROLLBACK
