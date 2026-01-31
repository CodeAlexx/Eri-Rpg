#!/usr/bin/env python3
"""
/coder:replay - Re-run phase with different parameters.

Re-executes a phase, optionally with different settings.

Usage:
    python -m erirpg.commands.replay <phase-number> [--json]
    python -m erirpg.commands.replay <phase-number> --reset [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.planning import (
    get_phase_info,
    reset_phase,
    prepare_replay,
)
from erirpg.coder.git_ops import rollback_to_phase_start


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
        # Get phase info
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found"
        else:
            result["phase_info"] = phase_info

            if reset_first:
                # Reset phase state and git
                rollback_result = rollback_to_phase_start(project_path, phase_number)
                reset_result = reset_phase(project_path, phase_number)
                result["reset"] = True
                result["rollback"] = rollback_result
                result["reset_result"] = reset_result

            # Prepare for replay
            replay_info = prepare_replay(project_path, phase_number)
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
