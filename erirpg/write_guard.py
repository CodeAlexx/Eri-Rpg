"""
Hard enforcement hooks for EriRPG.

Intercepts Python's builtin open() to block unauthorized file writes.
No prompts. No suggestions. Hard enforcement.

When EriRPG is imported, these hooks are automatically installed.
Any attempt to write files without going through EriRPG will be blocked.
"""

import builtins
import os
from typing import List, Optional

# Store the original open function
_original_open = builtins.open

# State for write protection
_PROTECTED_PATHS: List[str] = []  # Set by agent.preflight()
_WRITE_ALLOWED: bool = False
_HOOKS_INSTALLED: bool = False
_WRITE_PROJECT_PATH: Optional[str] = None  # Track project for boundary checks

# Paths that should never be protected (temp files, etc.)
_ALWAYS_ALLOWED_PATTERNS = (
    '/tmp/',
    '/var/tmp/',
    '.pyc',
    '__pycache__',
    '.git/',
    '.pytest_cache/',
    '.eri-rpg/',  # EriRPG's own data
)


def guarded_open(file, mode='r', *args, **kwargs):
    """
    Intercept file opens and block unauthorized writes.

    This is the hard enforcement mechanism. If you try to write
    any file without an active EriRPG run + preflight, you get
    a RuntimeError. No exceptions.
    """
    # Only intercept write modes
    if 'w' in mode or 'a' in mode or '+' in mode:
        # Get absolute path for comparison
        try:
            abs_path = os.path.realpath(str(file))
        except Exception as e:  # Path resolution fallback
            abs_path = str(file)

        # Check if path is always allowed (temp files, git, etc.)
        if not any(pattern in abs_path for pattern in _ALWAYS_ALLOWED_PATTERNS):
            # ENFORCEMENT: Must have writes enabled
            if not _WRITE_ALLOWED:
                raise RuntimeError(
                    f"╔══════════════════════════════════════════════════════╗\n"
                    f"║  ERI-RPG WRITE BLOCKED                               ║\n"
                    f"╠══════════════════════════════════════════════════════╣\n"
                    f"║  Cannot write to: {os.path.basename(abs_path):<35} ║\n"
                    f"║                                                      ║\n"
                    f"║  No active EriRPG run or preflight not done.        ║\n"
                    f"║                                                      ║\n"
                    f"║  To fix:                                             ║\n"
                    f"║    agent = Agent.from_goal('task', project='name')   ║\n"
                    f"║    agent.preflight(files, operation)                 ║\n"
                    f"║    agent.edit_file() or agent.write_file()           ║\n"
                    f"╚══════════════════════════════════════════════════════╝"
                )

            # ENFORCEMENT: File must be in preflight list
            if _PROTECTED_PATHS and abs_path not in _PROTECTED_PATHS:
                raise RuntimeError(
                    f"╔══════════════════════════════════════════════════════╗\n"
                    f"║  ERI-RPG WRITE BLOCKED                               ║\n"
                    f"╠══════════════════════════════════════════════════════╣\n"
                    f"║  File not in preflight: {os.path.basename(abs_path):<28} ║\n"
                    f"║                                                      ║\n"
                    f"║  This file was not included in preflight().          ║\n"
                    f"║                                                      ║\n"
                    f"║  To fix:                                             ║\n"
                    f"║    Re-run preflight with all files you intend to     ║\n"
                    f"║    modify, including this one.                       ║\n"
                    f"╚══════════════════════════════════════════════════════╝"
                )

            # CRITICAL: Boundary enforcement - block ANY path outside project
            if _WRITE_PROJECT_PATH:
                project_abs = os.path.realpath(_WRITE_PROJECT_PATH)
                if not abs_path.startswith(project_abs + os.sep) and abs_path != project_abs:
                    raise RuntimeError(
                        f"╔══════════════════════════════════════════════════════╗\n"
                        f"║  ERI-RPG BOUNDARY VIOLATION                          ║\n"
                        f"╠══════════════════════════════════════════════════════╣\n"
                        f"║  Path escapes project directory!                     ║\n"
                        f"║                                                      ║\n"
                        f"║  Attempted: {os.path.basename(abs_path):<40} ║\n"
                        f"║  Project:   {os.path.basename(project_abs):<40} ║\n"
                        f"║                                                      ║\n"
                        f"║  EriRPG REFUSES to write files outside the project.  ║\n"
                        f"║  This is a security feature to prevent accidents.    ║\n"
                        f"╚══════════════════════════════════════════════════════╝"
                    )

    # Allow the operation
    return _original_open(file, mode, *args, **kwargs)


