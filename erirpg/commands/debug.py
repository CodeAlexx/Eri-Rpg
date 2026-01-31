#!/usr/bin/env python3
"""
/coder:debug - Systematic debugging with scientific method.

Creates debug session with:
- Symptom capture
- Hypothesis tracking
- Evidence collection
- Resolution documentation

Usage:
    python -m erirpg.commands.debug <symptom> [--json]
    python -m erirpg.commands.debug --status [--json]
    python -m erirpg.commands.debug --resolve <resolution> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import ensure_planning_dir
from erirpg.coder.debug import (
    create_debug_session,
    get_active_session,
    add_hypothesis,
    add_evidence,
    resolve_session,
)


def debug(
    symptom: Optional[str] = None,
    status: bool = False,
    resolve: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Manage debug sessions."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "debug",
        "project": str(project_path),
    }

    if status:
        # Get active session status
        try:
            session = get_active_session(project_path)
            if session:
                result["status"] = "active"
                result["session"] = session
            else:
                result["status"] = "no_active_session"
                result["message"] = "No active debug session"
        except Exception as e:
            result["error"] = str(e)

    elif resolve:
        # Resolve active session
        try:
            resolved = resolve_session(project_path, resolve)
            result["status"] = "resolved"
            result["resolution"] = resolve
            result["session"] = resolved
        except Exception as e:
            result["error"] = str(e)

    elif symptom:
        # Create new debug session
        try:
            session = create_debug_session(project_path, symptom)
            result["status"] = "created"
            result["session"] = session
            result["next_steps"] = [
                "Form hypothesis about the cause",
                "Gather evidence (logs, stack traces, etc.)",
                "Test hypothesis",
                "Resolve with /coder:debug --resolve '<resolution>'"
            ]
        except Exception as e:
            result["error"] = str(e)

    else:
        result["error"] = "Provide symptom, --status, or --resolve"
        result["usage"] = {
            "new_session": "python -m erirpg.commands.debug '<symptom>'",
            "check_status": "python -m erirpg.commands.debug --status",
            "resolve": "python -m erirpg.commands.debug --resolve '<resolution>'"
        }

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    status = "--status" in sys.argv

    # Parse --resolve argument
    resolve = None
    if "--resolve" in sys.argv:
        idx = sys.argv.index("--resolve")
        if idx + 1 < len(sys.argv):
            resolve = sys.argv[idx + 1]

    # Get symptom (non-flag arguments)
    symptom = None
    if not status and not resolve:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            symptom = " ".join(args)

    debug(
        symptom=symptom,
        status=status,
        resolve=resolve,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
