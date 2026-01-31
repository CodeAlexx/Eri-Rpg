#!/usr/bin/env python3
"""
/coder:add-todo - Capture idea for later.

Usage:
    python -m erirpg.commands.add_todo <idea> [--priority high|medium|low] [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.todos import add_todo as _add_todo


def add_todo(
    idea: str,
    priority: str = "medium",
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a todo item."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "add-todo",
        "project": str(project_path),
    }

    try:
        todo = _add_todo(idea, priority=priority, project_path=project_path)
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

    priority = "medium"
    if "--priority" in sys.argv:
        idx = sys.argv.index("--priority")
        if idx + 1 < len(sys.argv):
            priority = sys.argv[idx + 1]

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
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
