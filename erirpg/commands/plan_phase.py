#!/usr/bin/env python3
"""
/coder:plan-phase - Create executable plans for a phase.

Usage:
    python -m erirpg.commands.plan_phase <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir, load_roadmap
from erirpg.coder.planning import list_phase_plans


def plan_phase(
    phase_number: int,
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

        # Get roadmap info
        roadmap = load_roadmap(project_path)
        phases = roadmap.get("phases", [])

        phase_info = None
        for p in phases:
            if p.get("number") == phase_number:
                phase_info = p
                break

        if not phase_info:
            # Create minimal phase info
            phase_info = {"number": phase_number, "name": f"Phase {phase_number}"}

        result["phase_info"] = phase_info

        # Create phase directory
        phase_name_slug = phase_info.get("name", f"phase-{phase_number}").lower().replace(" ", "-")
        phase_dir = planning_dir / "phases" / f"{phase_number:02d}-{phase_name_slug}"
        phase_dir.mkdir(parents=True, exist_ok=True)
        result["phase_dir"] = str(phase_dir)

        # Check existing plans
        existing_plans = list_phase_plans(phase_number, project_path)
        result["existing_plans"] = len(existing_plans)

        result["status"] = "ready_for_planning"
        result["message"] = f"Phase {phase_number} ready for planning"
        result["next_steps"] = [
            f"Create PLAN.md files in {phase_dir}",
            f"Run /coder:execute-phase {phase_number} when plans are ready"
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
            "usage": "python -m erirpg.commands.plan_phase <phase-number>"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    plan_phase(phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
