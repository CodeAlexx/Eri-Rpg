#!/usr/bin/env python3
"""
/coder:replay - Re-run phase with different parameters.

Usage:
    python -m erirpg.commands.replay <phase-number> [--json]
    python -m erirpg.commands.replay <phase-number> --reset [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.planning import prepare_replay, list_phase_plans
from erirpg.coder import load_roadmap


def replay(
    phase_number: int,
    reset_first: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Prepare to replay a phase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "replay",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        # Get phase plans
        plans = list_phase_plans(phase_number, project_path)
        result["plans_found"] = len(plans)
        result["plans"] = plans

        # Prepare replay
        replay_info = prepare_replay(phase_number, project_path)
        result["replay_info"] = replay_info

        result["message"] = f"Phase {phase_number} prepared for replay"
        result["next_steps"] = [
            f"Run /coder:execute-phase {phase_number} to re-execute",
            "Modify plans first if needed"
        ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    reset_first = "--reset" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.replay <phase-number> [--reset]"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    replay(phase_number, reset_first=reset_first, output_json=output_json)


if __name__ == "__main__":
    main()
