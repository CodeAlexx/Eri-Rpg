#!/usr/bin/env python3
"""
PostToolUse hook for EriRPG - Track modified files for verification-gated commit.

This hook does NOT auto-commit on every edit. Instead it:
1. Tracks files that were modified
2. After edits, user/Claude runs verification
3. Only after verification passes does commit happen

The actual commit happens via:
- Agent.complete_step() with auto_commit=True (runs verification first)
- verify_and_commit() function (standalone verification + commit)
- /eri:done command (runs verification then commits)

This hook just tracks modified files so we know what to commit.

Input (JSON on stdin):
{
  "tool_name": "Edit",
  "tool_input": {"file_path": "/path/to/file.py", ...},
  "cwd": "/current/working/directory"
}

Output (JSON to stdout):
{
  "continue": true
}
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Log file for debugging
LOG_FILE = "/tmp/erirpg-posttooluse.log"

# Track modified files per project
MODIFIED_FILES_STORE = "/tmp/erirpg-modified-files.json"


def log(msg: str) -> None:
    """Append to log file."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def find_project_root(file_path: str) -> str | None:
    """Find project root from file path.

    Detects both:
    - EriRPG projects (.eri-rpg/ directory)
    - Coder workflow projects (.planning/ directory)

    Excludes ~/.eri-rpg (global state dir) from being treated as a project.
    """
    path = Path(file_path).resolve()
    home = Path.home()

    for parent in [path] + list(path.parents):
        # Stop before home - ~/.eri-rpg is global state, not a project
        if parent == home or parent == Path("/"):
            break
        # Check for either project type
        if (parent / ".eri-rpg").is_dir() or (parent / ".planning").is_dir():
            return str(parent)

    return None


def load_modified_files() -> dict:
    """Load tracked modified files."""
    try:
        if os.path.exists(MODIFIED_FILES_STORE):
            with open(MODIFIED_FILES_STORE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_modified_files(data: dict) -> None:
    """Save tracked modified files."""
    try:
        with open(MODIFIED_FILES_STORE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Failed to save modified files: {e}")


def track_modified_file(file_path: str, project_path: str) -> None:
    """Track a file as modified for later commit."""
    data = load_modified_files()

    if project_path not in data:
        data[project_path] = {
            "files": [],
            "started": datetime.now().isoformat(),
        }

    if file_path not in data[project_path]["files"]:
        data[project_path]["files"].append(file_path)
        data[project_path]["last_modified"] = datetime.now().isoformat()
        log(f"Tracked: {file_path} in {project_path}")

    save_modified_files(data)

    # Update active edited project in global state for statusline
    update_active_edited_project(project_path)


def update_active_edited_project(project_path: str) -> None:
    """Update global state with the project being actively edited.

    Simple: just use the directory name. No registry lookups.
    """
    state_path = Path.home() / ".eri-rpg" / "state.json"
    project_name = Path(project_path).name

    try:
        state = {}
        if state_path.exists():
            state = json.loads(state_path.read_text())

        state["active_edited_project"] = project_name
        state["active_edited_at"] = datetime.now().isoformat()
        # Also set active_project so /coder:init knows where to resume after /clear
        state["active_project"] = project_name
        state["active_project_path"] = project_path

        state_path.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log(f"Failed to update active edited project: {e}")


def run_verification_and_commit(project_path: str) -> None:
    """Run verification and auto-commit if it passes."""
    try:
        from erirpg.verification import (
            Verifier,
            load_verification_config,
            get_default_python_config,
        )

        # Load or auto-detect verification config
        config = load_verification_config(project_path)
        if not config:
            # Auto-detect Python project
            if (Path(project_path) / "pyproject.toml").exists() or \
               (Path(project_path) / "tests").exists():
                config = get_default_python_config()

        if not config:
            # No verification - just commit
            _auto_commit_no_verify(project_path)
            return

        # Run verification with auto-commit enabled
        verifier = Verifier(config, project_path)
        result = verifier.run_verification("post-edit", auto_commit=True)

        if result.passed:
            log(f"Verification passed, auto-committed in {project_path}")
        else:
            log(f"Verification failed in {project_path}, no commit")

    except Exception as e:
        log(f"Verification error: {e}")


def _auto_commit_no_verify(project_path: str) -> None:
    """Auto-commit when no verification is configured."""
    import subprocess
    try:
        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True, timeout=30)

        # Check if anything to commit
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=project_path, capture_output=True, timeout=10)
        if result.returncode == 0:
            return  # Nothing to commit

        # Commit
        subprocess.run(
            ["git", "commit", "-m", "chore: auto-commit (no verification configured)"],
            cwd=project_path, capture_output=True, timeout=30
        )
        log(f"Auto-committed (no verify) in {project_path}")
    except Exception as e:
        log(f"Auto-commit error: {e}")


def main():
    """Process PostToolUse hook - track modified files."""
    try:
        input_data = json.loads(sys.stdin.read())

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", os.getcwd())

        # Project detection - early exit if not a tracked project
        # Tracks both EriRPG (.eri-rpg/) and coder workflow (.planning/) projects
        project_root = None
        check = cwd
        while check != '/':
            if os.path.isdir(os.path.join(check, '.eri-rpg')) or os.path.isdir(os.path.join(check, '.planning')):
                project_root = check
                break
            check = os.path.dirname(check)

        if project_root is None:
            # Not a tracked project. Output empty and exit.
            print(json.dumps({"continue": True}))
            return

        # Only track file edit tools
        if tool_name not in ("Edit", "Write", "MultiEdit"):
            print(json.dumps({"continue": True}))
            return

        # Get file path
        file_path = tool_input.get("file_path", "")
        if not file_path:
            print(json.dumps({"continue": True}))
            return

        # Make absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(cwd, file_path)
        file_path = os.path.realpath(file_path)

        # Find project root
        project_path = find_project_root(file_path)
        if not project_path:
            print(json.dumps({"continue": True}))
            return

        # Track the file
        track_modified_file(file_path, project_path)

        # Run verification and auto-commit if passes
        run_verification_and_commit(project_path)

        print(json.dumps({"continue": True}))

    except Exception as e:
        log(f"Hook error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
