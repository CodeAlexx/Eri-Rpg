#!/usr/bin/env python3
"""
/coder:add-todo - Capture idea for later.

Stores todos in .planning/todos/ for later implementation.

Usage:
    python -m erirpg.commands.add_todo <idea> [--priority high|medium|low] [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir
from erirpg.coder.todos import add_todo as _add_todo, list_todos


def add_todo(
    idea: str,
    priority: str = "medium",
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a todo item."""
    if project_path is None:
        project_path = Path.cwd()

    ensure_planning_dir(project_path)

    result = {
        "command": "add-todo",
        "project": str(project_path),
    }

    try:
        todo = _add_todo(project_path, idea, priority)
        result["status"] = "added"
        result["todo"] = todo
        result["message"] = f"Todo added: {idea[:50]}..."
    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse priority
    priority = "medium"
    if "--priority" in sys.argv:
        idx = sys.argv.index("--priority")
        if idx + 1 < len(sys.argv):
            priority = sys.argv[idx + 1]

    # Get idea (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # Remove priority value if it was parsed
    if priority in args:
        args.remove(priority)

    if not args:
        print(json.dumps({
            "error": "Idea required",
            "usage": "python -m erirpg.commands.add_todo <idea> [--priority high|medium|low]"
        }, indent=2))
        sys.exit(1)

    idea = " ".join(args)
    add_todo(idea, priority=priority, output_json=output_json)


if __name__ == "__main__":
    main()
