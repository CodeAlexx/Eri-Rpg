#!/usr/bin/env python3
"""
/coder:merge - Combine multiple plans.

Usage:
    python -m erirpg.commands.merge <plan1> <plan2> [plan3...] [--json]
    python -m erirpg.commands.merge <plan1> <plan2> --output <file> [--json]
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

from erirpg.coder.planning import merge_plans


def merge(
    plan_files: List[str],
    output_file: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Merge multiple plans."""
    if project_path is None:
        project_path = Path.cwd()

    plan_paths = []
    for pf in plan_files:
        path = Path(pf)
        if not path.is_absolute():
            path = project_path / pf
        plan_paths.append(path)

    result = {
        "command": "merge",
        "project": str(project_path),
        "plan_files": [str(p) for p in plan_paths],
    }

    try:
        missing = [str(p) for p in plan_paths if not p.exists()]
        if missing:
            result["error"] = f"Plan files not found: {missing}"
        else:
            merged = merge_plans(plan_paths, output_file)
            result["merged_plan"] = merged
            result["plans_merged"] = len(plan_paths)
            result["message"] = f"Merged {len(plan_paths)} plans"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if output_file and output_file in args:
        args.remove(output_file)

    if len(args) < 2:
        print(json.dumps({
            "error": "At least 2 plan files required",
            "usage": "python -m erirpg.commands.merge <plan1> <plan2> [--output <file>]"
        }, indent=2))
        sys.exit(1)

    merge(args, output_file=output_file, output_json=output_json)


if __name__ == "__main__":
    main()
