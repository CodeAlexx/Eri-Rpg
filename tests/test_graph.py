"""
Tests for graph data structures and operations.

Tests cover:
- Dataclasses (to_dict/from_dict)
- Graph operations (add_module, add_edge, get_module, save/load)
- Queries (find_modules, find_interface, get_dependencies, get_dependents, impact_analysis)
- Analysis (stats, find_circular_dependencies, orphan_modules)
- Storage (save_graph, load_graph, delete_graph, search_interfaces)
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg import storage


# Fixtures


@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    graph = Graph(project="test-project")

    # Create modules with interfaces
    mod_a = Module(
        path="src/module_a.py",
        lang="python",
        lines=100,
        summary="Module A with core functionality",
        interfaces=[
            Interface(
                name="ClassA",
                type="class",
                signature="class ClassA",
                docstring="Main class for A",
                methods=["method1", "method2"],
                line=10,
            ),
            Interface(
                name="function_a",
                type="function",
                signature="def function_a(x: int) -> str",
                docstring="Helper function",
                line=50,
            ),
        ],
        deps_internal=["src/module_b.py"],
        deps_external=["requests", "pytest"],
    )

    mod_b = Module(
        path="src/module_b.py",
        lang="python",
        lines=80,
        summary="Module B with utilities",
        interfaces=[
            Interface(
                name="ClassB",
                type="class",
                signature="class ClassB",
                docstring="Utility class",
                methods=["helper1"],
                line=5,
            ),
        ],
        deps_internal=["src/module_c.py"],
        deps_external=["requests"],
    )

    mod_c = Module(
        path="src/module_c.py",
        lang="python",
        lines=50,
        summary="Module C with base classes",
        interfaces=[
            Interface(
                name="BaseClass",
                type="class",
                signature="class BaseClass",
                docstring="Base class for inheritance",
                line=1,
            ),
        ],
        deps_internal=[],
        deps_external=["abc"],
    )

    mod_d = Module(
        path="src/module_d.py",
        lang="python",
        lines=30,
        summary="Orphan module with no dependents",
        interfaces=[],
        deps_internal=[],
        deps_external=[],
    )

    # Add modules
    graph.add_module(mod_a)
    graph.add_module(mod_b)
    graph.add_module(mod_c)
    graph.add_module(mod_d)

    # Add edges
    graph.add_edge(Edge(source="src/module_a.py", target="src/module_b.py", edge_type="imports", specifics=["ClassB"]))
    graph.add_edge(Edge(source="src/module_b.py", target="src/module_c.py", edge_type="imports", specifics=["BaseClass"]))

    return graph


@pytest.fixture
def circular_graph():
    """Create a graph with circular dependencies."""
    graph = Graph(project="circular-test")

    mod_x = Module(
        path="x.py",
        lang="python",
        lines=10,
        deps_internal=["y.py"],
    )
    mod_y = Module(
        path="y.py",
        lang="python",
        lines=10,
        deps_internal=["z.py"],
    )
    mod_z = Module(
        path="z.py",
        lang="python",
        lines=10,
        deps_internal=["x.py"],  # Circular back to x
    )

    graph.add_module(mod_x)
    graph.add_module(mod_y)
    graph.add_module(mod_z)

    graph.add_edge(Edge(source="x.py", target="y.py", edge_type="imports"))
    graph.add_edge(Edge(source="y.py", target="z.py", edge_type="imports"))
    graph.add_edge(Edge(source="z.py", target="x.py", edge_type="imports"))

    return graph


# Test Dataclasses


def test_interface_to_dict_from_dict():
    """Test Interface serialization."""
    iface = Interface(
        name="TestClass",
        type="class",
        signature="class TestClass(Base)",
        docstring="Test class",
        methods=["foo", "bar"],
        line=42,
    )

    d = iface.to_dict()
    assert d["name"] == "TestClass"
    assert d["type"] == "class"
    assert d["methods"] == ["foo", "bar"]
    assert d["line"] == 42

    iface2 = Interface.from_dict(d)
    assert iface2.name == iface.name
    assert iface2.type == iface.type
    assert iface2.methods == iface.methods
    assert iface2.line == iface.line


def test_module_to_dict_from_dict():
    """Test Module serialization."""
    mod = Module(
        path="test/module.py",
        lang="python",
        lines=100,
        summary="Test module",
        interfaces=[
            Interface(name="Func", type="function", line=10),
        ],
        deps_internal=["other.py"],
        deps_external=["requests"],
    )

    d = mod.to_dict()
    assert d["path"] == "test/module.py"
    assert d["lang"] == "python"
    assert d["lines"] == 100
    assert len(d["interfaces"]) == 1

    mod2 = Module.from_dict(d)
    assert mod2.path == mod.path
    assert mod2.lang == mod.lang
    assert len(mod2.interfaces) == 1
    assert mod2.deps_internal == ["other.py"]


def test_edge_to_dict_from_dict():
    """Test Edge serialization."""
    edge = Edge(
        source="a.py",
        target="b.py",
        edge_type="imports",
        specifics=["ClassB", "func_b"],
    )

    d = edge.to_dict()
    assert d["source"] == "a.py"
    assert d["target"] == "b.py"
    assert d["specifics"] == ["ClassB", "func_b"]

    edge2 = Edge.from_dict(d)
    assert edge2.source == edge.source
    assert edge2.target == edge.target
    assert edge2.specifics == edge.specifics


# Test Graph Operations


def test_graph_add_module(sample_graph):
    """Test adding modules to graph."""
    assert len(sample_graph.modules) == 4
    assert "src/module_a.py" in sample_graph.modules


def test_graph_add_edge(sample_graph):
    """Test adding edges to graph."""
    assert len(sample_graph.edges) == 2
    # Check dependents index is built
    assert "src/module_b.py" in sample_graph._dependents_index
    assert "src/module_a.py" in sample_graph._dependents_index["src/module_b.py"]


def test_graph_get_module(sample_graph):
    """Test retrieving modules from graph."""
    mod = sample_graph.get_module("src/module_a.py")
    assert mod is not None
    assert mod.path == "src/module_a.py"
    assert len(mod.interfaces) == 2

    missing = sample_graph.get_module("nonexistent.py")
    assert missing is None


def test_graph_save_load():
    """Test saving and loading graph to/from JSON."""
    graph = Graph(project="save-test")
    mod = Module(
        path="test.py",
        lang="python",
        lines=50,
        interfaces=[Interface(name="Test", type="class", line=1)],
    )
    graph.add_module(mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "graph.json")
        graph.save(path)

        assert os.path.exists(path)

        loaded = Graph.load(path)
        assert loaded.project == "save-test"
        assert len(loaded.modules) == 1
        assert "test.py" in loaded.modules
        assert loaded.modules["test.py"].lang == "python"


# Test Queries


def test_find_modules(sample_graph):
    """Test finding modules by pattern."""
    # Exact match
    results = sample_graph.find_modules("src/module_a.py")
    assert len(results) == 1
    assert results[0].path == "src/module_a.py"

    # Wildcard pattern
    results = sample_graph.find_modules("*module_*.py")
    assert len(results) == 4

    # Partial match
    results = sample_graph.find_modules("module_b")
    assert len(results) == 1
    assert results[0].path == "src/module_b.py"

    # No match
    results = sample_graph.find_modules("nonexistent")
    assert len(results) == 0


def test_find_interface(sample_graph):
    """Test finding interfaces by name."""
    # Exact match
    results = sample_graph.find_interface("ClassA")
    assert len(results) == 1
    assert results[0][0] == "src/module_a.py"
    assert results[0][1].name == "ClassA"

    # Partial match
    results = sample_graph.find_interface("class")
    assert len(results) == 3  # ClassA, ClassB, BaseClass

    # Case insensitive
    results = sample_graph.find_interface("CLASSA")
    assert len(results) == 1

    # No match
    results = sample_graph.find_interface("NonExistent")
    assert len(results) == 0


def test_get_dependencies(sample_graph):
    """Test getting module dependencies."""
    # Internal only
    deps = sample_graph.get_dependencies("src/module_a.py")
    assert "internal" in deps
    assert "src/module_b.py" in deps["internal"]
    assert "external" not in deps

    # Include external
    deps = sample_graph.get_dependencies("src/module_a.py", include_external=True)
    assert "internal" in deps
    assert "external" in deps
    assert "requests" in deps["external"]
    assert "pytest" in deps["external"]

    # Module with no deps
    deps = sample_graph.get_dependencies("src/module_c.py")
    assert deps["internal"] == []


def test_get_dependents(sample_graph):
    """Test getting module dependents."""
    # module_b is depended on by module_a
    deps = sample_graph.get_dependents("src/module_b.py")
    assert "src/module_a.py" in deps

    # module_c is depended on by module_b
    deps = sample_graph.get_dependents("src/module_c.py")
    assert "src/module_b.py" in deps

    # module_d has no dependents
    deps = sample_graph.get_dependents("src/module_d.py")
    assert len(deps) == 0


def test_get_transitive_dependents(sample_graph):
    """Test getting transitive dependents."""
    # module_c -> module_b -> module_a
    deps = sample_graph.get_transitive_dependents("src/module_c.py")
    assert "src/module_b.py" in deps
    assert "src/module_a.py" in deps

    # module_b -> module_a
    deps = sample_graph.get_transitive_dependents("src/module_b.py")
    assert "src/module_a.py" in deps


def test_impact_analysis(sample_graph):
    """Test impact analysis."""
    # Analyze module_c (affects module_b and module_a)
    analysis = sample_graph.impact_analysis("src/module_c.py")

    assert analysis["module"] == "src/module_c.py"
    assert analysis["summary"] == "Module C with base classes"
    assert "BaseClass" in analysis["interfaces"]
    assert "src/module_b.py" in analysis["direct_dependents"]
    assert "src/module_a.py" in analysis["transitive_dependents"]
    assert analysis["total_affected"] == 2
    assert analysis["risk"] == "LOW"  # Only 2 affected modules

    # Analyze orphan module
    analysis = sample_graph.impact_analysis("src/module_d.py")
    assert analysis["total_affected"] == 0
    assert analysis["risk"] == "LOW"


def test_impact_analysis_with_depth(sample_graph):
    """Test impact analysis with depth limit."""
    # Depth 1 should only get direct dependents
    analysis = sample_graph.impact_analysis("src/module_c.py", depth=1)
    assert "src/module_b.py" in analysis["direct_dependents"]
    assert "src/module_a.py" not in analysis["transitive_dependents"]


# Test Analysis Functions


def test_stats(sample_graph):
    """Test graph statistics."""
    stats = sample_graph.stats()

    assert stats["modules"] == 4
    assert stats["edges"] == 2
    assert stats["total_lines"] == 260  # 100 + 80 + 50 + 30
    assert stats["total_interfaces"] == 4  # ClassA, function_a, ClassB, BaseClass


def test_find_circular_dependencies(circular_graph):
    """Test finding circular dependency chains."""
    cycles = circular_graph.find_circular_dependencies()

    assert len(cycles) > 0
    # Should find the x -> y -> z -> x cycle
    cycle = cycles[0]
    assert len(cycle) == 4  # x, y, z, x (includes duplicate at end)
    assert cycle[0] == cycle[-1]  # Cycle property


def test_no_circular_dependencies(sample_graph):
    """Test graph with no circular dependencies."""
    cycles = sample_graph.find_circular_dependencies()
    assert len(cycles) == 0


def test_orphan_modules(sample_graph):
    """Test finding orphan modules."""
    orphans = sample_graph.orphan_modules()

    # module_a and module_d have no dependents
    assert "src/module_a.py" in orphans
    assert "src/module_d.py" in orphans
    assert len(orphans) == 2


# Test Storage Operations


def test_storage_save_load():
    """Test saving and loading graph via storage."""
    graph = Graph(project="storage-test")
    mod = Module(
        path="test.py",
        lang="python",
        lines=42,
        interfaces=[
            Interface(name="Foo", type="function", line=1),
        ],
    )
    graph.add_module(mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Save
        storage.save_graph(graph, db_path=db_path)

        # Load
        loaded = storage.load_graph("storage-test", db_path=db_path)
        assert loaded is not None
        assert loaded.project == "storage-test"
        assert len(loaded.modules) == 1
        assert "test.py" in loaded.modules


def test_storage_delete_graph():
    """Test deleting a graph from storage."""
    graph = Graph(project="delete-test")
    mod = Module(path="test.py", lang="python", lines=10)
    graph.add_module(mod)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Save
        storage.save_graph(graph, db_path=db_path)

        # Verify exists
        loaded = storage.load_graph("delete-test", db_path=db_path)
        assert loaded is not None

        # Delete
        result = storage.delete_project("delete-test", db_path=db_path)
        assert result is True

        # Verify deleted
        loaded = storage.load_graph("delete-test", db_path=db_path)
        assert loaded is None


def test_storage_search_interfaces():
    """Test searching for interfaces across projects."""
    graph1 = Graph(project="proj1")
    graph1.add_module(
        Module(
            path="a.py",
            lang="python",
            interfaces=[Interface(name="SharedClass", type="class", line=1)],
        )
    )

    graph2 = Graph(project="proj2")
    graph2.add_module(
        Module(
            path="b.py",
            lang="python",
            interfaces=[Interface(name="SharedClass", type="class", line=5)],
        )
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        storage.save_graph(graph1, db_path=db_path)
        storage.save_graph(graph2, db_path=db_path)

        # Search across projects
        results = storage.find_interface_across_projects("%SharedClass%", db_path=db_path)

        assert len(results) == 2
        projects = {r.project for r in results}
        assert "proj1" in projects
        assert "proj2" in projects


def test_topo_sort(sample_graph):
    """Test topological sorting of modules."""
    # Sort all modules
    modules = list(sample_graph.modules.keys())
    sorted_modules = sample_graph.topo_sort(modules)

    # module_c should come before module_b
    # module_b should come before module_a
    c_idx = sorted_modules.index("src/module_c.py")
    b_idx = sorted_modules.index("src/module_b.py")
    a_idx = sorted_modules.index("src/module_a.py")

    assert c_idx < b_idx
    assert b_idx < a_idx


def test_get_transitive_deps():
    """Test getting transitive dependencies."""
    # Create a fresh graph to avoid cache issues
    graph = Graph(project="test-deps")

    mod_a = Module(
        path="src/module_a.py",
        lang="python",
        deps_internal=["src/module_b.py"],
    )
    mod_b = Module(
        path="src/module_b.py",
        lang="python",
        deps_internal=["src/module_c.py"],
    )
    mod_c = Module(
        path="src/module_c.py",
        lang="python",
        deps_internal=[],
    )

    graph.add_module(mod_a)
    graph.add_module(mod_b)
    graph.add_module(mod_c)

    # module_a depends on module_b and transitively on module_c
    deps = graph.get_transitive_deps("src/module_a.py")

    assert "src/module_b.py" in deps
    assert "src/module_c.py" in deps
    assert "src/module_a.py" not in deps  # Shouldn't include itself
