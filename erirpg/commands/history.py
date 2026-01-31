#!/usr/bin/env python3
"""
/coder:history - Execution history.

Shows history of:
- Phase executions
- Plan executions
- Debug sessions
- Quick tasks

Usage:
    python -m erirpg.commands.history [--json]
    python -m erirpg.commands.history --limit <n> [--json]
    python -m erirpg.commands.history --type <phase|plan|debug|quick> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.metrics import get_execution_history


def history(
    limit: int = 20,
    history_type: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Get execution history."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "history",
        "project": str(project_path),
    }

    try:
        history_data = get_execution_history(project_path, limit=limit, filter_type=history_type)
        result["entries"] = history_data
        result["count"] = len(history_data)
        if history_type:
            result["filter"] = history_type

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse arguments
    limit = 20
    history_type = None

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            limit = int(sys.argv[idx + 1])

    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            history_type = sys.argv[idx + 1]

    history(limit=limit, history_type=history_type, output_json=output_json)


if __name__ == "__main__":
    main()
