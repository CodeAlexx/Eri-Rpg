#!/usr/bin/env python3
"""
/coder:handoff - Generate context documentation.

Usage:
    python -m erirpg.commands.handoff [--json]
    python -m erirpg.commands.handoff --output <file> [--json]
    python -m erirpg.commands.handoff --format human|ai [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.docs import generate_handoff
from erirpg.coder import ensure_planning_dir


def handoff(
    output_file: Optional[str] = None,
    format_type: str = "human",
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Generate handoff documentation."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "handoff",
        "project": str(project_path),
        "format": format_type,
    }

    try:
        handoff_content = generate_handoff(project_path, format_type)
        result["content"] = handoff_content

        # Save to file
        if output_file:
            output_path = Path(output_file)
            if not output_path.is_absolute():
                output_path = project_path / output_file
        else:
            planning_dir = ensure_planning_dir(project_path)
            output_path = planning_dir / "HANDOFF.md"

        output_path.write_text(handoff_content)
        result["output_file"] = str(output_path)
        result["message"] = f"Handoff document written to {output_path}"

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    format_type = "human"
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            format_type = sys.argv[idx + 1]

    handoff(output_file=output_file, format_type=format_type, output_json=output_json)


if __name__ == "__main__":
    main()
