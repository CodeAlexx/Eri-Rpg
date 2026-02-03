#!/usr/bin/env python3
"""
/coder:init CLI - Session context recovery.

Returns active project info and paths to context files.
The slash command uses this to know which project to load,
regardless of current working directory.

Usage:
    python -m erirpg.commands.coder_init [--json]
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


def get_active_project_info() -> tuple:
    """Get active project name and path from global state.

    Returns:
        (project_name, project_path) or (None, None) if not found
    """
    state_file = Path.home() / ".eri-rpg" / "state.json"
    registry_file = Path.home() / ".eri-rpg" / "registry.json"

    if not state_file.exists() or not registry_file.exists():
        return None, None

    try:
        with open(state_file) as f:
            state = json.load(f)
        with open(registry_file) as f:
            registry = json.load(f)

        active_project = state.get("active_project")
        if not active_project:
            return None, None

        project_info = registry.get("projects", {}).get(active_project)
        if not project_info:
            return None, None

        return active_project, project_info.get("path")
    except Exception:
        return None, None


def find_planning_directory(project_path: str) -> Optional[str]:
    """Find where .planning/ lives under the project path."""
    project = Path(project_path)

    # Check direct location first
    if (project / ".planning").exists():
        return str(project)

    # Check common subdirectories
    for subdir in ["desktop", "src", "app", "packages", "apps"]:
        subpath = project / subdir
        if subpath.exists() and (subpath / ".planning").exists():
            return str(subpath)

    return None


def get_context_files(project_path: str) -> Dict[str, Any]:
    """Get all context files for a project."""
    project = Path(project_path)
    planning_base = find_planning_directory(project_path)

    context = {
        "files": {},
        "missing": [],
    }

    # Define files to check with their purposes
    files_to_check = [
        # Project-level
        ("CLAUDE.md", project / "CLAUDE.md", "Project instructions"),
        ("EMPOWERMENT.md", project / "EMPOWERMENT.md", "Empowerment guidelines"),

        # Planning files (if planning dir exists)
    ]

    if planning_base:
        planning = Path(planning_base) / ".planning"
        files_to_check.extend([
            ("STATE.md", planning / "STATE.md", "Current state and progress"),
            ("status.md", planning / "status.md", "Status summary"),
            ("PROJECT.md", planning / "PROJECT.md", "Project definition"),
            ("ROADMAP.md", planning / "ROADMAP.md", "Phase roadmap"),
            ("RESUME.md", planning / "RESUME.md", "Resume point from pause"),
        ])

    # EriRPG session file
    eri_session = project / ".eri-rpg" / "session.json"
    files_to_check.append(("session.json", eri_session, "EriRPG session state"))

    for name, path, purpose in files_to_check:
        if path.exists():
            context["files"][name] = {
                "path": str(path),
                "purpose": purpose,
                "exists": True,
            }
        else:
            context["missing"].append({
                "name": name,
                "expected_path": str(path),
                "purpose": purpose,
            })

    return context


def get_cwd_context() -> Dict[str, Any]:
    """Get context for current working directory (fallback)."""
    cwd = Path.cwd()

    context = {
        "files": {},
        "missing": [],
    }

    # Check for planning files in cwd
    planning = cwd / ".planning"
    files_to_check = [
        ("CLAUDE.md", cwd / "CLAUDE.md"),
        ("STATE.md", planning / "STATE.md"),
        ("status.md", planning / "status.md"),
    ]

    for name, path in files_to_check:
        if path.exists():
            context["files"][name] = {
                "path": str(path),
                "exists": True,
            }

    return context


def coder_init(output_json: bool = False) -> dict:
    """Get session context for /coder:init."""
    result = {
        "command": "coder-init",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cwd": str(Path.cwd()),
    }

    # Get active project from global state
    active_name, active_path = get_active_project_info()

    if active_name and active_path and Path(active_path).exists():
        result["active_project"] = {
            "name": active_name,
            "path": active_path,
            "is_cwd": str(Path.cwd()) == active_path,
        }

        # Get context files from active project
        result["context"] = get_context_files(active_path)

        # Check if cwd is different from active project
        if str(Path.cwd()) != active_path:
            result["note"] = f"Active project '{active_name}' is at {active_path}, not cwd"
            result["cwd_context"] = get_cwd_context()

        result["status"] = "active_project_found"

    else:
        # No active project - fall back to cwd
        result["active_project"] = None
        result["context"] = get_cwd_context()
        result["status"] = "no_active_project"
        result["note"] = "No active project. Using current directory."

    # Build instructions for Claude
    if result.get("context", {}).get("files"):
        files_to_read = [f["path"] for f in result["context"]["files"].values()]
        result["instructions"] = {
            "action": "read_files",
            "files": files_to_read,
            "then": "Present recovered context to user",
        }
    else:
        result["instructions"] = {
            "action": "inform_user",
            "message": "No session context found",
        }

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    coder_init(output_json=output_json)


if __name__ == "__main__":
    main()
