"""Tests for deploy_sentinel.image_tracker."""
import time

import pytest

from deploy_sentinel.image_tracker import ImageRecord, ImageTracker


@pytest.fixture()
def tracker() -> ImageTracker:
    return ImageTracker(max_history=5)


class TestImageRecord:
    def test_to_dict_round_trip(self):
        ts = time.time()
        rec = ImageRecord("abc", "web", "nginx:1.25", timestamp=ts)
        d = rec.to_dict()
        restored = ImageRecord.from_dict(d)
        assert restored.container_id == "abc"
        assert restored.container_name == "web"
        assert restored.image == "nginx:1.25"
        assert restored.timestamp == ts

    def test_default_timestamp_is_recent(self):
        before = time.time()
        rec = ImageRecord("x", "y", "img:latest")
        after = time.time()
        assert before <= rec.timestamp <= after


class TestImageTrackerRecord:
    def test_record_stores_entry(self, tracker):
        tracker.record("c1", "web", "nginx:1.0")
        assert tracker.latest("c1").image == "nginx:1.0"

    def test_duplicate_image_not_stored_twice(self, tracker):
        tracker.record("c1", "web", "nginx:1.0")
        tracker.record("c1", "web", "nginx:1.0")
        assert len(tracker.history("c1")) == 1

    def test_different_images_both_stored(self, tracker):
        tracker.record("c1", "web", "nginx:1.0")
        tracker.record("c1", "web", "nginx:1.1")
        assert len(tracker.history("c1")) == 2

    def test_max_history_is_respected(self, tracker):
        for i in range(8):
            tracker.record("c1", "web", f"nginx:1.{i}")
        assert len(tracker.history("c1")) == 5

    def test_oldest_entries_are_dropped(self, tracker):
        for i in range(7):
            tracker.record("c1", "web", f"img:{i}")
        history = tracker.history("c1")
        assert history[0].image == "img:2"


class TestImageTrackerLatestAndPrevious:
    def test_latest_returns_none_for_unknown(self, tracker):
        assert tracker.latest("unknown") is None

    def test_previous_returns_none_for_single_entry(self, tracker):
        tracker.record("c1", "web", "img:1")
        assert tracker.previous("c1") is None

    def test_previous_returns_second_to_last(self, tracker):
        tracker.record("c1", "web", "img:1")
        tracker.record("c1", "web", "img:2")
        tracker.record("c1", "web", "img:3")
        assert tracker.previous("c1").image == "img:2"

    def test_clear_removes_history(self, tracker):
        tracker.record("c1", "web", "img:1")
        tracker.clear("c1")
        assert tracker.latest("c1") is None
        assert tracker.history("c1") == []
