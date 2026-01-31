#!/usr/bin/env python3
"""
/coder:plan-milestone-gaps - Create phases for audit gaps.

Usage:
    python -m erirpg.commands.plan_milestone_gaps [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir, load_roadmap


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
        planning_dir = ensure_planning_dir(project_path)

        # Look for verification files with gaps
        gaps = []
        phases_dir = planning_dir / "phases"
        if phases_dir.exists():
            for phase_dir in phases_dir.iterdir():
                if phase_dir.is_dir():
                    verification = phase_dir / "VERIFICATION.md"
                    if verification.exists():
                        content = verification.read_text()
                        if "gaps_found" in content.lower() or "status: gaps" in content.lower():
                            gaps.append({
                                "phase": phase_dir.name,
                                "file": str(verification)
                            })

        result["gaps_found"] = len(gaps)
        result["gaps"] = gaps

        if gaps:
            result["message"] = f"Found {len(gaps)} phases with gaps - create remediation phases"
            result["next_steps"] = [
                "Review each gap in detail",
                "Create new phases with /coder:add-phase for each gap"
            ]
        else:
            result["message"] = "No gaps found - all verifications passed"

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
