"""
EriRPG Quick Fix Mode - Lightweight single-file edits.

Skip the full spec ceremony for simple, focused changes:
- Single-file edits
- Small bug fixes
- Minor improvements
- Quick tweaks

No run state, no spec, no steps. Just:
1. Auto-preflight (strict=False)
2. Snapshot file
3. Allow edit
4. Auto-commit with description
5. Done

Usage:
    from erirpg.quick import quick_fix

    commit = quick_fix("myproject", "path/to/file.py", "Fix typo in docstring")

Or via CLI:
    eri-rpg quick myproject path/to/file.py "Fix typo in docstring"

Or via Agent API:
    agent = QuickAgent("myproject")
    agent.fix("path/to/file.py", "Fix typo")
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from erirpg.registry import Registry
from erirpg.memory import git_head, in_git_repo


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE - Quick fix mode active flag
# ═══════════════════════════════════════════════════════════════════════════════

_QUICK_FIX_ACTIVE: bool = False
_QUICK_FIX_FILE: Optional[str] = None
_QUICK_FIX_PROJECT: Optional[str] = None


def is_quick_fix_active() -> bool:
    """Check if quick fix mode is active."""
    return _QUICK_FIX_ACTIVE


def get_quick_fix_file() -> Optional[str]:
    """Get the file being quick-fixed."""
    return _QUICK_FIX_FILE


def get_quick_fix_project() -> Optional[str]:
    """Get the project being quick-fixed."""
    return _QUICK_FIX_PROJECT


def _set_quick_fix_active(active: bool, file_path: Optional[str] = None, project: Optional[str] = None) -> None:
    """Set quick fix mode state (internal use only)."""
    global _QUICK_FIX_ACTIVE, _QUICK_FIX_FILE, _QUICK_FIX_PROJECT
    _QUICK_FIX_ACTIVE = active
    _QUICK_FIX_FILE = file_path if active else None
    _QUICK_FIX_PROJECT = project if active else None


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK FIX STATE FILE - For hook integration
# ═══════════════════════════════════════════════════════════════════════════════

def save_quick_fix_state(project_path: str, file_path: str, description: str) -> Path:
    """
    Save quick fix state to file for Claude Code hooks.

    The pretooluse hook checks this file to allow quick fix edits
    without requiring a full run.
    """
    state = {
        "quick_fix_active": True,
        "target_file": file_path,
        "description": description,
        "timestamp": datetime.now().isoformat(),
    }

    state_dir = Path(project_path) / ".eri-rpg"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_file = state_dir / "quick_fix_state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    return state_file


def clear_quick_fix_state(project_path: str) -> None:
    """Clear quick fix state file."""
    state_file = Path(project_path) / ".eri-rpg" / "quick_fix_state.json"
    if state_file.exists():
        state_file.unlink()


def load_quick_fix_state(project_path: str) -> Optional[Dict[str, Any]]:
    """Load quick fix state from file."""
    state_file = Path(project_path) / ".eri-rpg" / "quick_fix_state.json"
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK FIX FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def quick_fix(
    project: str,
    file_path: str,
    description: str,
    auto_commit: bool = True,
    dry_run: bool = False,
) -> Optional[str]:
    """
    Single-file edit without full spec ceremony.

    This is the lightweight alternative to Agent.from_goal() for simple fixes.
    No run state, no spec, no steps - just preflight, snapshot, edit, commit.

    Args:
        project: Project name (from registry)
        file_path: Path to the file (relative to project)
        description: Description of the fix (used for commit message)
        auto_commit: Whether to git commit after edit (default: True)
        dry_run: If True, only setup but don't actually allow edits

    Returns:
        Commit hash if successful and auto_commit=True, else "ok"

    Raises:
        ValueError: If project not found
        FileNotFoundError: If file doesn't exist

    Usage:
        # Start quick fix mode
        commit = quick_fix("myproject", "src/utils.py", "Fix off-by-one error")

        # Now Claude Code can edit the file
        # The hook will allow it because quick_fix_state.json exists

        # After edit is done, the file is auto-committed
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        raise ValueError(f"Project '{project}' not found. Add it with: eri-rpg add {project} <path>")

    project_path = proj.path

    # Normalize file path
    file_path = os.path.normpath(file_path)
    full_path = Path(project_path) / file_path

    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {full_path}")

    # Snapshot file before changes
    original_content = full_path.read_text()
    snapshot_path = _save_snapshot(project_path, file_path, original_content)

    # Set global state
    _set_quick_fix_active(True, file_path, project)

    # Save state file for hook integration
    save_quick_fix_state(project_path, file_path, description)

    if dry_run:
        print(f"Quick fix mode activated (dry run)")
        print(f"  Project: {project}")
        print(f"  File: {file_path}")
        print(f"  Description: {description}")
        print(f"  Snapshot: {snapshot_path}")
        return "dry_run"

    print(f"Quick fix mode activated")
    print(f"  File: {file_path}")
    print(f"  Edit the file, then run: eri-rpg quick-done {project}")

    return "ready"


