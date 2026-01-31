"""
State management for coder workflow.

Commands:
- resume: Restore from last session
- progress: Show current position
- settings: View/modify configuration
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import (
    get_planning_dir,
    load_config,
    save_config,
    get_default_config,
    load_state,
    load_roadmap,
    timestamp,
)


def find_resume_state(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Find resume state from various sources.

    Checks in order:
    1. .planning/RESUME.md (from /coder:pause)
    2. .planning/STATE.md (session continuity section)
    3. .planning/phases/*/CHECKPOINT.md (in-progress checkpoints)

    Returns:
        Dict with resume info or empty dict if no resume state
    """
    planning_dir = get_planning_dir(project_path)

    # Check RESUME.md
    resume_path = planning_dir / "RESUME.md"
    if resume_path.exists():
        content = resume_path.read_text()
        return _parse_resume_md(content, resume_path)

    # Check STATE.md for session continuity
    state_path = planning_dir / "STATE.md"
    if state_path.exists():
        content = state_path.read_text()
        session_info = _parse_session_continuity(content)
        if session_info.get("resume_file") or session_info.get("pending_checkpoint"):
            return session_info

    # Check for checkpoint files
    phases_dir = planning_dir / "phases"
    if phases_dir.exists():
        for phase_dir in sorted(phases_dir.iterdir()):
            checkpoint_path = phase_dir / "CHECKPOINT.md"
            if checkpoint_path.exists():
                return _parse_checkpoint(checkpoint_path)

    return {}


def _parse_resume_md(content: str, path: Path) -> Dict[str, Any]:
    """Parse RESUME.md file."""
    result = {
        "source": "RESUME.md",
        "path": str(path),
        "type": "pause",
    }

    # Parse YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                fm = yaml.safe_load(parts[1]) or {}
                result.update(fm)
            except:
                pass

    return result


def _parse_session_continuity(content: str) -> Dict[str, Any]:
    """Parse session continuity section from STATE.md."""
    result = {}

    in_session = False
    for line in content.split("\n"):
        if "## Session Continuity" in line:
            in_session = True
            continue
        if in_session:
            if line.startswith("##"):
                break
            if "Last session:" in line:
                result["last_session"] = line.split(":", 1)[1].strip()
            elif "Stopped at:" in line:
                result["stopped_at"] = line.split(":", 1)[1].strip()
            elif "Resume file:" in line:
                value = line.split(":", 1)[1].strip()
                if value.lower() not in ("none", ""):
                    result["resume_file"] = value
            elif "Pending checkpoint:" in line:
                value = line.split(":", 1)[1].strip()
                if value.lower() not in ("none", ""):
                    result["pending_checkpoint"] = value

    if result:
        result["source"] = "STATE.md"
        result["type"] = "session"

    return result


def _parse_checkpoint(path: Path) -> Dict[str, Any]:
    """Parse CHECKPOINT.md file."""
    content = path.read_text()
    result = {
        "source": "CHECKPOINT.md",
        "path": str(path),
        "type": "checkpoint",
    }

    # Extract phase from path
    phase_dir = path.parent.name
    if phase_dir.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
        result["phase"] = int(phase_dir.split("-")[0])

    # Parse frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                fm = yaml.safe_load(parts[1]) or {}
                result.update(fm)
            except:
                pass

    return result


def clear_resume_state(project_path: Optional[Path] = None) -> None:
    """Clear resume state after successful resume."""
    planning_dir = get_planning_dir(project_path)
    resume_path = planning_dir / "RESUME.md"
    if resume_path.exists():
        resume_path.unlink()


