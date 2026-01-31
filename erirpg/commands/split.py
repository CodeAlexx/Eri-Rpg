#!/usr/bin/env python3
"""
/coder:split - Break plan into smaller plans.

Splits a large plan into multiple smaller, focused plans.

Usage:
    python -m erirpg.commands.split <plan-file> [--json]
    python -m erirpg.commands.split <plan-file> --into <n> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.planning import split_plan, analyze_plan_complexity


def split(
    plan_file: str,
    into_parts: Optional[int] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Split a plan into smaller plans."""
    if project_path is None:
        project_path = Path.cwd()

    plan_path = Path(plan_file)
    if not plan_path.is_absolute():
        plan_path = project_path / plan_file

    result = {
        "command": "split",
        "project": str(project_path),
        "plan_file": str(plan_path),
    }

    try:
        if not plan_path.exists():
            result["error"] = f"Plan file not found: {plan_path}"
        else:
            # Analyze complexity first
            complexity = analyze_plan_complexity(plan_path)
            result["complexity"] = complexity

            # Split the plan
            new_plans = split_plan(plan_path, into_parts=into_parts)
            result["split_into"] = len(new_plans)
            result["new_plans"] = [str(p) for p in new_plans]
            result["message"] = f"Split into {len(new_plans)} smaller plans"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --into argument
    into_parts = None
    if "--into" in sys.argv:
        idx = sys.argv.index("--into")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            into_parts = int(sys.argv[idx + 1])

    # Get plan file
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if into_parts and str(into_parts) in args:
        args.remove(str(into_parts))

    if not args:
        print(json.dumps({
            "error": "Plan file required",
            "usage": "python -m erirpg.commands.split <plan-file> [--into <n>]"
        }, indent=2))
        sys.exit(1)

    plan_file = args[0]
    split(plan_file, into_parts=into_parts, output_json=output_json)


if __name__ == "__main__":
    main()
