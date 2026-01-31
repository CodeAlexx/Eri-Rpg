#!/usr/bin/env python3
"""
/coder:blueprint - Manage section-level blueprints of complex programs.

Usage:
    python -m erirpg.commands.blueprint list [--json]
    python -m erirpg.commands.blueprint add <program> <section> "<description>" [--path <path>] [--json]
    python -m erirpg.commands.blueprint load <program>/<section> [--json]
    python -m erirpg.commands.blueprint status <program> [--json]
    python -m erirpg.commands.blueprint update <program>/<section> [--json]
    python -m erirpg.commands.blueprint deps <program> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from erirpg.coder import ensure_planning_dir


def get_blueprints_dir(project_path: Optional[Path] = None) -> Path:
    """Get or create blueprints directory."""
    if project_path is None:
        project_path = Path.cwd()
    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    blueprints_dir.mkdir(exist_ok=True)
    return blueprints_dir


def get_manifest_path(project_path: Optional[Path] = None) -> Path:
    """Get path to MANIFEST.md."""
    return get_blueprints_dir(project_path) / "MANIFEST.md"


def get_program_dir(program: str, project_path: Optional[Path] = None) -> Path:
    """Get or create program directory."""
    program_dir = get_blueprints_dir(project_path) / program
    program_dir.mkdir(exist_ok=True)
    return program_dir


def get_index_path(program: str, project_path: Optional[Path] = None) -> Path:
    """Get path to program's _index.json."""
    return get_program_dir(program, project_path) / "_index.json"


