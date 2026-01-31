#!/usr/bin/env python3
"""
/coder:new-project - Initialize a new project.

Creates project structure with:
- PROJECT.md
- config.json
- REQUIREMENTS.md
- ROADMAP.md
- STATE.md

Usage:
    python -m erirpg.commands.new_project [name] [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir
from erirpg.coder import save_config, get_default_config


def new_project(
    name: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Initialize a new project."""
    if project_path is None:
        project_path = Path.cwd()

    if not name:
        name = project_path.name

    result = {
        "command": "new-project",
        "project": str(project_path),
        "name": name,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Create PROJECT.md
        project_md = planning_dir / "PROJECT.md"
        if not project_md.exists():
            project_md.write_text(f"""---
name: {name}
created: {datetime.utcnow().isoformat()}Z
version: "0.1.0"
status: planning
---

# {name}

## Vision
[Describe the project vision and goals]

## Constraints
- [List any technical or business constraints]

## Success Criteria
- [ ] [Define measurable success criteria]

## Decisions
[Track key architectural and design decisions]
""")
            result["created_project_md"] = True

        # Create config.json
        config = get_default_config()
        config["project_name"] = name
        save_config(config, project_path)
        result["created_config"] = True

        # Create REQUIREMENTS.md
        requirements_md = planning_dir / "REQUIREMENTS.md"
        if not requirements_md.exists():
            requirements_md.write_text(f"""---
project: {name}
version: "0.1.0"
---

# Requirements

## V1 Scope

### REQ-001: [Requirement Name]
- **Priority**: P1
- **Description**: [Describe the requirement]
- **Acceptance Criteria**:
  - [ ] Criterion 1
  - [ ] Criterion 2

## V2 Scope
[Future requirements]

## Out of Scope
[What is explicitly NOT included]
""")
            result["created_requirements"] = True

        # Create ROADMAP.md
        roadmap_md = planning_dir / "ROADMAP.md"
        if not roadmap_md.exists():
            roadmap_md.write_text(f"""---
project: {name}
milestone: "0.1.0"
---

# Roadmap

## Phase 1: Foundation
**Status:** pending
**Goal:** Set up project foundation

### Requirements Covered
- REQ-001

### Success Criteria
- [ ] Basic structure in place
- [ ] Core functionality working
""")
            result["created_roadmap"] = True

        # Create STATE.md
        state_md = planning_dir / "STATE.md"
        if not state_md.exists():
            state_md.write_text(f"""---
project: {name}
current_phase: 1
status: planning
last_updated: {datetime.utcnow().isoformat()}Z
---

# Current State

## Position
- **Phase**: 1 - Foundation
- **Status**: Planning

## Context
[Session context and notes]

## Blockers
[Any current blockers]
""")
            result["created_state"] = True

        # Create directories
        (planning_dir / "phases").mkdir(exist_ok=True)
        (planning_dir / "research").mkdir(exist_ok=True)
        (planning_dir / "quick").mkdir(exist_ok=True)
        result["created_directories"] = ["phases", "research", "quick"]

        result["message"] = f"Project '{name}' initialized"
        result["next_steps"] = [
            "Edit PROJECT.md to define vision",
            "Edit REQUIREMENTS.md to list requirements",
            "Edit ROADMAP.md to plan phases",
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
    name = args[0] if args else None

    new_project(name=name, output_json=output_json)


if __name__ == "__main__":
    main()
