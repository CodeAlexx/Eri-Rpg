#!/usr/bin/env python3
"""
/coder:map-codebase - Analyze existing codebase (brownfield).

Creates:
- STACK.md - Technology stack
- ARCHITECTURE.md - System architecture
- CONVENTIONS.md - Code conventions
- CONCERNS.md - Technical concerns

Usage:
    python -m erirpg.commands.map_codebase [--json]
    python -m erirpg.commands.map_codebase --path <dir> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir


def map_codebase(
    target_path: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Map an existing codebase."""
    if project_path is None:
        project_path = Path.cwd()

    if target_path:
        scan_path = Path(target_path)
        if not scan_path.is_absolute():
            scan_path = project_path / target_path
    else:
        scan_path = project_path

    result = {
        "command": "map-codebase",
        "project": str(project_path),
        "scan_path": str(scan_path),
    }

    try:
        planning_dir = ensure_planning_dir(project_path)
        codebase_dir = planning_dir / "codebase"
        codebase_dir.mkdir(exist_ok=True)

        # Create STACK.md
        stack_path = codebase_dir / "STACK.md"
        stack_content = f"""---
scanned: {datetime.utcnow().isoformat()}Z
path: {scan_path}
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

## Runtime
- [Runtime environment]
"""
        stack_path.write_text(stack_content)
        result["stack_file"] = str(stack_path)

        # Create ARCHITECTURE.md
        arch_path = codebase_dir / "ARCHITECTURE.md"
        arch_content = f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Architecture

## Directory Structure
```
[Directory tree]
```

## Components
- [Main components]

## Data Flow
- [How data flows through the system]

## Entry Points
- [Main entry points]

## External Integrations
- [External services/APIs]
"""
        arch_path.write_text(arch_content)
        result["architecture_file"] = str(arch_path)

        # Create CONVENTIONS.md
        conv_path = codebase_dir / "CONVENTIONS.md"
        conv_content = f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Code Conventions

## Naming Conventions
- Files: [Convention]
- Functions: [Convention]
- Variables: [Convention]
- Classes: [Convention]

## File Organization
- [How files are organized]

## Patterns Used
- [Common patterns]

## Testing Approach
- [Testing conventions]
"""
        conv_path.write_text(conv_content)
        result["conventions_file"] = str(conv_path)

        # Create CONCERNS.md
        concerns_path = codebase_dir / "CONCERNS.md"
        concerns_content = f"""---
scanned: {datetime.utcnow().isoformat()}Z
---

# Technical Concerns

## Identified Issues
- [Technical debt]
- [Code smells]
- [Security concerns]

## Risks
- [Potential risks]

## Recommendations
- [Improvement suggestions]
"""
        concerns_path.write_text(concerns_content)
        result["concerns_file"] = str(concerns_path)

        result["status"] = "mapped"
        result["message"] = "Codebase analysis files created. Fill in details."
        result["next_steps"] = [
            "Review and complete STACK.md",
            "Review and complete ARCHITECTURE.md",
            "Review and complete CONVENTIONS.md",
            "Review and complete CONCERNS.md",
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

    # Parse --path argument
    target_path = None
    if "--path" in sys.argv:
        idx = sys.argv.index("--path")
        if idx + 1 < len(sys.argv):
            target_path = sys.argv[idx + 1]

    map_codebase(target_path=target_path, output_json=output_json)


if __name__ == "__main__":
    main()
