#!/usr/bin/env python3
"""
/coder:verify-work - Manual user acceptance testing.

Usage:
    python -m erirpg.commands.verify_work <phase-number> [--json]
    python -m erirpg.commands.verify_work <phase-number> --result pass|fail [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir, load_roadmap


def verify_work(
    phase_number: int,
    result_status: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Verify phase work."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "verify-work",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Find phase directory
        phases_dir = planning_dir / "phases"
        phase_dir = None
        if phases_dir.exists():
            for d in phases_dir.iterdir():
                if d.is_dir() and d.name.startswith(f"{phase_number:02d}"):
                    phase_dir = d
                    break

        if not phase_dir:
            phase_dir = phases_dir / f"{phase_number:02d}-phase"
            phase_dir.mkdir(parents=True, exist_ok=True)

        if result_status:
            # Record result
            uat_path = phase_dir / f"phase-{phase_number:02d}-UAT.md"
            uat_content = f"""---
phase: {phase_number}
verified: {datetime.utcnow().isoformat()}Z
status: {result_status}
---

# UAT Results - Phase {phase_number}

## Test Results
**Status**: {result_status.upper()}

## Notes
[Add verification notes]
"""
            uat_path.write_text(uat_content)
            result["uat_file"] = str(uat_path)
            result["status"] = result_status

            if result_status == "pass":
                result["message"] = f"Phase {phase_number} verified successfully"
                result["next_steps"] = [
                    "Proceed to next phase",
                    "Or run /coder:complete-milestone if all phases done"
                ]
            else:
                result["message"] = f"Phase {phase_number} verification failed"
                result["next_steps"] = [
                    "Review gaps and fix issues",
                    f"Re-run /coder:verify-work {phase_number} --result pass when fixed"
                ]
        else:
            result["status"] = "awaiting_verification"
            result["message"] = "Review the phase and record result"
            result["next_steps"] = [
                f"/coder:verify-work {phase_number} --result pass",
                f"/coder:verify-work {phase_number} --result fail"
            ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    result_status = None
    if "--result" in sys.argv:
        idx = sys.argv.index("--result")
        if idx + 1 < len(sys.argv):
            result_status = sys.argv[idx + 1].lower()
            if result_status not in ("pass", "fail"):
                print(json.dumps({"error": "Result must be 'pass' or 'fail'"}, indent=2))
                sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if result_status and result_status in args:
        args.remove(result_status)

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.verify_work <phase-number> [--result pass|fail]"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    verify_work(phase_number, result_status=result_status, output_json=output_json)


if __name__ == "__main__":
    main()
