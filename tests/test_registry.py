"""
Tests for project registry functionality.

Covers:
- Project dataclass (to_dict/from_dict, is_indexed, index_age_days)
- Registry operations (add, remove, get, list)
- Persistence (save, load, singleton)
- Language detection
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from erirpg.registry import Project, Registry, detect_project_language


class TestProject:
    """Test Project dataclass."""

    def test_project_creation(self):
        """Test basic project creation."""
        p = Project(name="test", path="/tmp/test", lang="python")
        assert p.name == "test"
        assert p.path == "/tmp/test"
        assert p.lang == "python"
        assert p.indexed_at is None
        assert p.description == ""
        assert p.todos == []
        assert p.notes == ""

    def test_project_graph_path_default(self):
        """Test graph_path is auto-generated."""
        p = Project(name="test", path="/tmp/test", lang="python")
        assert p.graph_path == "/tmp/test/.eri-rpg/graph.json"

    def test_project_graph_path_custom(self):
        """Test custom graph_path."""
        p = Project(name="test", path="/tmp/test", lang="python",
                   graph_path="/custom/path/graph.json")
        assert p.graph_path == "/custom/path/graph.json"

    def test_to_dict(self):
        """Test Project.to_dict()."""
        indexed_time = datetime.now()
        p = Project(
            name="test",
            path="/tmp/test",
            lang="python",
            indexed_at=indexed_time,
            description="Test project",
            todos=["task1", "task2"],
            notes="Some notes"
        )

        d = p.to_dict()
        assert d["name"] == "test"
        assert d["path"] == "/tmp/test"
        assert d["lang"] == "python"
        assert d["indexed_at"] == indexed_time.isoformat()
        assert d["description"] == "Test project"
        assert d["todos"] == ["task1", "task2"]
        assert d["notes"] == "Some notes"

    def test_to_dict_no_indexed_at(self):
        """Test to_dict with no indexed_at."""
        p = Project(name="test", path="/tmp/test", lang="python")
        d = p.to_dict()
        assert d["indexed_at"] is None

    def test_from_dict(self):
        """Test Project.from_dict()."""
        indexed_time = datetime.now()
        d = {
            "name": "test",
            "path": "/tmp/test",
            "lang": "python",
            "indexed_at": indexed_time.isoformat(),
            "graph_path": "/custom/graph.json",
            "description": "Test project",
            "todos": ["task1"],
            "notes": "Notes"
        }

        p = Project.from_dict(d)
        assert p.name == "test"
        assert p.path == "/tmp/test"
        assert p.lang == "python"
        assert p.indexed_at.isoformat() == indexed_time.isoformat()
        assert p.graph_path == "/custom/graph.json"
        assert p.description == "Test project"
        assert p.todos == ["task1"]
        assert p.notes == "Notes"

    def test_from_dict_minimal(self):
        """Test from_dict with minimal data."""
        d = {"name": "test", "path": "/tmp/test", "lang": "python"}
        p = Project.from_dict(d)
        assert p.name == "test"
        assert p.indexed_at is None
        assert p.description == ""
        assert p.todos == []

    def test_is_indexed_false(self):
        """Test is_indexed returns False when not indexed."""
        p = Project(name="test", path="/tmp/test", lang="python")
        assert p.is_indexed() is False

    def test_is_indexed_false_no_graph_file(self):
        """Test is_indexed returns False when graph file doesn't exist."""
        p = Project(name="test", path="/tmp/test", lang="python",
                   indexed_at=datetime.now())
        assert p.is_indexed() is False

    def test_is_indexed_true(self, tmp_path):
        """Test is_indexed returns True when graph exists."""
        # Create graph file
        graph_dir = tmp_path / ".eri-rpg"
        graph_dir.mkdir()
        graph_file = graph_dir / "graph.json"
        graph_file.write_text("{}")

        p = Project(
            name="test",
            path=str(tmp_path),
            lang="python",
            indexed_at=datetime.now()
        )
        assert p.is_indexed() is True

    def test_index_age_days_none(self):
        """Test index_age_days returns None when not indexed."""
        p = Project(name="test", path="/tmp/test", lang="python")
        assert p.index_age_days() is None

    def test_index_age_days_recent(self):
        """Test index_age_days for recent index."""
        p = Project(name="test", path="/tmp/test", lang="python",
                   indexed_at=datetime.now())
        age = p.index_age_days()
        assert age is not None
        assert age < 0.1  # Less than 0.1 days (2.4 hours)

    def test_index_age_days_old(self):
        """Test index_age_days for old index."""
        old_time = datetime.now() - timedelta(days=5)
        p = Project(name="test", path="/tmp/test", lang="python",
                   indexed_at=old_time)
        age = p.index_age_days()
        assert age is not None
        assert 4.9 < age < 5.1  # Approximately 5 days


