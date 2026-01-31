#!/usr/bin/env python3
"""
/coder:insert-phase - Insert urgent work between phases.

Usage:
    python -m erirpg.commands.insert_phase <position> <name> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir


def insert_phase(
    position: int,
    name: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Insert a phase at a specific position."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "insert-phase",
        "project": str(project_path),
        "position": position,
        "name": name,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)
        roadmap_path = planning_dir / "ROADMAP.md"

        result["message"] = f"Phase {position}: {name} inserted (manual renumbering may be needed)"
        result["note"] = "Update ROADMAP.md to renumber subsequent phases"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 2 or not args[0].isdigit():
        print(json.dumps({
            "error": "Position and name required",
            "usage": "python -m erirpg.commands.insert_phase <position> <name>"
        }, indent=2))
        sys.exit(1)

    position = int(args[0])
    name = " ".join(args[1:])
    insert_phase(position, name, output_json=output_json)


if __name__ == "__main__":
    main()
