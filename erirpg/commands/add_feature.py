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
        "overview": None,
        "architecture_pattern": None
    }

    # Try to load overview
    overview_file = program_dir / "overview.md"
    if overview_file.exists():
        result["overview"] = overview_file.read_text()

    # Try to load conventions if separate
    conventions_file = program_dir / "conventions.md"
    if conventions_file.exists():
        result["conventions"] = conventions_file.read_text()

    # Try to load architecture
    arch_file = program_dir / "architecture.md"
    if arch_file.exists():
        result["architecture"] = arch_file.read_text()

    # Load index for metadata
    index_file = program_dir / "_index.json"
    if index_file.exists():
        result["index"] = json.loads(index_file.read_text())

    # Detect architecture pattern from content
    result["architecture_pattern"] = detect_architecture_pattern(result)

    return result if result["overview"] or result["conventions"] else None


def detect_architecture_pattern(target_info: dict) -> Optional[dict]:
    """Detect architecture pattern from target blueprints."""
    content = ""
    if target_info.get("overview"):
        content += target_info["overview"].lower()
    if target_info.get("architecture"):
        content += target_info["architecture"].lower()
    if target_info.get("conventions"):
        content += target_info["conventions"].lower()

    patterns = {
        "hexagonal": ["hexagonal", "ports and adapters", "port", "adapter", "domain"],
        "layered": ["layer", "service layer", "data layer", "presentation layer"],
        "mvc": ["model", "view", "controller", "mvc"],
        "clean": ["clean architecture", "use case", "entity", "interface adapter"],
        "modular": ["module", "plugin", "extension"],
        "microservices": ["microservice", "service mesh", "api gateway"],
        "event-driven": ["event", "message", "queue", "subscriber", "publisher"],
    }

    detected = None
    max_score = 0

    for pattern_name, keywords in patterns.items():
        score = sum(1 for kw in keywords if kw in content)
        if score > max_score:
            max_score = score
            detected = pattern_name

    if detected:
        layer_mapping = {
            "hexagonal": {"domain": "Core logic", "ports": "Interfaces", "adapters": "Implementations"},
            "layered": {"domain": "Business logic", "service": "Orchestration", "data": "Persistence"},
            "mvc": {"model": "Data/logic", "view": "Presentation", "controller": "Input handling"},
            "clean": {"entities": "Business objects", "use_cases": "Application logic", "adapters": "External"},
            "modular": {"core": "Shared logic", "modules": "Features", "plugins": "Extensions"},
        }
        return {
            "pattern": detected,
            "confidence": min(max_score / 3, 1.0),
            "layers": layer_mapping.get(detected, {"core": "Core", "adapters": "Adapters"})
        }

    return None


def parse_behavior_dependencies(behavior_content: str) -> dict:
    """Extract dependencies from behavior spec."""
    result = {
        "hard": [],
        "soft": [],
        "environment": []
    }

    lines = behavior_content.split("\n")
    current_section = None

    for line in lines:
        line_lower = line.lower().strip()
        if "hard dependencies" in line_lower:
            current_section = "hard"
        elif "soft dependencies" in line_lower:
            current_section = "soft"
        elif "environment" in line_lower and "##" in line:
            current_section = "environment"
        elif line.startswith("- ") and current_section:
            dep = line[2:].strip()
            if dep and not dep.startswith("["):
                result[current_section].append(dep)

    return result


