#!/usr/bin/env python3
"""
/coder:compare - Compare approaches/branches.

Compares two branches or approaches for differences.

Usage:
    python -m erirpg.commands.compare <branch1> <branch2> [--json]
    python -m erirpg.commands.compare --approaches [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.git_ops import (
    compare_branches,
    list_approach_branches,
)


def compare(
    branch1: Optional[str] = None,
    branch2: Optional[str] = None,
    list_approaches: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Compare branches or approaches."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "compare",
        "project": str(project_path),
    }

    try:
        if list_approaches:
            # List available approach branches
            approaches = list_approach_branches(project_path)
            result["approaches"] = approaches
            result["count"] = len(approaches)

        elif branch1 and branch2:
            # Compare two branches
            comparison = compare_branches(project_path, branch1, branch2)
            result["branch1"] = branch1
            result["branch2"] = branch2
            result["comparison"] = comparison

        else:
            result["error"] = "Provide two branches or use --approaches"
            result["usage"] = {
                "compare": "python -m erirpg.commands.compare <branch1> <branch2>",
                "list": "python -m erirpg.commands.compare --approaches"
            }

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    list_approaches = "--approaches" in sys.argv

    # Get branches (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    branch1 = args[0] if len(args) > 0 else None
    branch2 = args[1] if len(args) > 1 else None

    compare(
        branch1=branch1,
        branch2=branch2,
        list_approaches=list_approaches,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
