#!/usr/bin/env python3
"""
/coder:add-feature - Add feature to existing codebase (brownfield).

Workflow for adding features to existing projects:
1. Analyze impact
2. Create feature branch
3. Plan implementation
4. Execute with checkpoints

Usage:
    python -m erirpg.commands.add_feature <description> [--json]
    python -m erirpg.commands.add_feature <description> --branch <name> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir, update_state
from erirpg.coder.git_ops import create_branch, get_current_branch
from erirpg.coder.planning import add_phase_to_roadmap


def add_feature(
    description: str,
    branch_name: Optional[str] = None,
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

        # Generate branch name if not provided
        if not branch_name:
            slug = description.lower().replace(" ", "-")[:30]
            branch_name = f"feature/{slug}"

        result["branch"] = branch_name

        # Create feature branch
        try:
            current = get_current_branch(project_path)
            result["base_branch"] = current
            branch_result = create_branch(project_path, branch_name)
            result["branch_created"] = True
        except Exception as e:
            result["branch_error"] = str(e)
            result["branch_created"] = False

        # Add as phase in roadmap
        from erirpg.coder.planning import get_roadmap_phases
        existing = get_roadmap_phases(project_path)
        phase_number = len(existing) + 1

        phase = add_phase_to_roadmap(
            project_path,
            number=phase_number,
            name=f"Feature: {description[:40]}",
            goal=description
        )

        result["phase"] = phase
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
status: planning
---

# Feature: {description}

## Description
{description}

## Impact Analysis
- **Files affected**: [List files]
- **Components affected**: [List components]
- **Dependencies**: [List dependencies]

## Implementation Plan
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Testing Plan
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Rollback Plan
[How to rollback if needed]
"""
        feature_file.write_text(feature_content)
        result["feature_file"] = str(feature_file)

        result["status"] = "created"
        result["message"] = f"Feature '{description[:40]}...' set up as phase {phase_number}"
        result["next_steps"] = [
            f"Edit {feature_file} to complete impact analysis",
            f"Run /coder:plan-phase {phase_number} to create plans",
            f"Run /coder:execute-phase {phase_number} to implement"
        ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --branch argument
    branch_name = None
    if "--branch" in sys.argv:
        idx = sys.argv.index("--branch")
        if idx + 1 < len(sys.argv):
            branch_name = sys.argv[idx + 1]

    # Get description (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if branch_name and branch_name in args:
        args.remove(branch_name)

    if not args:
        print(json.dumps({
            "error": "Feature description required",
            "usage": "python -m erirpg.commands.add_feature <description> [--branch <name>]"
        }, indent=2))
        sys.exit(1)

    description = " ".join(args)
    add_feature(description, branch_name=branch_name, output_json=output_json)


if __name__ == "__main__":
    main()