def parse_resource_budget(behavior_content: str) -> dict:
    """Extract resource budget from behavior spec."""
    result = {
        "memory": {},
        "time": {},
        "constraints": []
    }

    lines = behavior_content.split("\n")
    current_section = None

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        if "## resource budget" in line_lower:
            current_section = "budget"
        elif "### memory" in line_lower:
            current_section = "memory"
        elif "### time" in line_lower:
            current_section = "time"
        elif "### constraints" in line_lower:
            current_section = "constraints"
        elif current_section == "memory" and "**" in line:
            if "vram" in line_lower:
                result["memory"]["vram"] = line.split(":")[-1].strip() if ":" in line else ""
            elif "ram" in line_lower:
                result["memory"]["ram"] = line.split(":")[-1].strip() if ":" in line else ""
        elif current_section == "time" and "**" in line:
            if "init" in line_lower:
                result["time"]["init"] = line.split(":")[-1].strip() if ":" in line else ""
            elif "per" in line_lower:
                result["time"]["per_op"] = line.split(":")[-1].strip() if ":" in line else ""
        elif current_section == "constraints" and line.startswith("- "):
            constraint = line[2:].strip()
            if constraint and not constraint.startswith("["):
                result["constraints"].append(constraint)

    return result


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

            # Parse behavior spec for dependencies and resources
            behavior_deps = None
            resource_budget = None
            if behavior:
                behavior_deps = parse_behavior_dependencies(behavior["content"])
                resource_budget = parse_resource_budget(behavior["content"])
                result["source_dependencies"] = behavior_deps
                result["source_resources"] = resource_budget

            # Detect architecture pattern
            arch_pattern = None
            if target_conv:
                arch_pattern = target_conv.get("architecture_pattern")
                if arch_pattern:
                    result["target_architecture"] = arch_pattern

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

            # Add architectural gravity section
            feature_content += """
## Architectural Gravity

"""
            if arch_pattern:
                feature_content += f"""
**Detected Pattern:** {arch_pattern['pattern'].title()} (confidence: {arch_pattern['confidence']:.0%})

**Layer Mapping:**
"""
                for layer, desc in arch_pattern.get('layers', {}).items():
                    feature_content += f"- **{layer}:** {desc}\n"

                feature_content += f"""

**Implementation Strategy:**
1. Map behavior to DOMAIN layer first (pure logic, no framework deps)
2. Create ADAPTERS for framework-specific code
3. Never leak framework into domain

**Example Structure:**
```
Behavior: "{description}"
Domain:   {feature_slug.title().replace('-', '')}Trait with core methods
Adapter:  Framework{feature_slug.title().replace('-', '')} implements trait
```
"""
            else:
                feature_content += """
> Architecture pattern not detected. Analyze target blueprint.
> Default approach: Domain layer (pure logic) + Adapters (framework-specific)
"""

            # Add dependency mapping section
            feature_content += """
## Dependency Mapping

"""
            if behavior_deps:
                if behavior_deps.get("hard"):
                    feature_content += "### Hard Dependencies (must satisfy)\n"
                    for dep in behavior_deps["hard"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"

                if behavior_deps.get("soft"):
                    feature_content += "### Soft Dependencies (interface required)\n"
                    for dep in behavior_deps["soft"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"

                if behavior_deps.get("environment"):
                    feature_content += "### Environment Requirements\n"
                    for dep in behavior_deps["environment"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"
            else:
                feature_content += "> Dependencies not specified in behavior spec. Review source manually.\n\n"

            # Add resource budget section
            feature_content += """
## Resource Budget

"""
            if resource_budget:
                if resource_budget.get("memory"):
                    feature_content += "### Memory\n"
                    for key, val in resource_budget["memory"].items():
                        if val:
                            feature_content += f"- **{key.upper()}:** {val}\n"
                    feature_content += "\n"

                if resource_budget.get("time"):
                    feature_content += "### Time\n"
                    for key, val in resource_budget["time"].items():
                        if val:
                            feature_content += f"- **{key}:** {val}\n"
                    feature_content += "\n"

                if resource_budget.get("constraints"):
                    feature_content += "### Constraints\n"
                    for constraint in resource_budget["constraints"]:
                        feature_content += f"- {constraint}\n"
                    feature_content += "\n"

                feature_content += """
**Target Compatibility:**
- [ ] Can meet memory requirements
- [ ] Can meet time requirements
- [ ] All constraints acknowledged

"""
            else:
                feature_content += "> Resource budget not specified in behavior spec.\n\n"

            feature_content += f"""
## Implementation Plan

1. **Load source behavior**: `/coder:blueprint load {reference} --behavior`
2. **Load target conventions**: `/coder:blueprint load {target_program}/overview`
3. **Satisfy dependencies** - stub or implement each requirement
4. **Map to domain layer** - pure logic, no framework
5. **Create adapters** - framework-specific implementations
6. **Verify resource budget** - test against constraints

## Key Decisions
- [ ] Language/framework choices aligned with target
- [ ] API design matches target conventions
- [ ] Error handling follows target patterns
- [ ] Testing approach per target norms
- [ ] State machine preserved from source

## Files to Create
<!-- List files in target's structure, organized by layer -->

### Domain Layer
- `src/domain/{feature_slug}.rs` (or appropriate extension)

### Adapters
- `src/adapters/{feature_slug}_impl.rs`

### Tests
- `tests/{feature_slug}_test.rs`

## Notes
<!-- Implementation notes, gotchas from porting -->
"""
            feature_file.write_text(feature_content)
            result["feature_file"] = str(feature_file)

            result["message"] = f"Reference feature created: {target_program}/{feature_slug}"
            result["next_steps"] = [
                f"Load source behavior: /coder:blueprint load {reference} --behavior",
                f"Load target conventions: /coder:blueprint load {target_program}/overview",
                "Review dependency mapping and satisfy requirements",
                "Verify resource budget compatibility",
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