def quick_done(
    project: str,
    auto_commit: bool = True,
    commit_message: Optional[str] = None,
) -> Optional[str]:
    """
    Complete a quick fix - commit changes and cleanup.

    Call this after making edits to finalize the quick fix.

    Args:
        project: Project name
        auto_commit: Whether to git commit (default: True)
        commit_message: Custom commit message (default: uses description from quick_fix)

    Returns:
        Commit hash if committed, else "ok"
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        raise ValueError(f"Project '{project}' not found")

    project_path = proj.path

    # Load quick fix state
    state = load_quick_fix_state(project_path)
    if not state or not state.get("quick_fix_active"):
        print("No active quick fix to complete")
        return None

    file_path = state.get("target_file")
    description = commit_message or state.get("description", "Quick fix")

    commit_hash = None

    # Git commit if enabled
    if auto_commit and in_git_repo(project_path):
        commit_hash = _git_commit(
            project_path,
            [file_path],
            f"[quick-fix] {description}"
        )
        if commit_hash:
            print(f"Committed: {commit_hash[:8]}")

    # Clear state
    _set_quick_fix_active(False)
    clear_quick_fix_state(project_path)

    print(f"Quick fix complete: {file_path}")

    return commit_hash or "ok"


def quick_cancel(project: str) -> None:
    """
    Cancel a quick fix and restore original file.

    Args:
        project: Project name
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        raise ValueError(f"Project '{project}' not found")

    project_path = proj.path

    # Load quick fix state
    state = load_quick_fix_state(project_path)
    if not state or not state.get("quick_fix_active"):
        print("No active quick fix to cancel")
        return

    file_path = state.get("target_file")

    # Restore from snapshot
    restored = _restore_snapshot(project_path, file_path)

    # Clear state
    _set_quick_fix_active(False)
    clear_quick_fix_state(project_path)

    if restored:
        print(f"Restored: {file_path}")
    else:
        print(f"No snapshot found for: {file_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK AGENT - Object-oriented interface
# ═══════════════════════════════════════════════════════════════════════════════

class QuickAgent:
    """
    Lightweight agent for quick fixes.

    Alternative to the full Agent when you just need to make
    a simple, single-file change.

    Usage:
        agent = QuickAgent("myproject")
        agent.fix("src/utils.py", "Fix typo")
        # Make edits...
        commit = agent.done()
    """

    def __init__(self, project: str):
        """
        Initialize quick agent for a project.

        Args:
            project: Project name from registry
        """
        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            raise ValueError(f"Project '{project}' not found")

        self.project = project
        self.project_path = proj.path
        self._active_file: Optional[str] = None
        self._description: Optional[str] = None
        self._snapshot: Optional[str] = None

    def fix(self, file_path: str, description: str) -> "QuickAgent":
        """
        Start a quick fix on a file.

        Args:
            file_path: Path to file (relative to project)
            description: What you're fixing

        Returns:
            self (for chaining)
        """
        # Normalize path
        file_path = os.path.normpath(file_path)
        full_path = Path(self.project_path) / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")

        # Snapshot
        self._snapshot = full_path.read_text()
        _save_snapshot(self.project_path, file_path, self._snapshot)

        # Set state
        self._active_file = file_path
        self._description = description

        # Global state and file for hooks
        _set_quick_fix_active(True, file_path, self.project)
        save_quick_fix_state(self.project_path, file_path, description)

        return self

    def done(self, auto_commit: bool = True) -> Optional[str]:
        """
        Complete the quick fix.

        Args:
            auto_commit: Whether to git commit

        Returns:
            Commit hash or "ok"
        """
        if not self._active_file:
            raise RuntimeError("No active quick fix. Call fix() first.")

        commit_hash = None

        if auto_commit and in_git_repo(self.project_path):
            commit_hash = _git_commit(
                self.project_path,
                [self._active_file],
                f"[quick-fix] {self._description}"
            )

        # Cleanup
        _set_quick_fix_active(False)
        clear_quick_fix_state(self.project_path)

        self._active_file = None
        self._description = None
        self._snapshot = None

        return commit_hash or "ok"

    def cancel(self) -> None:
        """Cancel and restore original file."""
        if not self._active_file:
            return

        _restore_snapshot(self.project_path, self._active_file)

        _set_quick_fix_active(False)
        clear_quick_fix_state(self.project_path)

        self._active_file = None
        self._description = None
        self._snapshot = None

    @property
    def is_active(self) -> bool:
        """Check if a quick fix is in progress."""
        return self._active_file is not None


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _save_snapshot(project_path: str, file_path: str, content: str) -> Path:
    """Save file snapshot for potential rollback."""
    snapshot_dir = Path(project_path) / ".eri-rpg" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Use file path hash for unique name
    import hashlib
    path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:12]
    snapshot_file = snapshot_dir / f"{path_hash}.snapshot"

    # Save with metadata
    snapshot_data = {
        "file_path": file_path,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }

    with open(snapshot_file, "w") as f:
        json.dump(snapshot_data, f)

    return snapshot_file


def _restore_snapshot(project_path: str, file_path: str) -> bool:
    """Restore file from snapshot."""
    import hashlib

    snapshot_dir = Path(project_path) / ".eri-rpg" / "snapshots"
    path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:12]
    snapshot_file = snapshot_dir / f"{path_hash}.snapshot"

    if not snapshot_file.exists():
        return False

    try:
        with open(snapshot_file) as f:
            data = json.load(f)

        content = data.get("content", "")
        full_path = Path(project_path) / file_path
        full_path.write_text(content)

        # Remove snapshot after restore
        snapshot_file.unlink()

        return True
    except Exception:
        return False


def _git_commit(project_path: str, files: List[str], message: str) -> Optional[str]:
    """Create git commit for files."""
    try:
        # Stage files
        full_paths = [str(Path(project_path) / f) for f in files]
        subprocess.run(
            ['git', 'add'] + full_paths,
            check=True,
            capture_output=True,
            cwd=project_path,
        )

        # Commit
        subprocess.run(
            ['git', 'commit', '-m', message],
            check=True,
            capture_output=True,
            cwd=project_path,
        )

        # Get commit hash
        return git_head()
    except subprocess.CalledProcessError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Functions
    "quick_fix",
    "quick_done",
    "quick_cancel",
    # State checks
    "is_quick_fix_active",
    "get_quick_fix_file",
    "get_quick_fix_project",
    "load_quick_fix_state",
    # Class
    "QuickAgent",
]
