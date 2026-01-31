#!/usr/bin/env python3
"""
/coder:pause - Create handoff state when stopping.

Saves current state for later resume including:
- Current position
- Active tasks
- Context

Usage:
    python -m erirpg.commands.pause [reason] [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import (
    save_pause_state,
    get_current_position,
)


def pause(
    reason: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Create pause/handoff state."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "pause",
        "project": str(project_path),
        "paused_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        # Get current position
        position = get_current_position(project_path)
        result["position"] = position

        # Save pause state
        pause_state = save_pause_state(
            project_path,
            reason=reason,
            position=position
        )
        result["pause_state"] = pause_state
        result["resume_file"] = str(pause_state.get("resume_file", ""))
        result["message"] = "Session paused. Use /coder:resume to continue."

        if reason:
            result["reason"] = reason

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Get reason (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reason = " ".join(args) if args else None

    pause(reason=reason, output_json=output_json)


if __name__ == "__main__":
    main()
