"""Tests for deploy_sentinel.deployment_diff."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pytest

from deploy_sentinel.deployment_diff import DeploymentDiff, compute_diff
from deploy_sentinel.snapshot import ContainerSnapshot


def _make_snapshot(
    container_id: str = "abc123",
    name: str = "web",
    image_tag: str = "nginx:1.25",
    labels: Optional[Dict[str, str]] = None,
    env: Optional[List[str]] = None,
) -> ContainerSnapshot:
    return ContainerSnapshot(
        container_id=container_id,
        name=name,
        image_tag=image_tag,
        labels=labels or {},
        env=env or [],
    )


# ---------------------------------------------------------------------------
# DeploymentDiff.has_changes
# ---------------------------------------------------------------------------

class TestDeploymentDiffHasChanges:
    def test_no_changes_by_default(self):
        diff = DeploymentDiff(container_id="x", container_name="web")
        assert diff.has_changes is False

    def test_image_changed_sets_has_changes(self):
        diff = DeploymentDiff(container_id="x", container_name="web", image_changed=True)
        assert diff.has_changes is True

    def test_labels_added_sets_has_changes(self):
        diff = DeploymentDiff(container_id="x", container_name="web", labels_added={"k": "v"})
        assert diff.has_changes is True

    def test_env_removed_sets_has_changes(self):
        diff = DeploymentDiff(container_id="x", container_name="web", env_removed=["FOO=bar"])
        assert diff.has_changes is True


# ---------------------------------------------------------------------------
# DeploymentDiff.summary
# ---------------------------------------------------------------------------

class TestDeploymentDiffSummary:
    def test_no_changes_summary(self):
        diff = DeploymentDiff(container_id="x", container_name="web")
        assert diff.summary() == "web: no changes"

    def test_image_change_in_summary(self):
        diff = DeploymentDiff(
            container_id="x",
            container_name="web",
            image_changed=True,
            previous_image="nginx:1.24",
            current_image="nginx:1.25",
        )
        assert "nginx:1.24" in diff.summary()
        assert "nginx:1.25" in diff.summary()


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------

class TestComputeDiff:
    def test_identical_snapshots_no_changes(self):
        snap = _make_snapshot()
        diff = compute_diff(snap, snap)
        assert diff.has_changes is False

    def test_detects_image_change(self):
        prev = _make_snapshot(image_tag="nginx:1.24")
        curr = _make_snapshot(image_tag="nginx:1.25")
        diff = compute_diff(prev, curr)
        assert diff.image_changed is True
        assert diff.previous_image == "nginx:1.24"
        assert diff.current_image == "nginx:1.25"

    def test_detects_label_added(self):
        prev = _make_snapshot(labels={})
        curr = _make_snapshot(labels={"version": "2"})
        diff = compute_diff(prev, curr)
        assert "version" in diff.labels_added

    def test_detects_label_removed(self):
        prev = _make_snapshot(labels={"version": "1"})
        curr = _make_snapshot(labels={})
        diff = compute_diff(prev, curr)
        assert "version" in diff.labels_removed

    def test_detects_label_changed(self):
        prev = _make_snapshot(labels={"env": "staging"})
        curr = _make_snapshot(labels={"env": "production"})
        diff = compute_diff(prev, curr)
        assert "env" in diff.labels_changed
        assert diff.labels_changed["env"] == ("staging", "production")

    def test_detects_env_added(self):
        prev = _make_snapshot(env=["FOO=1"])
        curr = _make_snapshot(env=["FOO=1", "BAR=2"])
        diff = compute_diff(prev, curr)
        assert "BAR=2" in diff.env_added

    def test_detects_env_removed(self):
        prev = _make_snapshot(env=["FOO=1", "BAR=2"])
        curr = _make_snapshot(env=["FOO=1"])
        diff = compute_diff(prev, curr)
        assert "BAR=2" in diff.env_removed

    def test_container_metadata_copied(self):
        prev = _make_snapshot(container_id="abc", name="api")
        curr = _make_snapshot(container_id="abc", name="api")
        diff = compute_diff(prev, curr)
        assert diff.container_id == "abc"
        assert diff.container_name == "api"
