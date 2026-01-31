#!/usr/bin/env python3
"""
/coder:add-feature - Add feature to existing codebase (brownfield).

Usage:
    python -m erirpg.commands.add_feature <description> [--json]
    python -m erirpg.commands.add_feature <program> <feature> "<description>" --reference <source>/<section> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from erirpg.coder import ensure_planning_dir, load_roadmap


def load_behavior_spec(program: str, section: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load a behavior spec from blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / program

    # Handle nested sections
    if "/" in section:
        parts = section.split("/")
        behavior_file = program_dir
        for part in parts[:-1]:
            behavior_file = behavior_file / part
        behavior_file = behavior_file / f"{parts[-1]}-BEHAVIOR.md"
    else:
        behavior_file = program_dir / f"{section}-BEHAVIOR.md"

    if not behavior_file.exists():
        return None

    return {
        "program": program,
        "section": section,
        "file": str(behavior_file),
        "content": behavior_file.read_text()
    }


def load_target_conventions(program: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load target program's overview/conventions from blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / program

    result = {
        "program": program,
        "conventions": None,
        "overview": None
    }

    # Try to load overview
    overview_file = program_dir / "overview.md"
    if overview_file.exists():
        result["overview"] = overview_file.read_text()

    # Try to load conventions if separate
    conventions_file = program_dir / "conventions.md"
    if conventions_file.exists():
        result["conventions"] = conventions_file.read_text()

    # Load index for metadata
    index_file = program_dir / "_index.json"
    if index_file.exists():
        result["index"] = json.loads(index_file.read_text())

    return result if result["overview"] or result["conventions"] else None


def add_feature(
    description: str,
    target_program: Optional[str] = None,
    feature_name: Optional[str] = None,
    reference: Optional[str] = None,
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

        # Handle reference-based feature addition
        if reference and target_program:
            result["mode"] = "reference"
            result["target_program"] = target_program
            result["feature_name"] = feature_name or description.lower().replace(" ", "-")[:30]

            # Parse reference (source_program/section)
            if "/" not in reference:
                result["error"] = "Reference format: <source-program>/<section>"
                if output_json:
                    print(json.dumps(result, indent=2, default=str))
                return result

            ref_parts = reference.split("/", 1)
            source_program = ref_parts[0]
            source_section = ref_parts[1]
            result["reference"] = {
                "program": source_program,
                "section": source_section
            }

            # Load source behavior spec
            behavior = load_behavior_spec(source_program, source_section, project_path)
            if behavior:
                result["source_behavior"] = behavior
            else:
                result["warning"] = f"No behavior spec found for {reference}. Create with: /coder:blueprint add {source_program} {source_section} --extract-behavior"

            # Load target conventions
            target_conv = load_target_conventions(target_program, project_path)
            if target_conv:
                result["target_conventions"] = target_conv
            else:
                result["warning"] = (result.get("warning", "") +
                    f" No blueprint found for target {target_program}. Create with: /coder:blueprint add {target_program} overview").strip()

            # Create feature spec with reference
            feature_dir = planning_dir / "features"
            feature_dir.mkdir(exist_ok=True)

            feature_slug = result["feature_name"]
            feature_file = feature_dir / f"{target_program}-{feature_slug}.md"

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            feature_content = f"""---
feature: {description}
target_program: {target_program}
feature_name: {feature_slug}
reference_source: {reference}
created: {today}
mode: reference-port
---

# Feature: {description}

## Reference
Porting behavior from: **{reference}**

## Target Program
Implementing in: **{target_program}**

## Source Behavior
"""
            if behavior:
                feature_content += f"""
The behavior spec from {reference} defines:
- See: {behavior['file']}
- Load with: `/coder:blueprint load {reference} --behavior`

"""
            else:
                feature_content += f"""
> No behavior spec found. Extract it first:
> `/coder:blueprint add {source_program} {source_section} --extract-behavior`

"""

            feature_content += f"""
## Target Conventions
"""
            if target_conv and target_conv.get("overview"):
                feature_content += f"""
The target program {target_program} has conventions defined:
- See overview for patterns, language, frameworks

"""
            else:
                feature_content += f"""
> No blueprint found for target. Create it:
> `/coder:blueprint add {target_program} overview "<description>"`

"""

            feature_content += f"""
## Implementation Plan

1. **Load source behavior**: `/coder:blueprint load {reference} --behavior`
2. **Load target conventions**: `/coder:blueprint load {target_program}/overview`
3. **Plan implementation** in target's style using source's behavior
4. **Create files** following target's patterns

## Key Decisions
- [ ] Language/framework choices aligned with target
- [ ] API design matches target conventions
- [ ] Error handling follows target patterns
- [ ] Testing approach per target norms

## Files to Create
<!-- List files in target's structure -->

## Notes
<!-- Implementation notes, gotchas from porting -->
"""
            feature_file.write_text(feature_content)
            result["feature_file"] = str(feature_file)

            result["message"] = f"Reference feature created: {target_program}/{feature_slug}"
            result["next_steps"] = [
                f"Load source behavior: /coder:blueprint load {reference} --behavior",
                f"Load target conventions: /coder:blueprint load {target_program}/overview",
                "Plan implementation in target's style",
                f"Run /coder:plan-phase for the feature"
            ]

        else:
            # Standard feature addition (existing logic)
            result["mode"] = "standard"

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
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            feature_content = f"""---
feature: {description}
branch: {branch_name}
created: {today}
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

    # Check for --reference flag (new mode)
    reference = None
    if "--reference" in sys.argv:
        idx = sys.argv.index("--reference")
        if idx + 1 < len(sys.argv):
            reference = sys.argv[idx + 1]

    # Filter args
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # Remove reference value from args if present
    if reference and reference in args:
        args.remove(reference)

    if not args:
        print(json.dumps({
            "error": "Feature description required",
            "usage": {
                "standard": "add_feature <description>",
                "reference": 'add_feature <target-program> <feature-name> "<description>" --reference <source>/<section>'
            },
            "examples": {
                "standard": 'add_feature "Add user authentication"',
                "reference": 'add_feature eritrainer sana "Sana model training" --reference onetrainer/models/sana'
            }
        }, indent=2))
        sys.exit(1)

    if reference:
        # Reference mode: target_program feature_name description
        if len(args) < 3:
            print(json.dumps({
                "error": "Reference mode requires: <target-program> <feature-name> <description>",
                "example": 'add_feature eritrainer sana "Sana model training" --reference onetrainer/models/sana'
            }, indent=2))
            sys.exit(1)

        target_program = args[0]
        feature_name = args[1]
        description = " ".join(args[2:])

        add_feature(
            description,
            target_program=target_program,
            feature_name=feature_name,
            reference=reference,
            output_json=output_json
        )
    else:
        # Standard mode
        description = " ".join(args)
        add_feature(description, output_json=output_json)


if __name__ == "__main__":
    main()
