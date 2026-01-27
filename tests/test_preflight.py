"""
Tests for preflight behavior.

Tests critical EriRPG enforcement:
- Blocks edits without learning
- Passes with learning
- Detects stale learning
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPreflightBlocking:
    """Test that preflight blocks unauthorized changes."""

    def setup_method(self):
        """Create temporary project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = self.temp_dir

        # Create .eri-rpg directory
        eri_dir = Path(self.temp_dir) / ".eri-rpg"
        eri_dir.mkdir(parents=True, exist_ok=True)

        # Create a test file
        test_file = Path(self.temp_dir) / "test_module.py"
        test_file.write_text("# Test module\ndef hello():\n    return 'world'\n")

        # Create empty knowledge.json
        knowledge_file = eri_dir / "knowledge.json"
        knowledge_file.write_text('{"learnings": {}, "version": "2.0"}')

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preflight_blocks_without_learning(self):
        """Preflight should return ready=False if module not learned."""
        from erirpg.preflight import preflight

        report = preflight(
            project_path=self.project_path,
            files=["test_module.py"],
            operation="modify",
            strict=True,  # Strict mode requires learning
        )

        assert not report.ready
        assert len(report.must_learn_first) > 0

    def test_preflight_passes_with_learning(self):
        """Preflight should return ready=True after learning."""
        from erirpg.preflight import preflight
        from erirpg.memory import load_knowledge

        # Add learning for the module
        knowledge = load_knowledge(self.project_path)
        knowledge.learn(
            module_path="test_module.py",
            summary="Test module",
            purpose="Testing",
        )

        report = preflight(
            project_path=self.project_path,
            files=["test_module.py"],
            operation="modify",
            strict=True,
        )

        assert report.ready
        assert len(report.must_learn_first) == 0

    def test_preflight_detects_stale_learning(self):
        """Preflight should warn if file changed since learning."""
        from erirpg.preflight import preflight
        from erirpg.memory import load_knowledge

        # Add learning
        knowledge = load_knowledge(self.project_path)
        knowledge.learn(
            module_path="test_module.py",
            summary="Test module",
            purpose="Testing",
        )

        # Modify the file after learning
        test_file = Path(self.temp_dir) / "test_module.py"
        test_file.write_text("# Modified!\ndef hello():\n    return 'changed'\n")

        report = preflight(
            project_path=self.project_path,
            files=["test_module.py"],
            operation="modify",
            strict=True,
        )

        # Should still pass but have stale warning
        # (or block if strict about staleness)
        assert "stale" in str(report.warnings).lower() or not report.ready

    def test_preflight_allows_new_files(self):
        """Preflight should allow creating new files."""
        from erirpg.preflight import preflight

        report = preflight(
            project_path=self.project_path,
            files=["new_file.py"],
            operation="create",
            strict=False,
        )

        # Creating new files shouldn't require learning
        assert report.ready

    def test_preflight_non_strict_mode(self):
        """Non-strict preflight should pass without learning."""
        from erirpg.preflight import preflight

        report = preflight(
            project_path=self.project_path,
            files=["test_module.py"],
            operation="modify",
            strict=False,  # Non-strict mode
        )

        # Should pass even without learning
        assert report.ready


class TestPreflightState:
    """Test preflight state file management."""

    def setup_method(self):
        """Create temporary project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = self.temp_dir
        (Path(self.temp_dir) / ".eri-rpg").mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preflight_saves_state(self):
        """Preflight should save state file for hooks."""
        from erirpg.preflight import preflight

        report = preflight(
            project_path=self.project_path,
            files=["test.py"],
            operation="create",
            strict=False,
        )

        # Check state file exists
        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        assert state_file.exists()

        # Check state content
        state = json.loads(state_file.read_text())
        assert "test.py" in state.get("allowed_files", [])

    def test_preflight_state_cleared_on_complete(self):
        """Preflight state should be clearable."""
        from erirpg.preflight import preflight, clear_preflight_state

        preflight(
            project_path=self.project_path,
            files=["test.py"],
            operation="create",
            strict=False,
        )

        clear_preflight_state(self.project_path)

        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        assert not state_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
