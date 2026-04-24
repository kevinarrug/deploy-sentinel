"""Tests for deploy_sentinel.event_log."""

import json
from pathlib import Path

import pytest

from deploy_sentinel.event_log import EventEntry, EventLog


@pytest.fixture
def tmp_log(tmp_path: Path) -> EventLog:
    return EventLog(log_path=str(tmp_path / "test_events.jsonl"))


def _make_entry(
    event_type: str = "health_failure",
    container_id: str = "abc123",
    container_name: str = "web",
    image: str = "nginx:latest",
    detail: str = "",
) -> EventEntry:
    return EventEntry.create(event_type, container_id, container_name, image, detail)


class TestEventEntry:
    def test_create_sets_timestamp(self):
        entry = _make_entry()
        assert entry.timestamp  # non-empty ISO string

    def test_create_stores_fields(self):
        entry = _make_entry(event_type="rollback", detail="reverted")
        assert entry.event_type == "rollback"
        assert entry.detail == "reverted"

    def test_roundtrip_dict(self):
        entry = _make_entry()
        restored = EventEntry.from_dict(entry.to_dict())
        assert restored == entry


class TestEventLogAppendAndRead:
    def test_read_all_empty_when_no_file(self, tmp_log: EventLog):
        assert tmp_log.read_all() == []

    def test_append_creates_file(self, tmp_log: EventLog):
        tmp_log.append(_make_entry())
        assert Path(tmp_log.log_path).exists()

    def test_append_and_read_single(self, tmp_log: EventLog):
        entry = _make_entry()
        tmp_log.append(entry)
        results = tmp_log.read_all()
        assert len(results) == 1
        assert results[0] == entry

    def test_append_multiple_preserves_order(self, tmp_log: EventLog):
        entries = [_make_entry(detail=str(i)) for i in range(3)]
        for e in entries:
            tmp_log.append(e)
        results = tmp_log.read_all()
        assert [r.detail for r in results] == ["0", "1", "2"]

    def test_log_is_valid_jsonl(self, tmp_log: EventLog):
        tmp_log.append(_make_entry())
        lines = Path(tmp_log.log_path).read_text().strip().splitlines()
        for line in lines:
            json.loads(line)  # must not raise


class TestEventLogFilters:
    def test_filter_by_container(self, tmp_log: EventLog):
        tmp_log.append(_make_entry(container_name="web"))
        tmp_log.append(_make_entry(container_name="db"))
        results = tmp_log.filter_by_container("web")
        assert len(results) == 1
        assert results[0].container_name == "web"

    def test_filter_by_type(self, tmp_log: EventLog):
        tmp_log.append(_make_entry(event_type="rollback"))
        tmp_log.append(_make_entry(event_type="health_failure"))
        results = tmp_log.filter_by_type("rollback")
        assert len(results) == 1
        assert results[0].event_type == "rollback"

    def test_filter_returns_empty_for_unknown(self, tmp_log: EventLog):
        tmp_log.append(_make_entry())
        assert tmp_log.filter_by_container("unknown") == []


class TestEventLogClear:
    def test_clear_removes_file(self, tmp_log: EventLog):
        tmp_log.append(_make_entry())
        tmp_log.clear()
        assert not Path(tmp_log.log_path).exists()

    def test_clear_on_missing_file_is_noop(self, tmp_log: EventLog):
        tmp_log.clear()  # should not raise
