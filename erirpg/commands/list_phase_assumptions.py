#!/usr/bin/env python3
"""
/coder:list-phase-assumptions - See Claude's approach for a phase.

Usage:
    python -m erirpg.commands.list_phase_assumptions <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.planning import get_phase_assumptions


def list_phase_assumptions(
    phase_number: int,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Get assumptions for a phase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "list-phase-assumptions",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        assumptions = get_phase_assumptions(project_path, phase_number)
        result["assumptions"] = assumptions
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
            "usage": "python -m erirpg.commands.list_phase_assumptions <phase-number>"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    list_phase_assumptions(phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
