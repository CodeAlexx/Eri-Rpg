#!/usr/bin/env python3
"""
/coder:resume - Restore from last session.

Finds and displays resume state from:
- RESUME.md (explicit pause state)
- STATE.md (current project state)
- CHECKPOINT.md (phase checkpoints)

Usage:
    python -m erirpg.commands.resume [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import (
    get_resume_state,
    load_project_state,
    get_last_activity,
)


def resume(project_path: Optional[Path] = None, output_json: bool = False) -> dict:
    """Get resume state and context for continuing work."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "resume",
        "project": str(project_path),
        "resume_state": None,
        "project_state": None,
        "last_activity": None,
        "recommendations": [],
    }

    # Get resume state
    try:
        result["resume_state"] = get_resume_state(project_path)
    except Exception as e:
        result["resume_state"] = {"error": str(e)}

    # Get project state
    try:
        result["project_state"] = load_project_state(project_path)
    except Exception as e:
        result["project_state"] = {"error": str(e)}

    # Get last activity
    try:
        result["last_activity"] = get_last_activity(project_path)
    except Exception as e:
        result["last_activity"] = {"error": str(e)}

    # Generate recommendations
    if result["resume_state"] and result["resume_state"].get("exists"):
        source = result["resume_state"].get("source", "unknown")
        if source == "RESUME.md":
            result["recommendations"].append("Continue from explicit pause point")
            if result["resume_state"].get("task"):
                result["recommendations"].append(f"Resume task: {result['resume_state']['task']}")
        elif source == "STATE.md":
            phase = result["resume_state"].get("phase")
            if phase:
                result["recommendations"].append(f"Continue phase: {phase}")
        elif source == "CHECKPOINT.md":
            result["recommendations"].append("Resume from checkpoint")
    else:
        result["recommendations"].append("No explicit resume state found")
        result["recommendations"].append("Run /coder:progress to see current status")

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    resume(output_json=output_json)


if __name__ == "__main__":
    main()
