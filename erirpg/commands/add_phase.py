#!/usr/bin/env python3
"""
/coder:add-phase - Append a new phase to the roadmap.

Usage:
    python -m erirpg.commands.add_phase <name> [--json]
    python -m erirpg.commands.add_phase <name> --goal <goal> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import ensure_planning_dir
from erirpg.coder.planning import add_phase_to_roadmap, get_roadmap_phases


def add_phase(
    name: str,
    goal: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a phase to the roadmap."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "add-phase",
        "project": str(project_path),
        "name": name,
    }

    try:
        ensure_planning_dir(project_path)

        # Get existing phases to determine number
        existing = get_roadmap_phases(project_path)
        new_number = len(existing) + 1

        # Add phase
        phase = add_phase_to_roadmap(
            project_path,
            number=new_number,
            name=name,
            goal=goal
        )

        result["phase"] = phase
        result["phase_number"] = new_number
        result["message"] = f"Phase {new_number}: {name} added to roadmap"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --goal argument
    goal = None
    if "--goal" in sys.argv:
        idx = sys.argv.index("--goal")
        if idx + 1 < len(sys.argv):
            goal = sys.argv[idx + 1]

    # Get name (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if goal and goal in args:
        args.remove(goal)

    if not args:
        print(json.dumps({
            "error": "Phase name required",
            "usage": "python -m erirpg.commands.add_phase <name> [--goal <goal>]"
        }, indent=2))
        sys.exit(1)

    name = " ".join(args)
    add_phase(name, goal=goal, output_json=output_json)


if __name__ == "__main__":
    main()
