#!/usr/bin/env python3
"""
/coder:discuss-phase - Capture implementation decisions for a phase.

Usage:
    python -m erirpg.commands.discuss_phase <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir, load_roadmap


def discuss_phase(
    phase_number: int,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Create or get phase discussion context."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "discuss-phase",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Get phase info from roadmap
        roadmap = load_roadmap(project_path)
        phase_info = None
        for p in roadmap.get("phases", []):
            if p.get("number") == phase_number:
                phase_info = p
                break

        if not phase_info:
            phase_info = {"number": phase_number, "name": f"Phase {phase_number}"}

        result["phase_info"] = phase_info

        # Create phase directory
        phase_name = phase_info.get("name", f"phase-{phase_number}")
        phase_slug = phase_name.lower().replace(" ", "-")
        phase_dir = planning_dir / "phases" / f"{phase_number:02d}-{phase_slug}"
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Create CONTEXT.md
        context_path = phase_dir / f"phase-{phase_number:02d}-CONTEXT.md"

        if context_path.exists():
            result["context_file"] = str(context_path)
            result["exists"] = True
        else:
            context_content = f"""---
phase: {phase_number}
name: {phase_name}
created: {datetime.utcnow().isoformat()}Z
status: discussing
---

# Phase {phase_number}: {phase_name} - Implementation Context

## Goals
{phase_info.get('goal', '[Define phase goals]')}

## Approach
[Describe the implementation approach]

## Key Decisions
- Decision 1: [Rationale]

## Constraints
- [List any constraints]

## Dependencies
- [List dependencies]

## Open Questions
- [ ] [Question 1]
"""
            context_path.write_text(context_content)
            result["context_file"] = str(context_path)
            result["created"] = True

        result["next_steps"] = [
            f"Edit {context_path} to capture decisions",
            f"Run /coder:plan-phase {phase_number} when ready"
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

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.discuss_phase <phase-number>"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    discuss_phase(phase_number, output_json=output_json)


if __name__ == "__main__":
    main()
