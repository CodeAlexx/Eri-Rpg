#!/usr/bin/env python3
"""
/coder:quick - Ad-hoc task with coder guarantees.

Usage:
    python -m erirpg.commands.quick <description> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir


def quick(
    description: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Create a quick task with tracking."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    quick_dir = planning_dir / "quick"
    quick_dir.mkdir(parents=True, exist_ok=True)

    # Generate task number
    existing = list(quick_dir.glob("*"))
    task_num = len(existing) + 1
    task_id = f"{task_num:03d}"

    # Create task directory
    slug = description.lower().replace(" ", "-")[:30]
    task_dir = quick_dir / f"{task_id}-{slug}"
    task_dir.mkdir(parents=True, exist_ok=True)

    # Create PLAN.md
    plan_content = f"""---
task: {task_id}
description: {description}
created: {datetime.utcnow().isoformat()}Z
status: planning
---

# Quick Task: {description}

## Objective
{description}

## Tasks
- [ ] Task 1: TBD
- [ ] Task 2: TBD

## Verification
- [ ] Functionality works as expected
- [ ] No regressions introduced
"""

    plan_path = task_dir / "PLAN.md"
    plan_path.write_text(plan_content)

    result = {
        "command": "quick",
        "task_id": task_id,
        "description": description,
        "task_dir": str(task_dir),
        "plan_path": str(plan_path),
        "status": "created",
        "next_steps": [
            f"Edit {plan_path} to refine tasks",
            "Execute the tasks",
            "Run /coder:quick --complete to finish"
        ]
    }

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    output_json = "--json" in sys.argv

    if not args:
        print(json.dumps({
            "error": "Description required",
            "usage": "python -m erirpg.commands.quick <description> [--json]"
        }, indent=2))
        sys.exit(1)

    description = " ".join(args)
    quick(description, output_json=output_json)


if __name__ == "__main__":
    main()
