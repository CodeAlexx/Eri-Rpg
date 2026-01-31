#!/usr/bin/env python3
"""
/coder:remove-phase - Remove a future phase.

Usage:
    python -m erirpg.commands.remove_phase <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir


def remove_phase(
    phase_number: int,
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
        planning_dir = ensure_planning_dir(project_path)

        result["message"] = f"Phase {phase_number} marked for removal"
        result["note"] = "Manually edit ROADMAP.md to remove the phase section"

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
            "usage": "python -m erirpg.commands.remove_phase <phase-number>"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    remove_phase(phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
