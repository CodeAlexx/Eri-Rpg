#!/usr/bin/env python3
"""
/coder:execute-phase - Execute all plans for a phase.

Usage:
    python -m erirpg.commands.execute_phase <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir, load_roadmap
from erirpg.coder.planning import list_phase_plans


def execute_phase(
    phase_number: int,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Execute plans for a phase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "execute-phase",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        # Get plans
        plans = list_phase_plans(phase_number, project_path)

        if not plans:
            result["error"] = f"No plans found for phase {phase_number}"
            result["message"] = "Run /coder:plan-phase first"
        else:
            result["total_plans"] = len(plans)
            result["plans"] = plans
            result["status"] = "ready"
            result["message"] = f"Phase {phase_number} ready for execution ({len(plans)} plans)"
            result["next_steps"] = [
                "Execute each plan in order",
                "Create summaries after each plan",
                f"Run /coder:verify-work {phase_number} when complete"
            ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.execute_phase <phase-number>"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    execute_phase(phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
