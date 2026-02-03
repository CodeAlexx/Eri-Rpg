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

    Uses target_project (set by explicit switch) NOT active_edited_project.
    This ensures editing eri-rpg code doesn't lose track of the real project.

    Returns:
        (project_name, project_path, is_meta_mode) or (None, None, False)

    is_meta_mode is True when cwd is eri-rpg but target is different project.
    """
    state_file = Path.home() / ".eri-rpg" / "state.json"
    registry_file = Path.home() / ".eri-rpg" / "registry.json"

    if not state_file.exists():
        return None, None, False

    try:
        with open(state_file) as f:
            state = json.load(f)

        # Prefer target_project (explicit switch) over active_project (legacy)
        target_project = state.get("target_project") or state.get("active_project")
        target_path = state.get("target_project_path") or state.get("active_project_path")

        if not target_project:
            return None, None, False

        # If we have path directly, use it
        if target_path and Path(target_path).exists():
            # Check if we're in meta mode (cwd is eri-rpg but target is different)
            cwd = str(Path.cwd())
            is_meta = "eri-rpg" in cwd and target_path != cwd
            return target_project, target_path, is_meta

        # Otherwise look up in registry
        if not registry_file.exists():
            return None, None, False

        with open(registry_file) as f:
            registry = json.load(f)

        project_info = registry.get("projects", {}).get(target_project)
        if not project_info:
            return None, None, False

        path = project_info.get("path")
        cwd = str(Path.cwd())
        is_meta = "eri-rpg" in cwd and path != cwd

        return target_project, path, is_meta
    except Exception:
        return None, None, False


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


def ensure_state_md(project_path: str) -> Optional[str]:
    """Create STATE.md if .planning/ exists but STATE.md doesn't.

    Returns path to STATE.md if created/exists, None otherwise.
    """
    project = Path(project_path)
    planning_base = find_planning_directory(project_path)

    if not planning_base:
        return None

    planning = Path(planning_base) / ".planning"
    state_path = planning / "STATE.md"

    if state_path.exists():
        return str(state_path)

    # Planning dir exists but no STATE.md - create one by scanning phases
    phases_dir = planning / "phases"
    roadmap_path = planning / "ROADMAP.md"

    # Scan for phase info
    phases_status = []
    current_phase = None

    if phases_dir.exists():
        import re
        # Get phase names from ROADMAP.md
        phase_names = {}
        if roadmap_path.exists():
            content = roadmap_path.read_text()
            for match in re.finditer(r'###?\s*Phase\s*(\d+)[:\-\s]+([^\n]+)', content):
                phase_names[int(match.group(1))] = match.group(2).strip()

        for d in sorted(phases_dir.iterdir()):
            if not d.is_dir():
                continue
            parts = d.name.split("-", 1)
            if not parts[0].isdigit():
                continue

            phase_num = int(parts[0])
            phase_name = phase_names.get(phase_num, parts[1] if len(parts) > 1 else f"Phase {phase_num}")

            plans = list(d.glob("*-PLAN.md"))
            summaries = list(d.glob("*-SUMMARY.md")) + list(d.glob("SUMMARY-*.md"))

            if len(summaries) >= len(plans) and plans:
                status = "completed"
            elif summaries:
                status = "in_progress"
            elif plans:
                status = "planned"
            else:
                status = "pending"

            phases_status.append((phase_num, phase_name, status))

            if current_phase is None and status != "completed":
                current_phase = phase_num

    # Generate STATE.md
    project_name = project.name
    lines = [
        "# Current State",
        "",
        "## Project",
        f"**Name:** {project_name}",
        f"**Path:** {project}",
        "",
        "## Current Phase",
    ]

    if current_phase:
        name = next((n for num, n, s in phases_status if num == current_phase), f"Phase {current_phase}")
        lines.append(f"Phase {current_phase}: {name}")
    elif phases_status:
        lines.append("All phases completed")
    else:
        lines.append("No phases defined yet")

    lines.extend(["", "## Phase Status", "| Phase | Name | Status |", "|-------|------|--------|"])
    for num, name, status in phases_status:
        lines.append(f"| {num} | {name} | {status} |")

    lines.extend([
        "",
        "## Last Action",
        "- STATE.md auto-generated from project scan",
        "",
        "## Updated",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "",
    ])

    state_path.write_text("\n".join(lines))
    return str(state_path)


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

    # Get active project from global state (uses target_project, not active_edited)
    active_name, active_path, is_meta_mode = get_active_project_info()

    if active_name and active_path and Path(active_path).exists():
        result["active_project"] = {
            "name": active_name,
            "path": active_path,
            "is_cwd": str(Path.cwd()) == active_path,
        }

        # Flag meta mode (working on eri-rpg but target is different project)
        if is_meta_mode:
            result["is_meta_mode"] = True
            result["meta_note"] = (
                f"You're in eri-rpg directory but target project is '{active_name}' at {active_path}. "
                f"Read context from {active_name}, not eri-rpg."
            )

        # Ensure STATE.md exists (create if .planning/ exists but STATE.md doesn't)
        state_created = ensure_state_md(active_path)
        if state_created:
            result["state_md_ensured"] = state_created

        # Get context files from active project
        result["context"] = get_context_files(active_path)

        # Check if cwd is different from active project
        if str(Path.cwd()) != active_path:
            result["note"] = f"Target project '{active_name}' is at {active_path}, not cwd"
            result["cwd_context"] = get_cwd_context()

        result["status"] = "active_project_found"

    else:
        # No active project - fall back to cwd
        result["active_project"] = None

        # Ensure STATE.md exists for cwd if it has .planning/
        cwd = str(Path.cwd())
        state_created = ensure_state_md(cwd)
        if state_created:
            result["state_md_ensured"] = state_created

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