def install_hooks() -> None:
    """
    Install write protection hooks.

    Called automatically when erirpg is imported.
    """
    global _HOOKS_INSTALLED

    if _HOOKS_INSTALLED:
        return  # Already installed

    builtins.open = guarded_open
    _HOOKS_INSTALLED = True


def uninstall_hooks() -> None:
    """
    Uninstall write protection hooks.

    For testing or if you really need to bypass protection.
    """
    global _HOOKS_INSTALLED

    builtins.open = _original_open
    _HOOKS_INSTALLED = False


def enable_writes(paths: List[str], project_path: Optional[str] = None) -> None:
    """
    Enable writes for specific paths.

    Called by Agent.preflight() when preflight passes.

    Args:
        paths: List of file paths (relative or absolute)
        project_path: Project root for resolving relative paths

    Raises:
        RuntimeError: If any path is outside the project directory (boundary violation)
    """
    global _WRITE_ALLOWED, _PROTECTED_PATHS, _WRITE_PROJECT_PATH

    # Store project path for boundary checks in guarded_open
    _WRITE_PROJECT_PATH = project_path

    # Convert all paths to absolute
    resolved_paths = []
    project_abs = os.path.realpath(project_path) if project_path else None

    for p in paths:
        if os.path.isabs(p):
            abs_path = os.path.realpath(p)
        elif project_path:
            abs_path = os.path.realpath(os.path.join(project_path, p))
        else:
            abs_path = os.path.realpath(p)

        # CRITICAL: Hard boundary enforcement - block ANY path outside project
        if project_abs:
            if not abs_path.startswith(project_abs + os.sep) and abs_path != project_abs:
                raise RuntimeError(
                    f"╔══════════════════════════════════════════════════════╗\n"
                    f"║  ERI-RPG BOUNDARY VIOLATION                          ║\n"
                    f"╠══════════════════════════════════════════════════════╣\n"
                    f"║  Path escapes project directory!                     ║\n"
                    f"║                                                      ║\n"
                    f"║  Attempted: {abs_path:<40} ║\n"
                    f"║  Project:   {project_abs:<40} ║\n"
                    f"║                                                      ║\n"
                    f"║  EriRPG REFUSES to whitelist files outside project.  ║\n"
                    f"║  This is a security feature to prevent accidents.    ║\n"
                    f"╚══════════════════════════════════════════════════════╝"
                )

        resolved_paths.append(abs_path)

    _WRITE_ALLOWED = True
    _PROTECTED_PATHS = resolved_paths


def disable_writes() -> None:
    """
    Disable writes.

    Called when a run completes or is abandoned.
    """
    global _WRITE_ALLOWED, _PROTECTED_PATHS, _WRITE_PROJECT_PATH

    _WRITE_ALLOWED = False
    _PROTECTED_PATHS = []
    _WRITE_PROJECT_PATH = None


def is_write_allowed() -> bool:
    """Check if writes are currently allowed."""
    return _WRITE_ALLOWED


def get_allowed_paths() -> List[str]:
    """Get list of paths that are allowed to be written."""
    return _PROTECTED_PATHS.copy()


def add_allowed_path(path: str, project_path: Optional[str] = None) -> None:
    """
    Add a path to the allowed list.

    Use this if you discover you need to modify an additional file
    during a run. You'll need to re-run preflight for full tracking.

    Raises:
        RuntimeError: If path is outside the project directory (boundary violation)
    """
    global _PROTECTED_PATHS

    if os.path.isabs(path):
        abs_path = os.path.realpath(path)
    elif project_path:
        abs_path = os.path.realpath(os.path.join(project_path, path))
    else:
        abs_path = os.path.realpath(path)

    # CRITICAL: Boundary enforcement - use stored project path or provided one
    check_project = project_path or _WRITE_PROJECT_PATH
    if check_project:
        project_abs = os.path.realpath(check_project)
        if not abs_path.startswith(project_abs + os.sep) and abs_path != project_abs:
            raise RuntimeError(
                f"╔══════════════════════════════════════════════════════╗\n"
                f"║  ERI-RPG BOUNDARY VIOLATION                          ║\n"
                f"╠══════════════════════════════════════════════════════╣\n"
                f"║  Path escapes project directory!                     ║\n"
                f"║                                                      ║\n"
                f"║  Attempted: {abs_path:<40} ║\n"
                f"║  Project:   {project_abs:<40} ║\n"
                f"║                                                      ║\n"
                f"║  EriRPG REFUSES to allow files outside project.      ║\n"
                f"╚══════════════════════════════════════════════════════╝"
            )

    if abs_path not in _PROTECTED_PATHS:
        _PROTECTED_PATHS.append(abs_path)
