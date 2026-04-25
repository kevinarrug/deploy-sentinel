"""Tests for deploy_sentinel.dependency_graph."""
import pytest

from deploy_sentinel.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
    DependencyNode,
)


def _node(name: str, depends_on=None, cid=None) -> DependencyNode:
    return DependencyNode(
        container_id=cid or f"id-{name}",
        name=name,
        depends_on=depends_on or [],
    )


@pytest.fixture()
def graph() -> DependencyGraph:
    return DependencyGraph()


class TestDependencyNode:
    def test_to_dict_round_trip(self):
        node = _node("web", depends_on=["db", "cache"])
        assert DependencyNode.from_dict(node.to_dict()) == node

    def test_default_depends_on_is_empty(self):
        node = DependencyNode(container_id="abc", name="app")
        assert node.depends_on == []


class TestDependencyGraphRegister:
    def test_register_and_get(self, graph):
        node = _node("db")
        graph.register(node)
        assert graph.get("db") is node

    def test_remove_node(self, graph):
        graph.register(_node("db"))
        graph.remove("db")
        assert graph.get("db") is None

    def test_all_names_returns_registered(self, graph):
        graph.register(_node("a"))
        graph.register(_node("b"))
        assert set(graph.all_names()) == {"a", "b"}


class TestDependentsOf:
    def test_no_dependents(self, graph):
        graph.register(_node("db"))
        assert graph.dependents_of("db") == []

    def test_single_dependent(self, graph):
        graph.register(_node("db"))
        graph.register(_node("web", depends_on=["db"]))
        assert graph.dependents_of("db") == ["web"]

    def test_multiple_dependents(self, graph):
        graph.register(_node("db"))
        graph.register(_node("web", depends_on=["db"]))
        graph.register(_node("worker", depends_on=["db"]))
        assert set(graph.dependents_of("db")) == {"web", "worker"}


class TestRollbackOrder:
    def test_single_node_order(self, graph):
        graph.register(_node("app"))
        assert graph.rollback_order() == ["app"]

    def test_dependent_comes_before_dependency(self, graph):
        graph.register(_node("db"))
        graph.register(_node("web", depends_on=["db"]))
        order = graph.rollback_order()
        assert order.index("web") < order.index("db")

    def test_chain_order(self, graph):
        graph.register(_node("db"))
        graph.register(_node("api", depends_on=["db"]))
        graph.register(_node("web", depends_on=["api"]))
        order = graph.rollback_order()
        assert order.index("web") < order.index("api")
        assert order.index("api") < order.index("db")

    def test_cycle_raises(self, graph):
        graph.register(_node("a", depends_on=["b"]))
        graph.register(_node("b", depends_on=["a"]))
        with pytest.raises(CyclicDependencyError):
            graph.rollback_order()

    def test_independent_nodes_all_present(self, graph):
        graph.register(_node("x"))
        graph.register(_node("y"))
        assert set(graph.rollback_order()) == {"x", "y"}
