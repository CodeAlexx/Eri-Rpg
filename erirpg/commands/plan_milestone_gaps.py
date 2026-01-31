#!/usr/bin/env python3
"""
/coder:plan-milestone-gaps - Create phases for audit gaps.

Analyzes verification results and creates phases to address gaps.

Usage:
    python -m erirpg.commands.plan_milestone_gaps [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import ensure_planning_dir, get_planning_dir
from erirpg.coder.planning import (
    find_verification_gaps,
    create_gap_phases,
)


def plan_milestone_gaps(
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Analyze gaps and create phases to address them."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "plan-milestone-gaps",
        "project": str(project_path),
    }

    try:
        # Find gaps from verification results
        gaps = find_verification_gaps(project_path)
        result["gaps_found"] = len(gaps)
        result["gaps"] = gaps

        if gaps:
            # Create phases for gaps
            new_phases = create_gap_phases(project_path, gaps)
            result["phases_created"] = len(new_phases)
            result["new_phases"] = new_phases
            result["message"] = f"Created {len(new_phases)} phases to address {len(gaps)} gaps"
        else:
            result["message"] = "No gaps found - all verifications passed"
            result["phases_created"] = 0

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    plan_milestone_gaps(output_json=output_json)


if __name__ == "__main__":
    main()
