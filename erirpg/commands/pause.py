#!/usr/bin/env python3
"""
/coder:pause - Create handoff state when stopping.

Usage:
    python -m erirpg.commands.pause [reason] [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir
from erirpg.coder.state import get_progress


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
        planning_dir = ensure_planning_dir(project_path)

        # Get current progress
        progress = get_progress(project_path)
        result["progress"] = progress

        # Create RESUME.md
        resume_path = planning_dir / "RESUME.md"
        resume_content = f"""---
paused_at: {result['paused_at']}
phase: {progress.get('current_phase')}
status: {progress.get('status')}
reason: {reason or 'Manual pause'}
---

# Resume Point

## Current State
- **Phase**: {progress.get('current_phase', 'N/A')}
- **Status**: {progress.get('status', 'idle')}

## Reason for Pause
{reason or 'Manual pause - no specific reason given'}

## Next Steps
{progress.get('next_action', {}).get('description', 'Check /coder:progress')}

## Context
[Add any important context for the next session]
"""

        resume_path.write_text(resume_content)
        result["resume_file"] = str(resume_path)
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

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reason = " ".join(args) if args else None

    pause(reason=reason, output_json=output_json)


if __name__ == "__main__":
    main()
