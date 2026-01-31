#!/usr/bin/env python3
"""
/coder:diff - Show changes since checkpoint.

Displays git diff from checkpoint or between commits.

Usage:
    python -m erirpg.commands.diff [--json]
    python -m erirpg.commands.diff <checkpoint> [--json]
    python -m erirpg.commands.diff --from <commit1> --to <commit2> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.git_ops import (
    get_diff,
    get_diff_stats,
    list_checkpoints,
)


def diff(
    checkpoint: Optional[str] = None,
    from_commit: Optional[str] = None,
    to_commit: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Get diff from checkpoint or between commits."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "diff",
        "project": str(project_path),
    }

    try:
        if from_commit and to_commit:
            # Diff between two commits
            diff_output = get_diff(project_path, from_commit, to_commit)
            stats = get_diff_stats(project_path, from_commit, to_commit)
            result["from"] = from_commit
            result["to"] = to_commit
            result["diff"] = diff_output
            result["stats"] = stats

        elif checkpoint:
            # Diff from checkpoint
            diff_output = get_diff(project_path, checkpoint, "HEAD")
            stats = get_diff_stats(project_path, checkpoint, "HEAD")
            result["from"] = checkpoint
            result["to"] = "HEAD"
            result["diff"] = diff_output
            result["stats"] = stats

        else:
            # Diff from last checkpoint
            checkpoints = list_checkpoints(project_path)
            if checkpoints:
                last = checkpoints[0]["commit"]
                diff_output = get_diff(project_path, last, "HEAD")
                stats = get_diff_stats(project_path, last, "HEAD")
                result["from"] = last
                result["from_name"] = checkpoints[0].get("name")
                result["to"] = "HEAD"
                result["diff"] = diff_output
                result["stats"] = stats
            else:
                # No checkpoints, show uncommitted changes
                diff_output = get_diff(project_path, "HEAD", None)
                stats = get_diff_stats(project_path, "HEAD", None)
                result["from"] = "HEAD"
                result["to"] = "working tree"
                result["diff"] = diff_output
                result["stats"] = stats

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --from and --to arguments
    from_commit = None
    to_commit = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            from_commit = sys.argv[idx + 1]
    if "--to" in sys.argv:
        idx = sys.argv.index("--to")
        if idx + 1 < len(sys.argv):
            to_commit = sys.argv[idx + 1]

    # Get checkpoint (non-flag arguments)
    checkpoint = None
    if not from_commit:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            checkpoint = args[0]

    diff(
        checkpoint=checkpoint,
        from_commit=from_commit,
        to_commit=to_commit,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
