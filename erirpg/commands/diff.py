#!/usr/bin/env python3
"""
/coder:diff - Show changes since checkpoint.

Usage:
    python -m erirpg.commands.diff [--json]
    python -m erirpg.commands.diff <checkpoint> [--json]
    python -m erirpg.commands.diff --from <commit1> --to <commit2> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.git_ops import get_diff, get_diff_since_checkpoint


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
            diff_data = get_diff(from_commit, to_commit)
            result["from"] = from_commit
            result["to"] = to_commit
            result.update(diff_data)

        elif checkpoint:
            # Diff from checkpoint to HEAD
            diff_data = get_diff(checkpoint, "HEAD")
            result["from"] = checkpoint
            result["to"] = "HEAD"
            result.update(diff_data)

        else:
            # Diff from last checkpoint
            diff_data = get_diff_since_checkpoint()
            result.update(diff_data)

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

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

    checkpoint = None
    if not from_commit:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            checkpoint = args[0]

    diff(checkpoint=checkpoint, from_commit=from_commit, to_commit=to_commit, output_json=output_json)


if __name__ == "__main__":
    main()
