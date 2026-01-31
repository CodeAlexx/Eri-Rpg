#!/usr/bin/env python3
"""
/coder:progress - Show current position and metrics.

Displays:
- Current phase and plan status
- Completion percentages
- Performance metrics
- What's next

Usage:
    python -m erirpg.commands.progress [--json] [--detailed]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import (
    load_project_state,
    get_progress_metrics,
    get_current_position,
)
from erirpg.coder.metrics import get_session_metrics


def progress(
    project_path: Optional[Path] = None,
    output_json: bool = False,
    detailed: bool = False
) -> dict:
    """Get current progress and metrics."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "progress",
        "project": str(project_path),
        "position": None,
        "metrics": None,
        "session_metrics": None,
        "next_steps": [],
    }

    # Get current position
    try:
        result["position"] = get_current_position(project_path)
    except Exception as e:
        result["position"] = {"error": str(e)}

    # Get progress metrics
    try:
        result["metrics"] = get_progress_metrics(project_path)
    except Exception as e:
        result["metrics"] = {"error": str(e)}

    # Get session metrics if detailed
    if detailed:
        try:
            result["session_metrics"] = get_session_metrics(project_path)
        except Exception as e:
            result["session_metrics"] = {"error": str(e)}

    # Determine next steps
    pos = result.get("position", {})
    if pos and not pos.get("error"):
        current_phase = pos.get("current_phase")
        current_plan = pos.get("current_plan")
        status = pos.get("status")

        if status == "idle":
            result["next_steps"].append("Run /coder:plan-phase to start planning")
        elif status == "planning":
            result["next_steps"].append(f"Continue planning phase {current_phase}")
        elif status == "executing":
            result["next_steps"].append(f"Continue executing plan {current_plan}")
        elif status == "verifying":
            result["next_steps"].append("Run /coder:verify-work to complete verification")
        elif status == "complete":
            result["next_steps"].append("Run /coder:new-milestone or add more phases")

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    detailed = "--detailed" in sys.argv
    progress(output_json=output_json, detailed=detailed)


if __name__ == "__main__":
    main()
