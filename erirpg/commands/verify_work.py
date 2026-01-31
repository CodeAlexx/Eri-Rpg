#!/usr/bin/env python3
"""
/coder:verify-work - Manual user acceptance testing.

Guides UAT process with:
- Test checklist generation
- Result recording
- Gap identification

Usage:
    python -m erirpg.commands.verify_work <phase-number> [--json]
    python -m erirpg.commands.verify_work <phase-number> --result pass|fail [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder.state import (
    get_phase_info,
    update_state,
    ensure_planning_dir,
)
from erirpg.coder.planning import get_phase_verification


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

        # Get phase info
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found"
            if output_json:
                print(json.dumps(result, indent=2, default=str))
            return result

        # Get verification criteria
        verification = get_phase_verification(project_path, phase_number)
        result["verification_criteria"] = verification

        if result_status:
            # Record result
            phase_dir = planning_dir / "phases" / f"{phase_number:02d}-{phase_info.get('name', 'phase').lower().replace(' ', '-')}"
            phase_dir.mkdir(parents=True, exist_ok=True)

            uat_path = phase_dir / f"phase-{phase_number:02d}-UAT.md"
            uat_content = f"""---
phase: {phase_number}
verified: {datetime.utcnow().isoformat()}Z
status: {result_status}
---

# UAT Results - Phase {phase_number}

## Test Results
**Status**: {result_status.upper()}

## Verification Criteria
{chr(10).join(f"- [{'x' if result_status == 'pass' else ' '}] {c}" for c in verification.get('criteria', []))}

## Notes
[Add any notes about the verification]
"""
            uat_path.write_text(uat_content)
            result["uat_file"] = str(uat_path)
            result["status"] = result_status

            if result_status == "pass":
                update_state(project_path, {
                    "current_phase": phase_number,
                    "status": "verified"
                })
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
            # Show verification checklist
            result["status"] = "awaiting_verification"
            result["checklist"] = verification.get("criteria", [])
            result["message"] = "Review the checklist and record result"
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

    # Parse --result argument
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
