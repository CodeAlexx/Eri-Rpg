#!/usr/bin/env python3
"""
/coder:history - Execution history.

Usage:
    python -m erirpg.commands.history [--json]
    python -m erirpg.commands.history --limit <n> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.metrics import get_execution_history


def history(
    limit: int = 20,
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
        history_data = get_execution_history(project_path, limit=limit)
        result["entries"] = history_data
        result["count"] = len(history_data)

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    limit = 20
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            limit = int(sys.argv[idx + 1])

    history(limit=limit, output_json=output_json)


if __name__ == "__main__":
    main()
