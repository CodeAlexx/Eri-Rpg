#!/usr/bin/env python3
"""
/coder:add-phase - Append a new phase to the roadmap.

Usage:
    python -m erirpg.commands.add_phase <name> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import ensure_planning_dir, load_roadmap


def add_phase(
    name: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a phase to the roadmap."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "add-phase",
        "project": str(project_path),
        "name": name,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)
        roadmap_path = planning_dir / "ROADMAP.md"

        # Count existing phases
        roadmap = load_roadmap(project_path)
        existing = len(roadmap.get("phases", []))
        new_number = existing + 1

        # Append to ROADMAP.md
        new_section = f"""

## Phase {new_number}: {name}
**Status:** pending
**Goal:** [Define goal]

### Success Criteria
- [ ] [Criterion 1]
"""

        if roadmap_path.exists():
            content = roadmap_path.read_text()
            roadmap_path.write_text(content + new_section)
        else:
            roadmap_path.write_text(f"# Roadmap\n{new_section}")

        result["phase_number"] = new_number
        result["message"] = f"Phase {new_number}: {name} added to roadmap"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print(json.dumps({
            "error": "Phase name required",
            "usage": "python -m erirpg.commands.add_phase <name>"
        }, indent=2))
        sys.exit(1)

    name = " ".join(args)
    add_phase(name, output_json=output_json)


if __name__ == "__main__":
    main()
