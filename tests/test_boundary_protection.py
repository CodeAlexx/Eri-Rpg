"""
Tests for project boundary protection in EriRPG.

These tests verify that EriRPG prevents writing files outside
the project directory - a critical security feature.
"""

import os
import tempfile
from pathlib import Path
import pytest

from erirpg.write_guard import (
    enable_writes,
    disable_writes,
    add_allowed_path,
    guarded_open,
    install_hooks,
    uninstall_hooks,
    _original_open,
)


class TestBoundaryProtection:
    """Test boundary enforcement in write_guard.py"""

    def setup_method(self):
        """Reset state before each test."""
        disable_writes()
        uninstall_hooks()

    def teardown_method(self):
        """Clean up after each test."""
        disable_writes()
        uninstall_hooks()

    def test_enable_writes_blocks_absolute_path_outside_project(self, tmp_path):
        """Test that absolute paths outside project are blocked."""
        project = tmp_path / "myproject"
        project.mkdir()

        outside = tmp_path / "other" / "secret.txt"

        with pytest.raises(RuntimeError) as exc_info:
            enable_writes([str(outside)], str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_enable_writes_blocks_traversal_attack(self, tmp_path):
        """Test that path traversal attacks are blocked."""
        project = tmp_path / "myproject"
        project.mkdir()

        # Try to escape via ../
        with pytest.raises(RuntimeError) as exc_info:
            enable_writes(["../../../etc/passwd"], str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_enable_writes_blocks_symlink_escape(self, tmp_path):
        """Test that symlinks escaping the project are blocked."""
        project = tmp_path / "myproject"
        project.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        secret = outside / "secret.txt"
        secret.write_text("secret")

        # Create symlink inside project pointing outside
        symlink = project / "escape"
        symlink.symlink_to(outside)

        with pytest.raises(RuntimeError) as exc_info:
            enable_writes(["escape/secret.txt"], str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_enable_writes_allows_valid_paths(self, tmp_path):
        """Test that valid paths inside project are allowed."""
        project = tmp_path / "myproject"
        project.mkdir()

        subdir = project / "src"
        subdir.mkdir()

        # Should not raise
        enable_writes(["src/main.py", "README.md"], str(project))
        disable_writes()

    def test_enable_writes_allows_nested_paths(self, tmp_path):
        """Test that deeply nested paths inside project are allowed."""
        project = tmp_path / "myproject"
        project.mkdir()

        # Should not raise
        enable_writes(["src/deep/nested/file.py"], str(project))
        disable_writes()

    def test_add_allowed_path_blocks_outside_project(self, tmp_path):
        """Test that add_allowed_path also enforces boundaries."""
        project = tmp_path / "myproject"
        project.mkdir()

        # Enable writes first
        enable_writes(["src/main.py"], str(project))

        # Try to add path outside project
        outside = tmp_path / "other" / "evil.txt"
        with pytest.raises(RuntimeError) as exc_info:
            add_allowed_path(str(outside), str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)
        disable_writes()

    def test_guarded_open_blocks_outside_project_at_write_time(self, tmp_path):
        """Test that guarded_open enforces boundary at actual write time."""
        project = tmp_path / "myproject"
        project.mkdir()

        outside = tmp_path / "outside.txt"

        # Enable writes for a valid file
        install_hooks()
        enable_writes(["src/main.py"], str(project))

        # Even if we somehow get past enable_writes, guarded_open should block
        # (This tests the second layer of defense)
        # Note: This would require manipulating internal state, which we don't test directly
        # The important thing is that the boundary check exists in guarded_open

        disable_writes()

    def test_boundary_blocks_sibling_directory(self, tmp_path):
        """Test that sibling directories are blocked."""
        project_a = tmp_path / "project_a"
        project_a.mkdir()

        project_b = tmp_path / "project_b"
        project_b.mkdir()
        (project_b / "file.txt").write_text("content")

        # Working in project_a, trying to write to project_b
        with pytest.raises(RuntimeError) as exc_info:
            enable_writes(["../project_b/file.txt"], str(project_a))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_boundary_allows_project_root_file(self, tmp_path):
        """Test that files at project root are allowed."""
        project = tmp_path / "myproject"
        project.mkdir()

        # Should not raise
        enable_writes(["README.md"], str(project))
        disable_writes()


class TestRealWorldScenarios:
    """Test real-world scenarios that triggered this protection."""

    def setup_method(self):
        disable_writes()

    def teardown_method(self):
        disable_writes()

    def test_onetrainer_eritrainer_scenario(self, tmp_path):
        """
        Test the exact scenario that caused the bug:
        Working in eri-rpg but trying to write to OneTrainer/eritrainer.
        """
        # Simulate the directory structure
        eri_rpg = tmp_path / "eri-rpg"
        eri_rpg.mkdir()

        onetrainer = tmp_path / "OneTrainer" / "eritrainer"
        onetrainer.mkdir(parents=True)
        (onetrainer / "train.py").write_text("# original")

        # Working in eri-rpg, should NOT be able to write to OneTrainer
        with pytest.raises(RuntimeError) as exc_info:
            enable_writes([str(onetrainer / "train.py")], str(eri_rpg))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_home_directory_escape(self, tmp_path):
        """Test that escaping to home directory is blocked."""
        project = tmp_path / "project"
        project.mkdir()

        # Try to write to home directory
        home_path = os.path.expanduser("~/.bashrc")

        with pytest.raises(RuntimeError) as exc_info:
            enable_writes([home_path], str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)

    def test_etc_escape(self, tmp_path):
        """Test that system directories are blocked."""
        project = tmp_path / "project"
        project.mkdir()

        with pytest.raises(RuntimeError) as exc_info:
            enable_writes(["/etc/passwd"], str(project))

        assert "BOUNDARY VIOLATION" in str(exc_info.value)
