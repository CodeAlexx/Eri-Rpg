#!/usr/bin/env python3
"""
/coder:cost - Estimate tokens and cost.

Analyzes project to estimate token usage and API costs.

Usage:
    python -m erirpg.commands.cost [--json]
    python -m erirpg.commands.cost --phase <n> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.metrics import (
    estimate_project_cost,
    estimate_phase_cost,
    get_token_stats,
)


def cost(
    phase_number: Optional[int] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Estimate tokens and cost."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "cost",
        "project": str(project_path),
    }

    try:
        if phase_number:
            # Estimate for specific phase
            estimate = estimate_phase_cost(project_path, phase_number)
            result["phase"] = phase_number
            result["estimate"] = estimate
        else:
            # Estimate for whole project
            estimate = estimate_project_cost(project_path)
            result["estimate"] = estimate

        # Get token stats
        stats = get_token_stats(project_path)
        result["token_stats"] = stats

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --phase argument
    phase_number = None
    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            phase_number = int(sys.argv[idx + 1])

    cost(phase_number=phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