def get_progress(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate project progress metrics.

    Returns:
        Dict with progress metrics including:
        - phase_progress: current/total phases
        - plan_progress: current/total plans in phase
        - requirement_progress: completed/total requirements
        - status: current workflow status
        - next_action: recommended next command
    """
    planning_dir = get_planning_dir(project_path)
    roadmap = load_roadmap(project_path)
    state = load_state(project_path)
    config = load_config(project_path)

    phases = roadmap.get("phases", [])
    total_phases = len(phases)
    completed_phases = sum(1 for p in phases if p.get("status") == "complete")
    current_phase = next(
        (p for p in phases if p.get("status") in ("in-progress", "ready", "pending")),
        None
    )

    # Count plans in current phase
    plan_progress = {"current": 0, "total": 0}
    if current_phase:
        phase_num = current_phase.get("number", 1)
        phase_dir = _find_phase_dir(planning_dir, phase_num)
        if phase_dir and phase_dir.exists():
            plan_files = list(phase_dir.glob("*-PLAN.md"))
            summary_files = list(phase_dir.glob("*-SUMMARY.md"))
            plan_progress["total"] = len(plan_files)
            plan_progress["current"] = len(summary_files)

    # Count requirements
    req_progress = _count_requirements(planning_dir)

    # Determine status
    status = _determine_status(state, current_phase, plan_progress)

    # Determine next action
    next_action = _determine_next_action(
        status, current_phase, plan_progress, completed_phases, total_phases
    )

    return {
        "project_name": state.get("project_name", Path.cwd().name),
        "status": status,
        "phase_progress": {
            "current": current_phase.get("number", 0) if current_phase else 0,
            "total": total_phases,
            "completed": completed_phases,
            "percent": int((completed_phases / total_phases * 100)) if total_phases else 0,
        },
        "plan_progress": plan_progress,
        "requirement_progress": req_progress,
        "current_phase": current_phase,
        "next_action": next_action,
        "config": config,
    }


def _find_phase_dir(planning_dir: Path, phase_num: int) -> Optional[Path]:
    """Find phase directory by number."""
    phases_dir = planning_dir / "phases"
    if not phases_dir.exists():
        return None

    for d in phases_dir.iterdir():
        if d.is_dir() and d.name.startswith(f"{phase_num:02d}-"):
            return d

    return None


def _count_requirements(planning_dir: Path) -> Dict[str, Any]:
    """Count requirements from REQUIREMENTS.md."""
    req_path = planning_dir / "REQUIREMENTS.md"
    if not req_path.exists():
        return {"total": 0, "completed": 0, "percent": 0}

    content = req_path.read_text()
    total = 0
    completed = 0

    for line in content.split("\n"):
        if line.strip().startswith("- ["):
            total += 1
            if line.strip().startswith("- [x]") or line.strip().startswith("- [X]"):
                completed += 1

    return {
        "total": total,
        "completed": completed,
        "percent": int((completed / total * 100)) if total else 0,
    }


def _determine_status(
    state: Dict, current_phase: Optional[Dict], plan_progress: Dict
) -> str:
    """Determine current workflow status."""
    if state.get("paused"):
        return "paused"
    if state.get("blocked"):
        return "blocked"
    if not current_phase:
        return "idle"
    if plan_progress["total"] == 0:
        return "ready_to_plan"
    if plan_progress["current"] < plan_progress["total"]:
        return "executing"
    if plan_progress["current"] == plan_progress["total"]:
        return "ready_to_verify"
    return "idle"


def _determine_next_action(
    status: str,
    current_phase: Optional[Dict],
    plan_progress: Dict,
    completed: int,
    total: int,
) -> Dict[str, str]:
    """Determine recommended next action."""
    phase_num = current_phase.get("number", 1) if current_phase else 1

    actions = {
        "paused": {
            "command": "/coder:resume",
            "description": "Resume from where you left off",
        },
        "blocked": {
            "command": "Address blocker",
            "description": "Review STATE.md for blocker details",
        },
        "idle": {
            "command": f"/coder:plan-phase {phase_num}",
            "description": f"Start planning phase {phase_num}",
        },
        "ready_to_plan": {
            "command": f"/coder:plan-phase {phase_num}",
            "description": f"Create execution plans for phase {phase_num}",
        },
        "executing": {
            "command": f"/coder:execute-phase {phase_num}",
            "description": f"Continue executing phase {phase_num}",
        },
        "ready_to_verify": {
            "command": f"/coder:verify-work {phase_num}",
            "description": f"Verify phase {phase_num} is complete",
        },
    }

    if completed == total and total > 0:
        return {
            "command": "/coder:complete-milestone",
            "description": "All phases complete, finalize milestone",
        }

    return actions.get(status, actions["idle"])


def format_progress_bar(percent: int, width: int = 10) -> str:
    """Format a progress bar.

    Args:
        percent: Progress percentage (0-100)
        width: Bar width in characters

    Returns:
        Progress bar string like [████████░░]
    """
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def get_settings(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get current settings with defaults applied."""
    config = load_config(project_path)
    defaults = get_default_config()

    # Merge with defaults
    result = defaults.copy()
    result.update(config)

    # Ensure nested dicts are merged
    if "workflow" in config:
        result["workflow"] = {**defaults["workflow"], **config["workflow"]}
    if "notifications" in config:
        result["notifications"] = {**defaults.get("notifications", {}), **config["notifications"]}

    return result


def update_setting(
    key: str, value: Any, project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Update a single setting.

    Args:
        key: Setting key (e.g., "mode", "depth", "workflow.research")
        value: New value
        project_path: Project path

    Returns:
        Updated config dict
    """
    config = load_config(project_path)

    # Handle nested keys
    if "." in key:
        parts = key.split(".")
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    else:
        config[key] = value

    save_config(config, project_path)
    return config


def reset_settings(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Reset settings to defaults."""
    config = get_default_config()
    save_config(config, project_path)
    return config


def validate_setting(key: str, value: Any) -> Optional[str]:
    """Validate a setting value.

    Returns:
        Error message if invalid, None if valid
    """
    validators = {
        "mode": lambda v: v in ("yolo", "interactive"),
        "depth": lambda v: v in ("quick", "standard", "comprehensive"),
        "parallelization": lambda v: isinstance(v, bool),
        "commit_tracking": lambda v: isinstance(v, bool),
        "model_profile": lambda v: v in ("quality", "balanced", "budget"),
        "workflow.research": lambda v: isinstance(v, bool),
        "workflow.plan_check": lambda v: isinstance(v, bool),
        "workflow.verifier": lambda v: isinstance(v, bool),
    }

    if key in validators:
        if not validators[key](value):
            allowed = {
                "mode": "yolo, interactive",
                "depth": "quick, standard, comprehensive",
                "model_profile": "quality, balanced, budget",
            }
            if key in allowed:
                return f"Invalid value '{value}' for '{key}'. Allowed: {allowed[key]}"
            return f"Invalid value '{value}' for '{key}'"

    return None
