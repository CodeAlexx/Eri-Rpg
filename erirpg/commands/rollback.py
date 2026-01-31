#!/usr/bin/env python3
"""
/coder:rollback - Undo execution via git.

Usage:
    python -m erirpg.commands.rollback [--json]
    python -m erirpg.commands.rollback --to <commit> [--json]
    python -m erirpg.commands.rollback --list [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.git_ops import (
    preview_rollback,
    execute_rollback,
    find_last_plan_commits,
    get_commit_hash,
)


def rollback(
    to_commit: Optional[str] = None,
    list_checkpoints: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Rollback to checkpoint or commit."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "rollback",
        "project": str(project_path),
    }

    try:
        if list_checkpoints:
            # List available plan commits as checkpoints
            commits = find_last_plan_commits()
            result["checkpoints"] = commits
            result["count"] = len(commits)

        elif to_commit:
            # Preview and execute rollback
            current = get_commit_hash("HEAD")
            result["before"] = current

            preview = preview_rollback(to_commit)
            result["preview"] = preview

            if preview.get("can_rollback"):
                rollback_result = execute_rollback(to_commit)
                result["after"] = get_commit_hash("HEAD")
                result["status"] = "rolled_back"
                result["message"] = f"Rolled back to {to_commit}"
            else:
                result["status"] = "cannot_rollback"
                result["message"] = preview.get("reason", "Rollback not possible")

        else:
            # Show last commits as potential rollback points
            commits = find_last_plan_commits()
            if commits:
                result["available_checkpoints"] = commits[:5]
                result["message"] = "Use --to <commit> to rollback, or --list to see all"
            else:
                result["message"] = "No plan commits found"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    list_checkpoints = "--list" in sys.argv

    to_commit = None
    if "--to" in sys.argv:
        idx = sys.argv.index("--to")
        if idx + 1 < len(sys.argv):
            to_commit = sys.argv[idx + 1]

    rollback(to_commit=to_commit, list_checkpoints=list_checkpoints, output_json=output_json)


if __name__ == "__main__":
    main()
