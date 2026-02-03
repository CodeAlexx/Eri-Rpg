"""
Tests for the code indexer module.

Tests for:
- File finder functions (_find_python_files, _find_c_files, etc.)
- index_project function
- get_or_load_graph helper
- Error handling and edge cases
"""

import pytest
import os
import json
from pathlib import Path
from datetime import datetime

from erirpg.indexer import (
    _find_python_files,
    _find_c_files,
    _find_rust_files,
    _find_mojo_files,
    index_project,
    get_or_load_graph,
    STDLIB_MODULES,
)
from erirpg.registry import Project, Registry
from erirpg.graph import Graph


# =============================================================================
# File Finder Tests
# =============================================================================

class TestFileFinders:
    """Tests for language-specific file finder functions."""

    def test_find_python_files_basic(self, tmp_path):
        """_find_python_files finds .py files."""
        # Create test files
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "module.py").touch()

        files = _find_python_files(str(tmp_path))

        assert len(files) == 3
        assert any(f.endswith("main.py") for f in files)
        assert any(f.endswith("utils.py") for f in files)
        assert any(f.endswith("module.py") for f in files)

    def test_find_python_files_excludes_pycache(self, tmp_path):
        """_find_python_files excludes __pycache__ directories."""
        # Create valid file
        (tmp_path / "main.py").touch()

        # Create __pycache__ directory with .py file
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-39.py").touch()

        files = _find_python_files(str(tmp_path))

        assert len(files) == 1
        assert files[0].endswith("main.py")
        assert "__pycache__" not in files[0]

    def test_find_python_files_excludes_venv(self, tmp_path):
        """_find_python_files excludes venv directories."""
        # Create valid file
        (tmp_path / "main.py").touch()

        # Create venv directory
        venv = tmp_path / "venv" / "lib" / "python3.9"
        venv.mkdir(parents=True)
        (venv / "site.py").touch()

        files = _find_python_files(str(tmp_path))

        assert len(files) == 1
        assert files[0].endswith("main.py")
        assert "venv" not in files[0]

    def test_find_python_files_excludes_build(self, tmp_path):
        """_find_python_files excludes build directories."""
        # Create valid file
        (tmp_path / "main.py").touch()

        # Create build directory
        build = tmp_path / "build"
        build.mkdir()
        (build / "setup.py").touch()

        files = _find_python_files(str(tmp_path))

        assert len(files) == 1
        assert "build" not in files[0]

    def test_find_c_files_basic(self, tmp_path):
        """_find_c_files finds C/C++ files."""
        (tmp_path / "main.c").touch()
        (tmp_path / "utils.h").touch()
        (tmp_path / "module.cpp").touch()
        (tmp_path / "header.hpp").touch()

        files = _find_c_files(str(tmp_path))

        assert len(files) == 4
        assert any(f.endswith(".c") for f in files)
        assert any(f.endswith(".h") for f in files)
        assert any(f.endswith(".cpp") for f in files)
        assert any(f.endswith(".hpp") for f in files)

    def test_find_c_files_excludes_build(self, tmp_path):
        """_find_c_files excludes build directories."""
        (tmp_path / "main.c").touch()

        build = tmp_path / "build"
        build.mkdir()
        (build / "generated.c").touch()

        files = _find_c_files(str(tmp_path))

        assert len(files) == 1
        assert "build" not in files[0]

    def test_find_rust_files_basic(self, tmp_path):
        """_find_rust_files finds .rs files."""
        (tmp_path / "main.rs").touch()
        src = tmp_path / "src"
        src.mkdir()
        (src / "lib.rs").touch()

        files = _find_rust_files(str(tmp_path))

        assert len(files) == 2
        assert any(f.endswith("main.rs") for f in files)
        assert any(f.endswith("lib.rs") for f in files)

    def test_find_rust_files_excludes_target(self, tmp_path):
        """_find_rust_files excludes target directory."""
        (tmp_path / "main.rs").touch()

        target = tmp_path / "target" / "debug"
        target.mkdir(parents=True)
        (target / "build.rs").touch()

        files = _find_rust_files(str(tmp_path))

        assert len(files) == 1
        assert "target" not in files[0]

    def test_find_mojo_files_basic(self, tmp_path):
        """_find_mojo_files finds .mojo files."""
        (tmp_path / "main.mojo").touch()
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.mojo").touch()

        files = _find_mojo_files(str(tmp_path))

        assert len(files) == 2
        assert any(f.endswith(".mojo") for f in files)


# =============================================================================
# index_project Tests
# =============================================================================

