#!/usr/bin/env python3
"""
/coder:compare - Compare approaches/branches.

Usage:
    python -m erirpg.commands.compare <branch1> <branch2> [--json]
    python -m erirpg.commands.compare --list [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.git_ops import compare_branches, list_branches


def compare(
    branch1: Optional[str] = None,
    branch2: Optional[str] = None,
    list_only: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Compare branches or list available branches."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "compare",
        "project": str(project_path),
    }

    try:
        if list_only:
            branches = list_branches()
            result["branches"] = branches
            result["count"] = len(branches)

        elif branch1 and branch2:
            comparison = compare_branches(branch1, branch2)
            result["branch1"] = branch1
            result["branch2"] = branch2
            result.update(comparison)

        else:
            result["error"] = "Provide two branches or use --list"
            result["usage"] = {
                "compare": "python -m erirpg.commands.compare <branch1> <branch2>",
                "list": "python -m erirpg.commands.compare --list"
            }

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    list_only = "--list" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    branch1 = args[0] if len(args) > 0 else None
    branch2 = args[1] if len(args) > 1 else None

    compare(branch1=branch1, branch2=branch2, list_only=list_only, output_json=output_json)


if __name__ == "__main__":
    main()
