"""
EriRPG Coder Module - Logic for /coder:* commands.

This module provides the backend logic for eri-coder workflow commands.
The actual CLI is in cli_commands/coder_cmds.py.

Modules:
- state: Project state management (progress, resume, settings)
- git_ops: Git operations (rollback, diff, compare)
- metrics: Token counting, cost estimation, history tracking
- planning: Plan manipulation (split, merge, replay)
- knowledge: Pattern storage and learning
- docs: Documentation generation (handoff, template)
- debug: Debugging workflow support
- todos: Todo management
"""

from pathlib import Path
from typing import Optional
import json
from datetime import datetime


def get_planning_dir(project_path: Optional[Path] = None) -> Path:
    """Get the .planning directory for a project."""
    if project_path is None:
        project_path = Path.cwd()
    return project_path / ".planning"


def ensure_planning_dir(project_path: Optional[Path] = None) -> Path:
    """Ensure .planning directory exists."""
    planning_dir = get_planning_dir(project_path)
    planning_dir.mkdir(parents=True, exist_ok=True)
    return planning_dir


def load_config(project_path: Optional[Path] = None) -> dict:
    """Load project config from .planning/config.json."""
    config_path = get_planning_dir(project_path) / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return get_default_config()


def save_config(config: dict, project_path: Optional[Path] = None) -> None:
    """Save project config to .planning/config.json."""
    config_path = get_planning_dir(project_path) / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))


def get_default_config() -> dict:
    """Get default configuration."""
    return {
        "mode": "interactive",
        "depth": "standard",
        "parallelization": True,
        "commit_tracking": True,
        "model_profile": "balanced",
        "workflow": {
            "research": True,
            "plan_check": True,
            "verifier": True
        },
        "notifications": {
            "checkpoint_sound": False,
            "phase_complete": True
        }
    }


def load_state(project_path: Optional[Path] = None) -> dict:
    """Load project state from .planning/STATE.md frontmatter."""
    state_path = get_planning_dir(project_path) / "STATE.md"
    if not state_path.exists():
        return {}

    content = state_path.read_text()
    # Parse YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                return yaml.safe_load(parts[1]) or {}
            except:
                pass
    return {}


def load_roadmap(project_path: Optional[Path] = None) -> dict:
    """Load roadmap from .planning/ROADMAP.md."""
    roadmap_path = get_planning_dir(project_path) / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"phases": []}

    content = roadmap_path.read_text()
    # Parse phases from markdown
    phases = []
    current_phase = None

    for line in content.split("\n"):
        if line.startswith("## Phase "):
            if current_phase:
                phases.append(current_phase)
            # Parse phase number and name
            parts = line.replace("## Phase ", "").split(":", 1)
            phase_num = int(parts[0].strip()) if parts[0].strip().isdigit() else len(phases) + 1
            phase_name = parts[1].strip() if len(parts) > 1 else f"Phase {phase_num}"
            current_phase = {
                "number": phase_num,
                "name": phase_name,
                "status": "pending",
                "goals": [],
                "requirements": []
            }
        elif current_phase and line.startswith("**Status:**"):
            status = line.replace("**Status:**", "").strip().lower()
            current_phase["status"] = status

    if current_phase:
        phases.append(current_phase)

    return {"phases": phases}


def timestamp() -> str:
    """Get ISO timestamp."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
