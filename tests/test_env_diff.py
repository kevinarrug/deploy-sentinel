"""Tests for deploy_sentinel.env_diff."""
import pytest
from deploy_sentinel.env_diff import EnvDiff, compute_env_diff, _parse_env_list


# ---------------------------------------------------------------------------
# _parse_env_list
# ---------------------------------------------------------------------------

class TestParseEnvList:
    def test_empty_list_returns_empty_dict(self):
        assert _parse_env_list([]) == {}

    def test_none_returns_empty_dict(self):
        assert _parse_env_list(None) == {}

    def test_key_value_pair(self):
        assert _parse_env_list(["FOO=bar"]) == {"FOO": "bar"}

    def test_value_with_equals_sign(self):
        assert _parse_env_list(["URL=http://x.com/a=1"]) == {"URL": "http://x.com/a=1"}

    def test_key_without_value(self):
        assert _parse_env_list(["FLAG"]) == {"FLAG": ""}

    def test_multiple_entries(self):
        result = _parse_env_list(["A=1", "B=2"])
        assert result == {"A": "1", "B": "2"}


# ---------------------------------------------------------------------------
# compute_env_diff
# ---------------------------------------------------------------------------

class TestComputeEnvDiff:
    def test_no_changes(self):
        diff = compute_env_diff(["A=1"], ["A=1"])
        assert not diff.has_changes

    def test_added_key(self):
        diff = compute_env_diff(["A=1"], ["A=1", "B=2"])
        assert diff.added == {"B": "2"}
        assert not diff.removed
        assert not diff.changed
        assert diff.has_changes

    def test_removed_key(self):
        diff = compute_env_diff(["A=1", "B=2"], ["A=1"])
        assert diff.removed == {"B": "2"}
        assert not diff.added
        assert diff.has_changes

    def test_changed_value(self):
        diff = compute_env_diff(["A=old"], ["A=new"])
        assert diff.changed == {"A": ("old", "new")}
        assert diff.has_changes

    def test_none_inputs(self):
        diff = compute_env_diff(None, None)
        assert not diff.has_changes

    def test_summary_no_changes(self):
        diff = compute_env_diff(["X=1"], ["X=1"])
        assert diff.summary() == "no changes"

    def test_summary_with_changes(self):
        diff = compute_env_diff(["A=1"], ["A=2", "B=3"])
        summary = diff.summary()
        assert "added" in summary
        assert "changed" in summary

    def test_mixed_changes(self):
        old = ["KEEP=same", "REMOVE=gone", "CHANGE=old"]
        new = ["KEEP=same", "CHANGE=new", "NEW=here"]
        diff = compute_env_diff(old, new)
        assert "KEEP" not in diff.changed
        assert diff.removed == {"REMOVE": "gone"}
        assert diff.added == {"NEW": "here"}
        assert diff.changed == {"CHANGE": ("old", "new")}
