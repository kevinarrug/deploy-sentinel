"""Tests for deploy_sentinel.container_filter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from deploy_sentinel.container_filter import (
    ContainerFilter,
    FilterConfig,
    matches_filter,
)


def _make_container(name: str, labels: dict | None = None):
    """Create a minimal fake Docker container object."""
    c = MagicMock()
    c.attrs = {"Name": f"/{name}"}
    c.labels = labels or {}
    return c


# ---------------------------------------------------------------------------
# matches_filter
# ---------------------------------------------------------------------------

class TestMatchesFilter:
    def test_empty_config_matches_everything(self):
        c = _make_container("web")
        assert matches_filter(c, FilterConfig()) is True

    def test_excluded_name_returns_false(self):
        c = _make_container("infra-proxy")
        cfg = FilterConfig(excluded_names=["infra-proxy"])
        assert matches_filter(c, cfg) is False

    def test_required_label_present(self):
        c = _make_container("api", labels={"sentinel.monitor": "true"})
        cfg = FilterConfig(required_labels=["sentinel.monitor"])
        assert matches_filter(c, cfg) is True

    def test_required_label_missing(self):
        c = _make_container("api", labels={})
        cfg = FilterConfig(required_labels=["sentinel.monitor"])
        assert matches_filter(c, cfg) is False

    def test_name_pattern_match(self):
        c = _make_container("app-v2")
        cfg = FilterConfig(name_patterns=["app-*"])
        assert matches_filter(c, cfg) is True

    def test_name_pattern_no_match(self):
        c = _make_container("db-primary")
        cfg = FilterConfig(name_patterns=["app-*"])
        assert matches_filter(c, cfg) is False

    def test_multiple_patterns_any_match(self):
        c = _make_container("worker-1")
        cfg = FilterConfig(name_patterns=["app-*", "worker-*"])
        assert matches_filter(c, cfg) is True

    def test_excluded_takes_priority_over_pattern(self):
        c = _make_container("app-debug")
        cfg = FilterConfig(name_patterns=["app-*"], excluded_names=["app-debug"])
        assert matches_filter(c, cfg) is False


# ---------------------------------------------------------------------------
# ContainerFilter.apply
# ---------------------------------------------------------------------------

class TestContainerFilter:
    def test_apply_empty_list(self):
        cf = ContainerFilter()
        assert cf.apply([]) == []

    def test_apply_filters_out_excluded(self):
        containers = [
            _make_container("web"),
            _make_container("sidecar"),
        ]
        cf = ContainerFilter(FilterConfig(excluded_names=["sidecar"]))
        result = cf.apply(containers)
        assert len(result) == 1
        assert result[0] is containers[0]

    def test_apply_keeps_matching_labels(self):
        containers = [
            _make_container("api", labels={"monitor": "1"}),
            _make_container("db", labels={}),
        ]
        cf = ContainerFilter(FilterConfig(required_labels=["monitor"]))
        result = cf.apply(containers)
        assert len(result) == 1

    def test_default_config_keeps_all(self):
        containers = [_make_container(f"c{i}") for i in range(5)]
        cf = ContainerFilter()
        assert cf.apply(containers) == containers
