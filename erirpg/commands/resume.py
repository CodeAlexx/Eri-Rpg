#!/usr/bin/env python3
"""
/coder:resume - Restore from last session.

Usage:
    python -m erirpg.commands.resume [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import find_resume_state, get_progress


def resume(project_path: Optional[Path] = None, output_json: bool = False) -> dict:
    """Get resume state and context for continuing work."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "resume",
        "project": str(project_path),
    }

    # Get resume state
    try:
        resume_state = find_resume_state(project_path)
        result["resume_state"] = resume_state
    except Exception as e:
        result["resume_state"] = {"error": str(e)}

    # Get current progress
    try:
        progress = get_progress(project_path)
        result["progress"] = progress
    except Exception as e:
        result["progress"] = {"error": str(e)}

    # Generate recommendations
    result["recommendations"] = []
    rs = result.get("resume_state", {})
    if rs.get("found"):
        result["recommendations"].append(f"Resume from: {rs.get('source', 'unknown')}")
        if rs.get("phase"):
            result["recommendations"].append(f"Continue phase: {rs.get('phase')}")
    else:
        result["recommendations"].append("No explicit resume state found")
        result["recommendations"].append("Run /coder:progress to see current status")

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    resume(output_json=output_json)


if __name__ == "__main__":
    main()
