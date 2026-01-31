#!/usr/bin/env python3
"""
/coder:new-milestone - Start next version.

Creates new milestone with:
- Version bump
- Fresh roadmap section
- State reset

Usage:
    python -m erirpg.commands.new_milestone <version> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir, update_state
from erirpg.coder import load_config, save_config


def new_milestone(
    version: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Start a new milestone/version."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "new-milestone",
        "project": str(project_path),
        "version": version,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Update config
        config = load_config(project_path)
        previous_version = config.get("version", "0.0.0")
        config["version"] = version
        config["previous_version"] = previous_version
        save_config(config, project_path)

        result["previous_version"] = previous_version

        # Update ROADMAP.md to add new milestone section
        roadmap_path = planning_dir / "ROADMAP.md"
        if roadmap_path.exists():
            roadmap_content = roadmap_path.read_text()
            new_section = f"""

---

# Milestone {version}

## Phase 1: [First Phase Name]
**Status:** pending
**Goal:** [Define goal]

### Requirements
- [REQ-XXX]

### Success Criteria
- [ ] [Criterion 1]
"""
            roadmap_path.write_text(roadmap_content + new_section)
            result["roadmap_updated"] = True

        # Reset state for new milestone
        update_state(project_path, {
            "current_phase": 1,
            "milestone": version,
            "status": "planning",
            "milestone_started": datetime.utcnow().isoformat() + "Z"
        })

        result["status"] = "created"
        result["message"] = f"Milestone {version} started"
        result["next_steps"] = [
            "Edit ROADMAP.md to define phases for this milestone",
            "Run /coder:plan-phase 1 to start planning"
        ]

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
            "error": "Version required",
            "usage": "python -m erirpg.commands.new_milestone <version>"
        }, indent=2))
        sys.exit(1)

    version = args[0]
    new_milestone(version, output_json=output_json)


if __name__ == "__main__":
    main()