class TestRegistry:
    """Test Registry class."""

    @pytest.fixture
    def temp_registry(self, tmp_path):
        """Create a registry with temporary config dir."""
        config_dir = str(tmp_path / "config")
        registry = Registry(config_dir=config_dir)
        return registry

    def test_registry_creation(self, temp_registry):
        """Test basic registry creation."""
        assert temp_registry.projects == {}
        assert temp_registry.config_dir.endswith("config")

    def test_add_project(self, temp_registry, tmp_path):
        """Test adding a project."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        p = temp_registry.add("test", str(project_dir), "python")
        assert p.name == "test"
        assert p.path == str(project_dir)
        assert p.lang == "python"
        assert "test" in temp_registry.projects

    def test_add_project_duplicate_name(self, temp_registry, tmp_path):
        """Test adding project with duplicate name raises error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        temp_registry.add("test", str(project_dir), "python")

        with pytest.raises(ValueError, match="already exists"):
            temp_registry.add("test", str(project_dir), "python")

    def test_add_project_nonexistent_path(self, temp_registry):
        """Test adding project with non-existent path raises error."""
        with pytest.raises(FileNotFoundError):
            temp_registry.add("test", "/nonexistent/path", "python")

    def test_add_project_expands_path(self, temp_registry, tmp_path):
        """Test adding project expands relative paths."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Use relative path
        os.chdir(tmp_path)
        p = temp_registry.add("test", "project", "python")

        # Should be absolute
        assert os.path.isabs(p.path)
        assert p.path.endswith("project")

    def test_remove_project(self, temp_registry, tmp_path):
        """Test removing a project."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        temp_registry.add("test", str(project_dir), "python")
        assert "test" in temp_registry.projects

        result = temp_registry.remove("test")
        assert result is True
        assert "test" not in temp_registry.projects

    def test_remove_nonexistent_project(self, temp_registry):
        """Test removing non-existent project returns False."""
        result = temp_registry.remove("nonexistent")
        assert result is False

    def test_get_project(self, temp_registry, tmp_path):
        """Test getting a project."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        temp_registry.add("test", str(project_dir), "python")

        p = temp_registry.get("test")
        assert p is not None
        assert p.name == "test"

    def test_get_nonexistent_project(self, temp_registry):
        """Test getting non-existent project returns None."""
        p = temp_registry.get("nonexistent")
        assert p is None

    def test_list_projects(self, temp_registry, tmp_path):
        """Test listing projects."""
        # Create multiple projects
        for i in range(3):
            project_dir = tmp_path / f"project{i}"
            project_dir.mkdir()
            temp_registry.add(f"test{i}", str(project_dir), "python")

        projects = temp_registry.list()
        assert len(projects) == 3
        names = {p.name for p in projects}
        assert names == {"test0", "test1", "test2"}

    def test_list_empty_registry(self, temp_registry):
        """Test listing empty registry."""
        projects = temp_registry.list()
        assert projects == []

    def test_save_and_load(self, temp_registry, tmp_path):
        """Test saving and loading registry."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Add project and save
        temp_registry.add("test", str(project_dir), "python")
        temp_registry.projects["test"].description = "Test desc"
        temp_registry.save()

        # Create new registry and load
        new_registry = Registry(config_dir=temp_registry.config_dir)
        new_registry.load()

        assert "test" in new_registry.projects
        p = new_registry.get("test")
        assert p.name == "test"
        assert p.path == str(project_dir)
        assert p.description == "Test desc"

    def test_load_nonexistent_file(self, temp_registry):
        """Test loading when registry file doesn't exist."""
        temp_registry.load()
        assert temp_registry.projects == {}

    def test_save_creates_directory(self, tmp_path):
        """Test save creates config directory if needed."""
        config_dir = str(tmp_path / "new_config")
        registry = Registry(config_dir=config_dir)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        registry.add("test", str(project_dir), "python")

        assert os.path.exists(config_dir)
        assert os.path.exists(os.path.join(config_dir, "registry.json"))

    def test_update_indexed(self, temp_registry, tmp_path):
        """Test update_indexed marks project as indexed."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        temp_registry.add("test", str(project_dir), "python")
        p = temp_registry.get("test")
        assert p.indexed_at is None

        # Update indexed
        temp_registry.update_indexed("test")

        p = temp_registry.get("test")
        assert p.indexed_at is not None
        assert p.index_age_days() is not None
        assert p.index_age_days() < 0.1

    def test_update_indexed_nonexistent(self, temp_registry):
        """Test update_indexed with non-existent project does nothing."""
        temp_registry.update_indexed("nonexistent")  # Should not raise

    def test_get_instance(self):
        """Test get_instance returns registry."""
        # This will use ~/.eri-rpg - just verify it works
        registry = Registry.get_instance()
        assert isinstance(registry, Registry)


class TestLanguageDetection:
    """Test detect_project_language function."""

    def test_detect_rust(self, tmp_path):
        """Test detecting Rust project."""
        cargo_file = tmp_path / "Cargo.toml"
        cargo_file.write_text("[package]\nname = 'test'\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "rust"

    def test_detect_mojo(self, tmp_path):
        """Test detecting Mojo project."""
        mojo_file = tmp_path / "mojoproject.toml"
        mojo_file.write_text("[project]\nname = 'test'\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "mojo"

    def test_detect_python_pyproject(self, tmp_path):
        """Test detecting Python project via pyproject.toml."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "python"

    def test_detect_python_setup(self, tmp_path):
        """Test detecting Python project via setup.py."""
        setup_file = tmp_path / "setup.py"
        setup_file.write_text("from setuptools import setup\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "python"

    def test_detect_python_by_files(self, tmp_path):
        """Test detecting Python by counting .py files."""
        for i in range(5):
            py_file = tmp_path / f"module{i}.py"
            py_file.write_text("# Python file\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "python"

    def test_detect_c_by_files(self, tmp_path):
        """Test detecting C by counting .c files."""
        for i in range(5):
            c_file = tmp_path / f"module{i}.c"
            c_file.write_text("// C file\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "c"

    def test_detect_unknown(self, tmp_path):
        """Test detecting unknown language."""
        # Empty directory
        lang = detect_project_language(str(tmp_path))
        assert lang == "unknown"

    def test_detect_mixed_majority(self, tmp_path):
        """Test detecting language by majority in mixed project."""
        # More Python files
        for i in range(6):
            py_file = tmp_path / f"module{i}.py"
            py_file.write_text("# Python\n")

        # Fewer C files
        for i in range(2):
            c_file = tmp_path / f"file{i}.c"
            c_file.write_text("// C\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "python"

    def test_detect_skips_hidden_dirs(self, tmp_path):
        """Test detection skips hidden directories."""
        # Create .git directory with many files
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        for i in range(20):
            (git_dir / f"file{i}.c").write_text("// C\n")

        # Create Python file in main directory
        (tmp_path / "main.py").write_text("# Python\n")

        lang = detect_project_language(str(tmp_path))
        assert lang == "python"

    def test_detect_expands_path(self, tmp_path):
        """Test detection expands ~ in path."""
        # Just verify it doesn't crash with home directory
        home = os.path.expanduser("~")
        if os.path.exists(home):
            lang = detect_project_language("~")
            assert lang in ["python", "rust", "c", "mojo", "unknown"]
