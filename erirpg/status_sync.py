"""
Central status file synchronization.

This module provides a single entry point for regenerating status files
(STATUS.md, ROADMAP.md, TASKS.md) after any state change. All state-changing
functions should call sync_status_files() after committing their changes.

Design: Never fail on status update - this is a best-effort operation
that should not interrupt the primary workflow.
"""

from pathlib import Path
from typing import Optional


def sync_status_files(project_path: str, project_name: Optional[str] = None) -> bool:
    """Regenerate all status files after a state change.

    This is the central function that should be called after ANY state change
    that affects session data, decisions, blockers, actions, or run state.

    Args:
        project_path: Path to the project directory
        project_name: Project name (auto-detected if not provided)

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
        return True

    except Exception:
        # Never fail on status update - this is a best-effort operation
        return False


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
