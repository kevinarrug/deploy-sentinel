"""Tests for deploy_sentinel.alert_policy."""
import pytest
from deploy_sentinel.alert_policy import AlertPolicy, PolicyStore

CID = "abc123"


@pytest.fixture()
def store() -> PolicyStore:
    return PolicyStore(policy=AlertPolicy(failure_threshold=3, cooldown_seconds=60))


class TestAlertPolicy:
    def test_default_is_valid(self):
        assert AlertPolicy().is_valid()

    def test_zero_threshold_invalid(self):
        assert not AlertPolicy(failure_threshold=0).is_valid()

    def test_negative_cooldown_invalid(self):
        assert not AlertPolicy(failure_threshold=1, cooldown_seconds=-1).is_valid()


class TestPolicyStore:
    def test_initial_failure_count_zero(self, store):
        assert store.failure_count(CID) == 0

    def test_record_failure_increments(self, store):
        store.record_failure(CID)
        store.record_failure(CID)
        assert store.failure_count(CID) == 2

    def test_reset_clears_count(self, store):
        store.record_failure(CID)
        store.reset(CID)
        assert store.failure_count(CID) == 0

    def test_no_alert_below_threshold(self, store):
        store.record_failure(CID)
        store.record_failure(CID)  # count == 2, threshold == 3
        assert not store.should_alert(CID, now=1000.0)

    def test_alert_at_threshold(self, store):
        for _ in range(3):
            store.record_failure(CID)
        assert store.should_alert(CID, now=1000.0)

    def test_no_alert_during_cooldown(self, store):
        for _ in range(3):
            store.record_failure(CID)
        store.mark_alerted(CID, now=1000.0)
        # only 30 s later — still within 60 s cooldown
        assert not store.should_alert(CID, now=1030.0)

    def test_alert_after_cooldown_expires(self, store):
        for _ in range(3):
            store.record_failure(CID)
        store.mark_alerted(CID, now=1000.0)
        assert store.should_alert(CID, now=1061.0)

    def test_reset_also_clears_last_alerted(self, store):
        for _ in range(3):
            store.record_failure(CID)
        store.mark_alerted(CID, now=1000.0)
        store.reset(CID)
        # After reset a single failure should NOT trigger an alert
        store.record_failure(CID)
        assert not store.should_alert(CID, now=1001.0)
