#!/usr/bin/env python3
"""
/coder:remove-phase - Remove a future phase.

Only allows removing phases that haven't started.

Usage:
    python -m erirpg.commands.remove_phase <phase-number> [--json]
    python -m erirpg.commands.remove_phase <phase-number> --force [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import ensure_planning_dir
from erirpg.coder.planning import remove_phase_from_roadmap, get_phase_info


def remove_phase(
    phase_number: int,
    force: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Remove a phase from the roadmap."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "remove-phase",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        ensure_planning_dir(project_path)

        # Check phase status
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found"
        elif phase_info.get("status") not in ("pending", "planning") and not force:
            result["error"] = f"Phase {phase_number} has already started. Use --force to remove anyway."
            result["phase_status"] = phase_info.get("status")
        else:
            # Remove phase
            removed = remove_phase_from_roadmap(project_path, phase_number)
            result["removed"] = removed
            result["message"] = f"Phase {phase_number} removed from roadmap"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    force = "--force" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.remove_phase <phase-number> [--force]"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    remove_phase(phase_number, force=force, output_json=output_json)


if __name__ == "__main__":
    main()
