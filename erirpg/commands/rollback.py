#!/usr/bin/env python3
"""
/coder:rollback - Undo execution via git.

Rolls back to a previous checkpoint or commit.

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
    rollback_to_checkpoint,
    list_checkpoints,
    get_current_commit,
)


def rollback(
    to_commit: Optional[str] = None,
    list_checkpoints_only: bool = False,
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
        if list_checkpoints_only:
            # List available checkpoints
            checkpoints = list_checkpoints(project_path)
            result["checkpoints"] = checkpoints
            result["count"] = len(checkpoints)

        elif to_commit:
            # Rollback to specific commit
            current = get_current_commit(project_path)
            result["before"] = current

            rollback_result = rollback_to_checkpoint(project_path, to_commit)
            result["after"] = rollback_result.get("commit")
            result["status"] = "rolled_back"
            result["message"] = f"Rolled back to {to_commit}"

        else:
            # Rollback to last checkpoint
            checkpoints = list_checkpoints(project_path)
            if checkpoints:
                last_checkpoint = checkpoints[0]
                current = get_current_commit(project_path)
                result["before"] = current

                rollback_result = rollback_to_checkpoint(project_path, last_checkpoint["commit"])
                result["after"] = last_checkpoint["commit"]
                result["status"] = "rolled_back"
                result["message"] = f"Rolled back to last checkpoint: {last_checkpoint.get('name', last_checkpoint['commit'])}"
            else:
                result["status"] = "no_checkpoints"
                result["message"] = "No checkpoints available"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    list_only = "--list" in sys.argv

    # Parse --to argument
    to_commit = None
    if "--to" in sys.argv:
        idx = sys.argv.index("--to")
        if idx + 1 < len(sys.argv):
            to_commit = sys.argv[idx + 1]

    rollback(
        to_commit=to_commit,
        list_checkpoints_only=list_only,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
