#!/usr/bin/env python3
"""
/coder:discuss-phase - Capture implementation decisions for a phase.

Creates CONTEXT.md with:
- Implementation approach
- Key decisions
- Constraints
- Dependencies

Usage:
    python -m erirpg.commands.discuss_phase <phase-number> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir, get_phase_info
from erirpg.coder.planning import create_phase_directory


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

        # Get phase info
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found"
            if output_json:
                print(json.dumps(result, indent=2, default=str))
            return result

        result["phase_info"] = phase_info

        # Create/get phase directory
        phase_name = phase_info.get("name", f"phase-{phase_number}")
        phase_dir = create_phase_directory(project_path, phase_number, phase_name)

        # Create or read CONTEXT.md
        context_path = phase_dir / f"phase-{phase_number:02d}-CONTEXT.md"

        if context_path.exists():
            result["context_file"] = str(context_path)
            result["exists"] = True
            result["content"] = context_path.read_text()
        else:
            # Create new CONTEXT.md
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
- Decision 2: [Rationale]

## Constraints
- [List any constraints]

## Dependencies
- [List dependencies on other phases/systems]

## Open Questions
- [ ] [Question 1]
- [ ] [Question 2]

## Notes
[Additional context and notes]
"""
            context_path.write_text(context_content)
            result["context_file"] = str(context_path)
            result["exists"] = False
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
