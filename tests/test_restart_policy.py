"""Tests for deploy_sentinel.restart_policy."""
from datetime import datetime, timedelta

import pytest

from deploy_sentinel.restart_policy import (
    RestartPolicy,
    RestartPolicyStore,
    RestartRecord,
)


@pytest.fixture()
def store() -> RestartPolicyStore:
    return RestartPolicyStore(policy=RestartPolicy(max_restarts=3, window_seconds=300))


class TestRestartPolicy:
    def test_default_is_valid(self):
        assert RestartPolicy().is_valid()

    def test_zero_max_restarts_invalid(self):
        assert not RestartPolicy(max_restarts=0).is_valid()

    def test_zero_window_invalid(self):
        assert not RestartPolicy(window_seconds=0).is_valid()

    def test_negative_max_restarts_invalid(self):
        assert not RestartPolicy(max_restarts=-1).is_valid()


class TestRestartRecord:
    def test_initial_count_is_zero(self):
        r = RestartRecord(container_id="abc")
        assert r.restart_count == 0

    def test_record_increments_count(self):
        r = RestartRecord(container_id="abc")
        r.record()
        assert r.restart_count == 1

    def test_record_sets_first_restart(self):
        r = RestartRecord(container_id="abc")
        now = datetime(2024, 1, 1, 12, 0, 0)
        r.record(now=now)
        assert r.first_restart == now

    def test_second_record_does_not_overwrite_first(self):
        r = RestartRecord(container_id="abc")
        t1 = datetime(2024, 1, 1, 12, 0, 0)
        t2 = datetime(2024, 1, 1, 12, 1, 0)
        r.record(now=t1)
        r.record(now=t2)
        assert r.first_restart == t1

    def test_reset_clears_count(self):
        r = RestartRecord(container_id="abc")
        r.record()
        r.reset()
        assert r.restart_count == 0
        assert r.first_restart is None


class TestRestartPolicyStore:
    def test_should_restart_true_initially(self, store):
        assert store.should_restart("c1") is True

    def test_should_restart_false_after_max(self, store):
        now = datetime(2024, 6, 1, 10, 0, 0)
        for _ in range(3):
            store.record_restart("c1", now=now)
        assert store.should_restart("c1", now=now) is False

    def test_window_expiry_resets_count(self, store):
        early = datetime(2024, 6, 1, 10, 0, 0)
        for _ in range(3):
            store.record_restart("c1", now=early)
        # Advance time beyond the window
        later = early + timedelta(seconds=301)
        assert store.should_restart("c1", now=later) is True

    def test_restart_count_tracked(self, store):
        store.record_restart("c2")
        store.record_restart("c2")
        assert store.restart_count("c2") == 2

    def test_reset_clears_record(self, store):
        store.record_restart("c3")
        store.reset("c3")
        assert store.restart_count("c3") == 0

    def test_unknown_container_restart_count_is_zero(self, store):
        assert store.restart_count("unknown") == 0

    def test_invalid_policy_prevents_restart(self):
        bad_store = RestartPolicyStore(policy=RestartPolicy(max_restarts=0))
        assert bad_store.should_restart("c1") is False