def load_index(program: str, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load program index, create if missing."""
    index_path = get_index_path(program, project_path)
    if index_path.exists():
        return json.loads(index_path.read_text())
    return {
        "program": program,
        "path": None,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sections": []
    }


def save_index(program: str, index: Dict[str, Any], project_path: Optional[Path] = None):
    """Save program index."""
    index_path = get_index_path(program, project_path)
    index_path.write_text(json.dumps(index, indent=2))


def load_manifest(project_path: Optional[Path] = None) -> str:
    """Load MANIFEST.md content."""
    manifest_path = get_manifest_path(project_path)
    if manifest_path.exists():
        return manifest_path.read_text()
    return "# Blueprints\n\n"


def regenerate_manifest(project_path: Optional[Path] = None):
    """Regenerate MANIFEST.md from all program indexes."""
    blueprints_dir = get_blueprints_dir(project_path)
    manifest_path = get_manifest_path(project_path)

    lines = ["# Blueprints\n"]

    # Find all program directories
    programs = sorted([d for d in blueprints_dir.iterdir() if d.is_dir()])

    for program_dir in programs:
        program = program_dir.name
        index_path = program_dir / "_index.json"

        if not index_path.exists():
            continue

        index = json.loads(index_path.read_text())
        sections = index.get("sections", [])

        if not sections:
            continue

        lines.append(f"\n## {program.title()}\n")
        lines.append("| Section | Status | Last Updated | Dependencies |")
        lines.append("|---------|--------|--------------|--------------|")

        status_icons = {
            "complete": "✅ complete",
            "in_progress": "🔄 in_progress",
            "not_started": "❌ not_started",
            "outdated": "⚠️ outdated"
        }

        for section in sections:
            name = section.get("name", "unknown")
            status = status_icons.get(section.get("status", "not_started"), "❓ unknown")
            updated = section.get("updated", "-")
            deps = section.get("depends_on", [])
            deps_str = ", ".join(deps) if deps else "-"
            lines.append(f"| {name} | {status} | {updated} | {deps_str} |")

        lines.append("")

    manifest_path.write_text("\n".join(lines))


def blueprint_list(project_path: Optional[Path] = None, output_json: bool = False) -> dict:
    """List all blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "list",
        "project": str(project_path),
    }

    try:
        blueprints_dir = get_blueprints_dir(project_path)
        programs = []

        for program_dir in sorted(blueprints_dir.iterdir()):
            if not program_dir.is_dir():
                continue

            index_path = program_dir / "_index.json"
            if index_path.exists():
                index = json.loads(index_path.read_text())
                programs.append({
                    "program": program_dir.name,
                    "sections": len(index.get("sections", [])),
                    "path": index.get("path"),
                    "created": index.get("created")
                })

        result["programs"] = programs
        result["manifest"] = load_manifest(project_path)
        result["manifest_path"] = str(get_manifest_path(project_path))

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def blueprint_add(
    program: str,
    section: str,
    description: str,
    source_path: Optional[str] = None,
    depends_on: Optional[List[str]] = None,
    extract_behavior: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a new blueprint section."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "add",
        "project": str(project_path),
        "program": program,
        "section": section,
    }

    try:
        program_dir = get_program_dir(program, project_path)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Handle nested sections (e.g., models/flux)
        if "/" in section:
            parts = section.split("/")
            section_dir = program_dir
            for part in parts[:-1]:
                section_dir = section_dir / part
                section_dir.mkdir(exist_ok=True)
            section_file = section_dir / f"{parts[-1]}.md"
            behavior_file = section_dir / f"{parts[-1]}-BEHAVIOR.md"
            section_name = section
        else:
            section_file = program_dir / f"{section}.md"
            behavior_file = program_dir / f"{section}-BEHAVIOR.md"
            section_name = section

        # Create blueprint file
        blueprint_content = f"""---
program: {program}
section: {section_name}
description: {description}
source_path: {source_path or 'N/A'}
created: {today}
updated: {today}
status: not_started
has_behavior: {str(extract_behavior).lower()}
---

# {section_name.replace('/', ' / ').title()}

## Description
{description}

## Source Path
{source_path or 'Not specified - run codebase mapper to analyze'}

## Architecture
<!-- High-level structure of this section -->

## Key Components
<!-- Main classes, functions, modules -->

## Data Flow
<!-- How data moves through this section -->

## Dependencies
<!-- What this section depends on -->
{chr(10).join(f"- {d}" for d in (depends_on or [])) or '- None specified'}

## Integration Points
<!-- How this section connects to others -->

## Notes
<!-- Implementation notes, gotchas, patterns -->
"""
        section_file.write_text(blueprint_content)
        result["blueprint_file"] = str(section_file)

        # Create behavior file if requested
        if extract_behavior:
            behavior_content = f"""---
program: {program}
section: {section_name}
type: behavior-spec
portable: true
created: {today}
updated: {today}
---

# {section_name.replace('/', ' / ').title()} - Behavior Spec

> Portable behavior specification. Describes WHAT this does, not HOW it's coded.
> Use this to implement equivalent functionality in different languages/frameworks.

## Purpose
<!-- What this feature accomplishes for the user -->
{description}

## Inputs
<!-- What data/config it accepts -->
- **Required inputs:**
  - [Input 1]: [format, constraints]
- **Optional inputs:**
  - [Input 2]: [format, default value]
- **Configuration:**
  - [Config option]: [description]

## Outputs
<!-- What it produces -->
- **Primary output:**
  - [Output description]
- **Side effects:**
  - [Files created, state changes]
- **Artifacts:**
  - [Logs, checkpoints, etc.]

## Behavior
<!-- Step by step what happens (user perspective, not code) -->
1. [First thing that happens]
2. [Second thing that happens]
3. [Result user sees]

## Constraints
<!-- Non-functional requirements -->
- **Memory:** [limits, requirements]
- **Performance:** [speed expectations]
- **Dependencies:** [what other features must exist]

## User-Facing
<!-- How users interact with this -->
- **CLI commands:**
  - `command --flag`: [what it does]
- **Config options:**
  - `option_name`: [effect]
- **Output files:**
  - `path/to/output`: [contents]

## Edge Cases
<!-- What happens in unusual situations -->
- **When [condition X]:** [behavior]
- **Error handling:** [what user sees on failure]
- **Recovery:** [how to resume/retry]

## Examples
<!-- Concrete usage examples -->
```
# Example 1: Basic usage
[command or config]

# Example 2: Advanced usage
[command or config]
```
"""
            behavior_file.write_text(behavior_content)
            result["behavior_file"] = str(behavior_file)
            result["extract_behavior"] = True

        # Update index
        index = load_index(program, project_path)

        # Check if section already exists
        existing = next((s for s in index["sections"] if s["name"] == section_name), None)
        if existing:
            existing["updated"] = today
            existing["status"] = "not_started"
            if depends_on:
                existing["depends_on"] = depends_on
            existing["has_behavior"] = extract_behavior
        else:
            index["sections"].append({
                "name": section_name,
                "path": str(section_file.relative_to(program_dir)),
                "status": "not_started",
                "depends_on": depends_on or [],
                "updated": today,
                "description": description,
                "has_behavior": extract_behavior
            })

        if source_path:
            index["path"] = source_path

        save_index(program, index, project_path)
        result["index_updated"] = True

        # Regenerate manifest
        regenerate_manifest(project_path)
        result["manifest_updated"] = True

        result["message"] = f"Blueprint created: {program}/{section_name}"
        next_steps = [
            f"Run codebase mapper on section: Task agent to analyze {source_path or 'source'}",
            f"Load blueprint: /coder:blueprint load {program}/{section_name}",
            f"Update status when complete: /coder:blueprint update {program}/{section_name}"
        ]
        if extract_behavior:
            next_steps.insert(1, f"Run behavior extractor: Task agent with eri-behavior-extractor on {source_path or 'source'}")
        result["next_steps"] = next_steps

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def blueprint_load(
    program_section: str,
    behavior_only: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Load a blueprint into context."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "load",
        "project": str(project_path),
        "target": program_section,
    }

    try:
        if "/" not in program_section:
            result["error"] = "Format: <program>/<section>"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        parts = program_section.split("/", 1)
        program = parts[0]
        section = parts[1]

        program_dir = get_program_dir(program, project_path)

        # Find the blueprint file
        if "/" in section:
            # Nested section
            section_parts = section.split("/")
            section_file = program_dir
            for part in section_parts[:-1]:
                section_file = section_file / part
            section_file = section_file / f"{section_parts[-1]}.md"
            behavior_file = section_file.parent / f"{section_parts[-1]}-BEHAVIOR.md"
        else:
            section_file = program_dir / f"{section}.md"
            behavior_file = program_dir / f"{section}-BEHAVIOR.md"

        if not section_file.exists():
            result["error"] = f"Blueprint not found: {section_file}"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        # Load blueprint content (unless behavior_only)
        if not behavior_only:
            content = section_file.read_text()
            result["content"] = content
            result["file"] = str(section_file)

        # Load behavior spec if it exists
        if behavior_file.exists():
            result["behavior_content"] = behavior_file.read_text()
            result["behavior_file"] = str(behavior_file)
            result["has_behavior"] = True
        else:
            result["has_behavior"] = False

        # If behavior_only but no behavior file
        if behavior_only and not behavior_file.exists():
            result["error"] = f"Behavior spec not found: {behavior_file}"
            result["hint"] = "Create with: blueprint add --extract-behavior"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        # Load index for dependency info
        index = load_index(program, project_path)
        section_info = next((s for s in index["sections"] if s["name"] == section), None)

        if section_info:
            result["section_info"] = section_info

            # Load dependencies if any (skip for behavior_only)
            if not behavior_only:
                deps = section_info.get("depends_on", [])
                if deps:
                    result["dependencies"] = []
                    for dep in deps:
                        dep_file = program_dir / f"{dep}.md"
                        if dep_file.exists():
                            result["dependencies"].append({
                                "name": dep,
                                "file": str(dep_file),
                                "content": dep_file.read_text()
                            })

        result["message"] = f"Loaded {'behavior spec' if behavior_only else 'blueprint'}: {program_section}"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def blueprint_status(
    program: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Show blueprint status for a program."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "status",
        "project": str(project_path),
        "program": program,
    }

    try:
        index = load_index(program, project_path)
        sections = index.get("sections", [])

        # Categorize sections
        complete = [s for s in sections if s.get("status") == "complete"]
        in_progress = [s for s in sections if s.get("status") == "in_progress"]
        not_started = [s for s in sections if s.get("status") == "not_started"]
        outdated = [s for s in sections if s.get("status") == "outdated"]

        result["summary"] = {
            "total": len(sections),
            "complete": len(complete),
            "in_progress": len(in_progress),
            "not_started": len(not_started),
            "outdated": len(outdated)
        }

        result["sections"] = {
            "complete": [s["name"] for s in complete],
            "in_progress": [s["name"] for s in in_progress],
            "not_started": [s["name"] for s in not_started],
            "outdated": [s["name"] for s in outdated]
        }

        # Suggest next sections
        suggestions = []
        for section in not_started:
            deps = section.get("depends_on", [])
            deps_met = all(
                any(s["name"] == d and s.get("status") == "complete" for s in sections)
                for d in deps
            ) if deps else True

            if deps_met:
                suggestions.append({
                    "section": section["name"],
                    "reason": "Dependencies satisfied" if deps else "No dependencies"
                })

        result["suggested_next"] = suggestions[:3]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def blueprint_update(
    program_section: str,
    new_status: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Update a blueprint section."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "update",
        "project": str(project_path),
        "target": program_section,
    }

    try:
        if "/" not in program_section:
            result["error"] = "Format: <program>/<section>"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        parts = program_section.split("/", 1)
        program = parts[0]
        section = parts[1]

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Update index
        index = load_index(program, project_path)
        section_info = next((s for s in index["sections"] if s["name"] == section), None)

        if not section_info:
            result["error"] = f"Section not found: {section}"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        section_info["updated"] = today
        if new_status:
            section_info["status"] = new_status

        save_index(program, index, project_path)
        result["index_updated"] = True

        # Regenerate manifest
        regenerate_manifest(project_path)
        result["manifest_updated"] = True

        result["section"] = section_info
        result["message"] = f"Updated: {program_section}"

        if new_status:
            result["new_status"] = new_status

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def blueprint_deps(
    program: str,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Show dependency graph for a program."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "blueprint",
        "subcommand": "deps",
        "project": str(project_path),
        "program": program,
    }

    try:
        index = load_index(program, project_path)
        sections = index.get("sections", [])

        # Build dependency graph
        graph = {}
        reverse_graph = {}  # What depends on this

        for section in sections:
            name = section["name"]
            deps = section.get("depends_on", [])
            graph[name] = deps

            for dep in deps:
                if dep not in reverse_graph:
                    reverse_graph[dep] = []
                reverse_graph[dep].append(name)

        result["dependencies"] = graph
        result["dependents"] = reverse_graph

        # Find root sections (no dependencies)
        roots = [name for name, deps in graph.items() if not deps]
        result["roots"] = roots

        # Find leaf sections (nothing depends on them)
        all_names = set(graph.keys())
        has_dependents = set(reverse_graph.keys())
        leaves = list(all_names - has_dependents)
        result["leaves"] = leaves

        # Suggest loading order (topological sort)
        visited = set()
        order = []

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            for dep in graph.get(name, []):
                visit(dep)
            order.append(name)

        for name in graph:
            visit(name)

        result["load_order"] = order

        # Generate ASCII graph
        lines = ["Dependency Graph:", ""]
        for root in roots:
            lines.append(f"  {root}")
            for dep_name in reverse_graph.get(root, []):
                lines.append(f"    └── {dep_name}")
                for sub_dep in reverse_graph.get(dep_name, []):
                    lines.append(f"        └── {sub_dep}")

        result["graph_ascii"] = "\n".join(lines)

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
            "error": "Subcommand required",
            "usage": {
                "list": "blueprint list",
                "add": "blueprint add <program> <section> <description> [--path <path>]",
                "load": "blueprint load <program>/<section>",
                "status": "blueprint status <program>",
                "update": "blueprint update <program>/<section> [--status <status>]",
                "deps": "blueprint deps <program>"
            }
        }, indent=2))
        sys.exit(1)

    subcommand = args[0]

    if subcommand == "list":
        blueprint_list(output_json=output_json)

    elif subcommand == "add":
        if len(args) < 4:
            print(json.dumps({
                "error": "Usage: blueprint add <program> <section> <description>",
                "example": 'blueprint add onetrainer training-pipeline "Core training loop"'
            }, indent=2))
            sys.exit(1)

        program = args[1]
        section = args[2]

        # Filter out flag values from description
        desc_args = []
        skip_next = False
        for i, arg in enumerate(args[3:]):
            if skip_next:
                skip_next = False
                continue
            if arg in ["--path", "--depends"]:
                skip_next = True
                continue
            desc_args.append(arg)
        description = " ".join(desc_args)

        # Check for --path
        source_path = None
        if "--path" in sys.argv:
            idx = sys.argv.index("--path")
            if idx + 1 < len(sys.argv):
                source_path = sys.argv[idx + 1]

        # Check for --depends
        depends_on = None
        if "--depends" in sys.argv:
            idx = sys.argv.index("--depends")
            if idx + 1 < len(sys.argv):
                depends_on = sys.argv[idx + 1].split(",")

        # Check for --extract-behavior
        extract_behavior = "--extract-behavior" in sys.argv

        blueprint_add(program, section, description, source_path=source_path,
                     depends_on=depends_on, extract_behavior=extract_behavior,
                     output_json=output_json)

    elif subcommand == "load":
        if len(args) < 2:
            print(json.dumps({
                "error": "Usage: blueprint load <program>/<section>",
                "example": "blueprint load onetrainer/training-pipeline"
            }, indent=2))
            sys.exit(1)

        behavior_only = "--behavior" in sys.argv or "--behavior-only" in sys.argv
        blueprint_load(args[1], behavior_only=behavior_only, output_json=output_json)

    elif subcommand == "status":
        if len(args) < 2:
            print(json.dumps({
                "error": "Usage: blueprint status <program>",
                "example": "blueprint status onetrainer"
            }, indent=2))
            sys.exit(1)

        blueprint_status(args[1], output_json=output_json)

    elif subcommand == "update":
        if len(args) < 2:
            print(json.dumps({
                "error": "Usage: blueprint update <program>/<section>",
                "example": "blueprint update onetrainer/training-pipeline"
            }, indent=2))
            sys.exit(1)

        new_status = None
        if "--status" in sys.argv:
            idx = sys.argv.index("--status")
            if idx + 1 < len(sys.argv):
                new_status = sys.argv[idx + 1]

        blueprint_update(args[1], new_status=new_status, output_json=output_json)

    elif subcommand == "deps":
        if len(args) < 2:
            print(json.dumps({
                "error": "Usage: blueprint deps <program>",
                "example": "blueprint deps onetrainer"
            }, indent=2))
            sys.exit(1)

        blueprint_deps(args[1], output_json=output_json)

    else:
        print(json.dumps({
            "error": f"Unknown subcommand: {subcommand}",
            "valid": ["list", "add", "load", "status", "update", "deps"]
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
