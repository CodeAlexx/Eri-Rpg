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
        """Create temporary project structure.

        IMPORTANT: Uses ~/.eri-rpg-test/ instead of /tmp/ because the hook
        has a passthrough for /tmp/ files (always allows temp file writes).
        """
        # Use home directory instead of /tmp to avoid passthrough
        self.temp_dir = str(Path.home() / ".eri-rpg-test" / f"test-{os.getpid()}")
        self.project_path = self.temp_dir
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

        # Create .eri-rpg directory
        eri_dir = Path(self.temp_dir) / ".eri-rpg"
        eri_dir.mkdir(parents=True, exist_ok=True)

        # Set mode to maintain (enforcement requires maintain mode)
        config_file = eri_dir / "config.json"
        config_file.write_text(json.dumps({"mode": "maintain"}))

        # Create runs directory for active run detection
        runs_dir = eri_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        # Get hook script path
        self.hook_script = Path(__file__).parent.parent / "erirpg" / "hooks" / "pretooluse.py"

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Also clean parent if empty
        parent = Path(self.temp_dir).parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

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
        # Create active run (required before preflight check)
        runs_dir = Path(self.project_path) / ".eri-rpg" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_state = {"id": "test-run", "completed_at": None}
        (runs_dir / "test-run.json").write_text(json.dumps(run_state))

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
        # Create active run (required before preflight check)
        runs_dir = Path(self.project_path) / ".eri-rpg" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_state = {"id": "test-run", "completed_at": None}
        (runs_dir / "test-run.json").write_text(json.dumps(run_state))

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
        """Read operations should always be allowed (passthrough)."""
        result = self._call_hook("Read", str(Path(self.project_path) / "any_file.py"))

        # Hook returns {} for passthrough (tools not in watch list)
        assert result.get("decision") != "block"

    def test_hook_allows_tmp_directory(self):
        """Writes to /tmp should always be allowed (passthrough)."""
        result = self._call_hook("Edit", "/tmp/test_file.py")

        # Hook returns {} for passthrough (/tmp always allowed)
        assert result.get("decision") != "block"


class TestHookEdgeCases:
    """Test edge cases in hook behavior."""

    def setup_method(self):
        """Create temporary project structure.

        Uses ~/.eri-rpg-test/ to avoid /tmp passthrough.
        """
        self.temp_dir = str(Path.home() / ".eri-rpg-test" / f"edge-{os.getpid()}")
        self.project_path = self.temp_dir
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

        eri_dir = Path(self.temp_dir) / ".eri-rpg"
        eri_dir.mkdir(parents=True, exist_ok=True)

        # Set mode to maintain (enforcement requires maintain mode)
        config_file = eri_dir / "config.json"
        config_file.write_text(json.dumps({"mode": "maintain"}))

        self.hook_script = Path(__file__).parent.parent / "erirpg" / "hooks" / "pretooluse.py"

    def teardown_method(self):
        """Cleanup temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Also clean parent if empty
        parent = Path(self.temp_dir).parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

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

        # Should passthrough (can't determine file) - returns {}
        assert result.get("decision") != "block" or result.get("decision") is None

    def test_hook_handles_glob_tool(self):
        """Glob tool should always be allowed (passthrough)."""
        result = self._call_hook("Glob", {"pattern": "**/*.py"})

        # Hook returns {} for tools not in watch list
        assert result.get("decision") != "block"

    def test_hook_handles_bash_tool(self):
        """Bash tool without file writes should be allowed (passthrough)."""
        result = self._call_hook("Bash", {"command": "ls -la"})

        # Hook returns {} for Bash commands that don't write files
        assert result.get("decision") != "block"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
