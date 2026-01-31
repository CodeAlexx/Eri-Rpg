#!/usr/bin/env python3
"""
/coder:map-codebase - Analyze existing codebase (brownfield).

Usage:
    python -m erirpg.commands.map_codebase [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir


def map_codebase(
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Map an existing codebase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "map-codebase",
        "project": str(project_path),
    }

    try:
        planning_dir = ensure_planning_dir(project_path)
        codebase_dir = planning_dir / "codebase"
        codebase_dir.mkdir(exist_ok=True)

        files_created = []

        # Create STACK.md
        stack_path = codebase_dir / "STACK.md"
        if not stack_path.exists():
            stack_path.write_text(f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Technology Stack

## Languages
- [Detected languages]

## Frameworks
- [Detected frameworks]

## Build Tools
- [Build system]

## Dependencies
- [Key dependencies]
""")
            files_created.append("STACK.md")

        # Create ARCHITECTURE.md
        arch_path = codebase_dir / "ARCHITECTURE.md"
        if not arch_path.exists():
            arch_path.write_text(f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Architecture

## Directory Structure
[Directory tree]

## Components
- [Main components]

## Data Flow
- [How data flows]
""")
            files_created.append("ARCHITECTURE.md")

        # Create CONVENTIONS.md
        conv_path = codebase_dir / "CONVENTIONS.md"
        if not conv_path.exists():
            conv_path.write_text(f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Code Conventions

## Naming Conventions
- Files: [Convention]
- Functions: [Convention]

## Patterns Used
- [Common patterns]
""")
            files_created.append("CONVENTIONS.md")

        result["codebase_dir"] = str(codebase_dir)
        result["files_created"] = files_created
        result["message"] = "Codebase analysis files created"
        result["next_steps"] = [
            "Review and complete analysis files",
            "Run /coder:add-feature to add new features"
        ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    map_codebase(output_json=output_json)


if __name__ == "__main__":
    main()
