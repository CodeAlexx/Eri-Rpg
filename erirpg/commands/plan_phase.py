#!/usr/bin/env python3
"""
/coder:plan-phase - Create executable plans for a phase.

Orchestrates:
- Phase research (optional)
- Plan creation
- Plan verification

Usage:
    python -m erirpg.commands.plan_phase <phase-number> [--json]
    python -m erirpg.commands.plan_phase <phase-number> --skip-research [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import (
    ensure_planning_dir,
    get_phase_info,
    update_state,
)
from erirpg.coder.planning import (
    get_phase_plans,
    create_phase_directory,
)


def plan_phase(
    phase_number: int,
    skip_research: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Plan a phase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "plan-phase",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Get phase info from roadmap
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found in roadmap"
            if output_json:
                print(json.dumps(result, indent=2, default=str))
            return result

        result["phase_info"] = phase_info

        # Create phase directory
        phase_dir = create_phase_directory(project_path, phase_number, phase_info.get("name", f"Phase {phase_number}"))
        result["phase_dir"] = str(phase_dir)

        # Check for existing plans
        existing_plans = get_phase_plans(project_path, phase_number)
        result["existing_plans"] = len(existing_plans)

        # Update state to planning
        update_state(project_path, {
            "current_phase": phase_number,
            "status": "planning"
        })

        result["status"] = "ready_for_planning"
        result["message"] = f"Phase {phase_number} ready for planning"
        result["next_steps"] = []

        if not skip_research and not (phase_dir / f"phase-{phase_number:02d}-RESEARCH.md").exists():
            result["next_steps"].append("Research phase requirements")

        if not existing_plans:
            result["next_steps"].append("Create PLAN.md files for the phase")

        result["next_steps"].append(f"Run /coder:execute-phase {phase_number} when plans are ready")

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    skip_research = "--skip-research" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.plan_phase <phase-number> [--skip-research]"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    plan_phase(phase_number, skip_research=skip_research, output_json=output_json)


if __name__ == "__main__":
    main()
