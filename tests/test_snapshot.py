"""Tests for deploy_sentinel.snapshot."""

from __future__ import annotations

import json
import os

import pytest

from deploy_sentinel.snapshot import ContainerSnapshot, SnapshotStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(
    container_id: str = "abc123",
    image: str = "myapp:1.0",
    image_id: str = "sha256:aaa",
) -> ContainerSnapshot:
    return ContainerSnapshot(
        container_id=container_id,
        container_name="myapp",
        image=image,
        image_id=image_id,
    )


@pytest.fixture()
def store(tmp_path):
    return SnapshotStore(path=str(tmp_path / "snapshots.json"))


# ---------------------------------------------------------------------------
# ContainerSnapshot.has_changed
# ---------------------------------------------------------------------------

class TestContainerSnapshotHasChanged:
    def test_identical_snapshots_not_changed(self):
        s = _make_snapshot()
        assert s.has_changed(s) is False

    def test_different_image_tag_is_changed(self):
        old = _make_snapshot(image="myapp:1.0")
        new = _make_snapshot(image="myapp:2.0")
        assert old.has_changed(new) is True

    def test_different_image_id_is_changed(self):
        old = _make_snapshot(image_id="sha256:aaa")
        new = _make_snapshot(image_id="sha256:bbb")
        assert old.has_changed(new) is True

    def test_same_tag_same_id_not_changed(self):
        a = _make_snapshot(image="myapp:latest", image_id="sha256:ccc")
        b = _make_snapshot(image="myapp:latest", image_id="sha256:ccc")
        assert a.has_changed(b) is False


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

class TestSnapshotStore:
    def test_get_missing_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_save_and_get_roundtrip(self, store):
        snap = _make_snapshot()
        store.save(snap)
        result = store.get(snap.container_id)
        assert result == snap

    def test_save_persists_to_disk(self, store):
        snap = _make_snapshot()
        store.save(snap)
        assert os.path.exists(store.path)
        with open(store.path) as fh:
            data = json.load(fh)
        assert snap.container_id in data

    def test_reload_restores_state(self, tmp_path):
        path = str(tmp_path / "snapshots.json")
        snap = _make_snapshot()
        store1 = SnapshotStore(path=path)
        store1.save(snap)

        store2 = SnapshotStore(path=path)
        assert store2.get(snap.container_id) == snap

    def test_remove_deletes_entry(self, store):
        snap = _make_snapshot()
        store.save(snap)
        store.remove(snap.container_id)
        assert store.get(snap.container_id) is None

    def test_remove_nonexistent_does_not_raise(self, store):
        store.remove("ghost")  # should not raise

    def test_corrupt_file_handled_gracefully(self, tmp_path):
        path = tmp_path / "snapshots.json"
        path.write_text("not valid json")
        store = SnapshotStore(path=str(path))  # should not raise
        assert store.get("any") is None
