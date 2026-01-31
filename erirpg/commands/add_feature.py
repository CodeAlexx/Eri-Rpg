#!/usr/bin/env python3
"""
/coder:add-feature - Add feature to existing codebase (brownfield).

Usage:
    python -m erirpg.commands.add_feature <description> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir, load_roadmap


def add_feature(
    description: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a feature to an existing codebase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "add-feature",
        "project": str(project_path),
        "description": description,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Generate branch name
        slug = description.lower().replace(" ", "-")[:30]
        branch_name = f"feature/{slug}"

        result["branch"] = branch_name

        # Count existing phases and add as new phase
        roadmap = load_roadmap(project_path)
        existing = len(roadmap.get("phases", []))
        phase_number = existing + 1

        # Append to roadmap
        roadmap_path = planning_dir / "ROADMAP.md"
        new_section = f"""

## Phase {phase_number}: Feature - {description[:40]}
**Status:** pending
**Goal:** {description}

### Success Criteria
- [ ] Feature implemented
- [ ] Tests passing
"""

        if roadmap_path.exists():
            content = roadmap_path.read_text()
            roadmap_path.write_text(content + new_section)

        result["phase_number"] = phase_number

        # Create feature directory
        feature_dir = planning_dir / "features"
        feature_dir.mkdir(exist_ok=True)

        feature_file = feature_dir / f"{branch_name.replace('/', '-')}.md"
        feature_content = f"""---
feature: {description}
branch: {branch_name}
created: {datetime.utcnow().isoformat()}Z
phase: {phase_number}
---

# Feature: {description}

## Description
{description}

## Impact Analysis
- **Files affected**: [List files]
- **Components affected**: [List components]

## Implementation Plan
1. [Step 1]
2. [Step 2]
"""
        feature_file.write_text(feature_content)
        result["feature_file"] = str(feature_file)

        result["message"] = f"Feature set up as phase {phase_number}"
        result["next_steps"] = [
            f"Create branch: git checkout -b {branch_name}",
            f"Run /coder:plan-phase {phase_number}",
            f"Run /coder:execute-phase {phase_number}"
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
            "error": "Feature description required",
            "usage": "python -m erirpg.commands.add_feature <description>"
        }, indent=2))
        sys.exit(1)

    description = " ".join(args)
    add_feature(description, output_json=output_json)


if __name__ == "__main__":
    main()
