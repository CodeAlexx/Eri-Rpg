#!/usr/bin/env python3
"""
/coder:progress - Show current position and metrics.

Displays:
- Current phase and plan status
- Completion percentages
- Performance metrics
- What's next

Usage:
    python -m erirpg.commands.progress [--json] [--detailed]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import get_progress


def progress(
    project_path: Optional[Path] = None,
    output_json: bool = False,
    detailed: bool = False
) -> dict:
    """Get current progress and metrics."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "progress",
        "project": str(project_path),
    }

    # Get progress from state module
    try:
        progress_data = get_progress(project_path)
        result.update(progress_data)
    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    detailed = "--detailed" in sys.argv
    progress(output_json=output_json, detailed=detailed)


if __name__ == "__main__":
    main()
