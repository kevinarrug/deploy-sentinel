"""Tests for deploy_sentinel.dependency_loader."""
from types import SimpleNamespace

import pytest

from deploy_sentinel.dependency_loader import (
    _parse_depends_on,
    build_graph_from_containers,
)


def _make_container(name: str, labels=None, cid=None):
    return SimpleNamespace(
        id=cid or f"id-{name}",
        name=name,
        labels=labels or {},
    )


class TestParseDependsOn:
    def test_empty_string_returns_empty(self):
        assert _parse_depends_on("") == []

    def test_single_dependency(self):
        assert _parse_depends_on("db") == ["db"]

    def test_multiple_dependencies(self):
        assert _parse_depends_on("db,cache") == ["db", "cache"]

    def test_strips_whitespace(self):
        assert _parse_depends_on(" db , cache ") == ["db", "cache"]

    def test_ignores_empty_segments(self):
        assert _parse_depends_on("db,,cache") == ["db", "cache"]


class TestBuildGraphFromContainers:
    def test_empty_list_returns_empty_graph(self):
        graph = build_graph_from_containers([])
        assert graph.all_names() == []

    def test_registers_all_containers(self):
        containers = [_make_container("web"), _make_container("db")]
        graph = build_graph_from_containers(containers)
        assert set(graph.all_names()) == {"web", "db"}

    def test_no_label_means_no_dependencies(self):
        containers = [_make_container("web")]
        graph = build_graph_from_containers(containers)
        node = graph.get("web")
        assert node is not None
        assert node.depends_on == []

    def test_label_parsed_into_depends_on(self):
        containers = [
            _make_container("web", labels={"deploy-sentinel.depends-on": "db,cache"}),
            _make_container("db"),
            _make_container("cache"),
        ]
        graph = build_graph_from_containers(containers)
        node = graph.get("web")
        assert node is not None
        assert set(node.depends_on) == {"db", "cache"}

    def test_container_id_stored(self):
        containers = [_make_container("app", cid="abc123")]
        graph = build_graph_from_containers(containers)
        node = graph.get("app")
        assert node.container_id == "abc123"

    def test_rollback_order_respects_label_dependency(self):
        containers = [
            _make_container("web", labels={"deploy-sentinel.depends-on": "db"}),
            _make_container("db"),
        ]
        graph = build_graph_from_containers(containers)
        order = graph.rollback_order()
        assert order.index("web") < order.index("db")
