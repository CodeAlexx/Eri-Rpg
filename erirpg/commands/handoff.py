#!/usr/bin/env python3
"""
/coder:handoff - Generate context documentation.

Creates comprehensive handoff documentation including:
- Current state
- Key decisions
- Architecture overview
- Next steps

Usage:
    python -m erirpg.commands.handoff [--json]
    python -m erirpg.commands.handoff --output <file> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.docs import generate_handoff_document
from erirpg.coder.state import load_project_state


def handoff(
    output_file: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Generate handoff documentation."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "handoff",
        "project": str(project_path),
    }

    try:
        # Generate handoff document
        handoff_content = generate_handoff_document(project_path)
        result["content"] = handoff_content

        # Save if output file specified
        if output_file:
            output_path = Path(output_file)
            if not output_path.is_absolute():
                output_path = project_path / output_file
            output_path.write_text(handoff_content)
            result["output_file"] = str(output_path)
            result["message"] = f"Handoff document written to {output_path}"
        else:
            # Default location
            planning_dir = project_path / ".planning"
            planning_dir.mkdir(parents=True, exist_ok=True)
            default_path = planning_dir / "HANDOFF.md"
            default_path.write_text(handoff_content)
            result["output_file"] = str(default_path)
            result["message"] = f"Handoff document written to {default_path}"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --output argument
    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    handoff(output_file=output_file, output_json=output_json)


if __name__ == "__main__":
    main()
