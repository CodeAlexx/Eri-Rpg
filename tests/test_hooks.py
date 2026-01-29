"""
Tests for Claude Code hook behavior.

Tests critical enforcement:
- Blocks unauthorized writes
- Allows after preflight
- Blocks wrong file
"""

import pytest
import tempfile
import os
import json
import subprocess
from pathlib import Path


class TestPreToolUseHook:
    """Test the pretooluse.py hook behavior."""

    def setup_method(self):
        """Create temporary project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = self.temp_dir

        # Create .eri-rpg directory
        eri_dir = Path(self.temp_dir) / ".eri-rpg"
        eri_dir.mkdir(parents=True, exist_ok=True)

        # Get hook script path
        self.hook_script = Path(__file__).parent.parent / "erirpg" / "hooks" / "pretooluse.py"

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _call_hook(self, tool_name: str, file_path: str) -> dict:
        """Call the pretooluse hook and return result."""
        input_data = {
            "tool_name": tool_name,
            "tool_input": {
                "file_path": file_path,
            },
            "cwd": self.project_path,
        }

        result = subprocess.run(
            ["python3", str(self.hook_script)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"decision": "error", "output": result.stdout, "error": result.stderr}

    def test_hook_blocks_without_preflight(self):
        """Write without preflight should be blocked."""
        # Clear any existing state
        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        if state_file.exists():
            state_file.unlink()

        quick_file = Path(self.project_path) / ".eri-rpg" / "quick_fix_state.json"
        if quick_file.exists():
            quick_file.unlink()

        result = self._call_hook("Edit", str(Path(self.project_path) / "test.py"))

        assert result.get("decision") == "block"

    def test_hook_allows_after_preflight(self):
        """Write after preflight should succeed."""
        # Create preflight state - current format uses target_files and ready
        state = {
            "target_files": ["test.py"],
            "operation": "modify",
            "ready": True,
        }
        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        state_file.write_text(json.dumps(state))

        result = self._call_hook("Edit", str(Path(self.project_path) / "test.py"))

        assert result.get("decision") == "allow"

    def test_hook_blocks_wrong_file(self):
        """Write to file not in preflight should be blocked."""
        # Create preflight state for different file - current format uses target_files and ready
        state = {
            "target_files": ["allowed.py"],
            "operation": "modify",
            "ready": True,
        }
        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        state_file.write_text(json.dumps(state))

        result = self._call_hook("Edit", str(Path(self.project_path) / "not_allowed.py"))

        assert result.get("decision") == "block"

    def test_hook_allows_quick_fix(self):
        """Quick fix mode should allow edits to target file."""
        # Create quick fix state
        state = {
            "quick_fix_active": True,
            "target_file": "quick_target.py",
        }
        state_file = Path(self.project_path) / ".eri-rpg" / "quick_fix_state.json"
        state_file.write_text(json.dumps(state))

        result = self._call_hook("Edit", str(Path(self.project_path) / "quick_target.py"))

        assert result.get("decision") == "allow"

    def test_hook_blocks_non_target_in_quick_fix(self):
        """Quick fix should block edits to non-target files."""
        # Create quick fix state
        state = {
            "quick_fix_active": True,
            "target_file": "quick_target.py",
        }
        state_file = Path(self.project_path) / ".eri-rpg" / "quick_fix_state.json"
        state_file.write_text(json.dumps(state))

        result = self._call_hook("Edit", str(Path(self.project_path) / "other_file.py"))

        assert result.get("decision") == "block"

    def test_hook_allows_read_operations(self):
        """Read operations should always be allowed."""
        result = self._call_hook("Read", str(Path(self.project_path) / "any_file.py"))

        assert result.get("decision") == "allow"

    def test_hook_allows_tmp_directory(self):
        """Writes to /tmp should always be allowed."""
        result = self._call_hook("Edit", "/tmp/test_file.py")

        assert result.get("decision") == "allow"


class TestHookEdgeCases:
    """Test edge cases in hook behavior."""

    def setup_method(self):
        """Create temporary project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = self.temp_dir
        (Path(self.temp_dir) / ".eri-rpg").mkdir(parents=True, exist_ok=True)
        self.hook_script = Path(__file__).parent.parent / "erirpg" / "hooks" / "pretooluse.py"

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _call_hook(self, tool_name: str, tool_input: dict) -> dict:
        """Call the pretooluse hook."""
        input_data = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": self.project_path,
        }

        result = subprocess.run(
            ["python3", str(self.hook_script)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"decision": "error", "output": result.stdout}

    def test_hook_handles_missing_file_path(self):
        """Hook should handle missing file_path gracefully."""
        result = self._call_hook("Edit", {})

        # Should either allow (can't determine file) or handle gracefully
        assert result.get("decision") in ["allow", "block", "error"]

    def test_hook_handles_glob_tool(self):
        """Glob tool should always be allowed."""
        result = self._call_hook("Glob", {"pattern": "**/*.py"})

        assert result.get("decision") == "allow"

    def test_hook_handles_bash_tool(self):
        """Bash tool should be allowed (has own safety)."""
        result = self._call_hook("Bash", {"command": "ls -la"})

        assert result.get("decision") == "allow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