class TestIndexProject:
    """Tests for the main index_project function."""

    def test_index_creates_graph(self, tmp_path):
        """index_project creates a graph with modules."""
        # Create a simple Python file
        test_file = tmp_path / "simple.py"
        test_file.write_text("""
def hello():
    \"\"\"Say hello.\"\"\"
    return "Hello, world!"
""")

        # Create project
        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        # Create .eri-rpg directory
        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")

        # Index project
        graph = index_project(project, verbose=False)

        # Verify graph was created
        assert graph is not None
        assert graph.project == "test"
        assert len(graph.modules) > 0

        # Check that simple.py was indexed
        assert "simple.py" in graph.modules
        module = graph.modules["simple.py"]
        assert module.lang == "python"
        assert module.lines > 0

    def test_index_handles_parse_errors(self, tmp_path):
        """index_project continues on parse errors."""
        # Create valid file
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("def valid(): pass")

        # Create file with syntax error
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(:\n    pass")

        # Create project
        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")

        # Index should succeed despite bad file
        graph = index_project(project, verbose=False)

        # Valid file should be indexed
        assert "valid.py" in graph.modules

    def test_index_resolves_internal_deps(self, tmp_path):
        """index_project resolves internal dependencies."""
        # Create module A
        module_a = tmp_path / "module_a.py"
        module_a.write_text("""
def func_a():
    return "A"
""")

        # Create module B that imports A
        module_b = tmp_path / "module_b.py"
        module_b.write_text("""
from module_a import func_a

def func_b():
    return func_a() + "B"
""")

        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")

        graph = index_project(project, verbose=False)

        # Check that module_b depends on module_a
        module_b_obj = graph.modules["module_b.py"]
        assert "module_a.py" in module_b_obj.deps_internal

    def test_index_filters_stdlib_deps(self, tmp_path):
        """index_project filters out stdlib from external deps."""
        # Create module that imports stdlib
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
import json

def test():
    pass
""")

        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")

        graph = index_project(project, verbose=False)

        # Stdlib should NOT be in external deps
        module = graph.modules["test.py"]
        assert "os" not in module.deps_external
        assert "sys" not in module.deps_external
        assert "pathlib" not in module.deps_external
        assert "json" not in module.deps_external

    def test_index_includes_third_party_deps(self, tmp_path):
        """index_project includes third-party packages in external deps."""
        # Create module with third-party imports
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import click
import pytest
from flask import Flask

def test():
    pass
""")

        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")

        graph = index_project(project, verbose=False)

        # Third-party should be in external deps
        module = graph.modules["test.py"]
        assert "click" in module.deps_external
        assert "pytest" in module.deps_external
        assert "flask" in module.deps_external

    def test_index_saves_to_json(self, tmp_path):
        """index_project saves graph to JSON file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        graph_path = eri_dir / "graph.json"
        project.graph_path = str(graph_path)

        index_project(project, verbose=False)

        # Verify JSON file was created
        assert graph_path.exists()

        # Verify it's valid JSON
        with open(graph_path) as f:
            data = json.load(f)

        assert data["project"] == "test"
        assert "modules" in data


# =============================================================================
# get_or_load_graph Tests
# =============================================================================

class TestGetOrLoadGraph:
    """Tests for the get_or_load_graph helper function."""

    def test_load_from_json(self, tmp_path):
        """get_or_load_graph loads from JSON when available."""
        # Create and index a project
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        eri_dir = tmp_path / ".eri-rpg"
        eri_dir.mkdir()
        project.graph_path = str(eri_dir / "graph.json")
        project.indexed_at = datetime.now()

        # Index to create graph.json
        index_project(project, verbose=False)

        # Load using helper
        graph = get_or_load_graph(project, prefer_sqlite=False)

        assert graph is not None
        assert graph.project == "test"
        assert len(graph.modules) > 0

    def test_raises_on_unindexed_project(self, tmp_path):
        """get_or_load_graph raises ValueError for unindexed project."""
        project = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
        )

        # No indexing done
        with pytest.raises(ValueError, match="not indexed"):
            get_or_load_graph(project, prefer_sqlite=False)


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_stdlib_modules_defined(self):
        """STDLIB_MODULES is defined and non-empty."""
        assert STDLIB_MODULES is not None
        assert len(STDLIB_MODULES) > 100

        # Check some common stdlib modules
        assert "os" in STDLIB_MODULES
        assert "sys" in STDLIB_MODULES
        assert "json" in STDLIB_MODULES
        assert "pathlib" in STDLIB_MODULES
        assert "datetime" in STDLIB_MODULES
        assert "typing" in STDLIB_MODULES
