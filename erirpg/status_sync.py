"""
Central status file synchronization with auto-commit.

This module provides a single entry point for regenerating status files
(STATUS.md, ROADMAP.md, TASKS.md) after any state change, then automatically
committing those changes.

Design: Never fail on status update - this is a best-effort operation
that should not interrupt the primary workflow.
"""

import subprocess
from pathlib import Path
from typing import Optional


def sync_status_files(project_path: str, project_name: Optional[str] = None, auto_commit: bool = True) -> bool:
    """Regenerate all status files after a state change and auto-commit.

    This is the central function that should be called after ANY state change
    that affects session data, decisions, blockers, actions, or run state.

    Args:
        project_path: Path to the project directory
        project_name: Project name (auto-detected if not provided)
        auto_commit: Whether to automatically commit status file changes (default: True)

    Returns:
        True if sync succeeded, False otherwise (never raises)
    """
    try:
        # Auto-detect project name if not provided
        if not project_name:
            project_name = _get_project_name(project_path)
            if not project_name:
                return False

        # Import here to avoid circular imports
        from erirpg.generators.status_md import regenerate_status

        regenerate_status(project_name, project_path)

        # Auto-commit the status file changes
        if auto_commit:
            _auto_commit_status(project_path)

        return True

    except Exception:
        # Never fail on status update - this is a best-effort operation
        return False


def _auto_commit_status(project_path: str) -> bool:
    """Automatically commit status file changes.

    Only commits .eri-rpg/*.md files to avoid committing unrelated changes.

    Returns:
        True if commit succeeded or nothing to commit, False on error
    """
    try:
        eri_dir = Path(project_path) / ".eri-rpg"
        if not eri_dir.exists():
            return False

        # Find status files that exist
        status_files = []
        for md_file in ["STATUS.md", "ROADMAP.md", "TASKS.md"]:
            if (eri_dir / md_file).exists():
                status_files.append(f".eri-rpg/{md_file}")

        if not status_files:
            return True  # Nothing to commit

        # Stage only status files
        subprocess.run(
            ["git", "add"] + status_files,
            cwd=project_path,
            capture_output=True,
            timeout=10,
        )

        # Check if there's anything staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=project_path,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True  # Nothing to commit

        # Commit with auto-generated message
        subprocess.run(
            ["git", "commit", "-m", "chore: auto-update status files"],
            cwd=project_path,
            capture_output=True,
            timeout=30,
        )

        return True

    except Exception:
        return False  # Never fail


def _get_project_name(project_path: str) -> Optional[str]:
    """Get project name from path.

    Tries multiple methods:
    1. Registry lookup by path
    2. Active project from state
    3. Directory name as fallback
    """
    try:
        # Try registry first
        from erirpg.registry import Registry
        registry = Registry.get_instance()
        for project in registry.list():
            if project.path == project_path:
                return project.name

        # Try active project from state
        from erirpg.state import State
        state = State.load()
        if state.active_project:
            project = registry.get(state.active_project)
            if project and project.path == project_path:
                return state.active_project

        # Fallback to directory name
        return Path(project_path).name

    except Exception:
        # Absolute fallback
        return Path(project_path).name


def sync_from_session(session_id: str, db_path: Optional[str] = None) -> bool:
    """Regenerate status files using session ID to lookup project info.

    Useful when we have a session ID but not the project path directly.

    Args:
        session_id: The session ID to lookup
        db_path: Optional database path

    Returns:
        True if sync succeeded, False otherwise (never raises)
    """
    try:
        from erirpg import storage
        from erirpg.registry import Registry

        session = storage.get_session(session_id, db_path)
        if not session:
            return False

        project_name = session.project_name

        # Get project path from registry
        registry = Registry.get_instance()
        project = registry.get(project_name)
        if not project:
            return False

        return sync_status_files(project.path, project_name)

    except Exception:
        return False
