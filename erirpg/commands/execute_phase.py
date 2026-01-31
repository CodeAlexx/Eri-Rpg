#!/usr/bin/env python3
"""
/coder:execute-phase - Execute all plans for a phase.

Orchestrates plan execution with:
- Wave-based parallelization
- Checkpoint creation
- Progress tracking
- Verification

Usage:
    python -m erirpg.commands.execute_phase <phase-number> [--json]
    python -m erirpg.commands.execute_phase <phase-number> --plan <n> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.state import (
    ensure_planning_dir,
    get_phase_info,
    update_state,
)
from erirpg.coder.planning import (
    get_phase_plans,
    group_plans_by_wave,
)
from erirpg.coder.git_ops import create_checkpoint


def execute_phase(
    phase_number: int,
    plan_number: Optional[int] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Execute plans for a phase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "execute-phase",
        "project": str(project_path),
        "phase": phase_number,
    }

    try:
        # Get phase info
        phase_info = get_phase_info(project_path, phase_number)
        if not phase_info:
            result["error"] = f"Phase {phase_number} not found"
            if output_json:
                print(json.dumps(result, indent=2, default=str))
            return result

        # Get plans
        plans = get_phase_plans(project_path, phase_number)
        if not plans:
            result["error"] = f"No plans found for phase {phase_number}"
            result["message"] = "Run /coder:plan-phase first"
            if output_json:
                print(json.dumps(result, indent=2, default=str))
            return result

        result["total_plans"] = len(plans)

        if plan_number:
            # Execute specific plan
            plan = next((p for p in plans if p.get("number") == plan_number), None)
            if not plan:
                result["error"] = f"Plan {plan_number} not found"
            else:
                result["executing_plan"] = plan
                result["status"] = "ready"
                result["message"] = f"Ready to execute plan {plan_number}"
        else:
            # Group by wave for parallel execution
            waves = group_plans_by_wave(plans)
            result["waves"] = waves
            result["wave_count"] = len(waves)

            # Create checkpoint before execution
            checkpoint = create_checkpoint(
                f"phase-{phase_number}-start",
                project_path
            )
            result["checkpoint"] = checkpoint

            # Update state
            update_state(project_path, {
                "current_phase": phase_number,
                "status": "executing"
            })

            result["status"] = "ready"
            result["message"] = f"Phase {phase_number} ready for execution ({len(plans)} plans in {len(waves)} waves)"

        result["next_steps"] = [
            "Execute each plan in order",
            "Create summaries after each plan",
            f"Run /coder:verify-work {phase_number} when complete"
        ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --plan argument
    plan_number = None
    if "--plan" in sys.argv:
        idx = sys.argv.index("--plan")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
            plan_number = int(sys.argv[idx + 1])

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if plan_number and str(plan_number) in args:
        args.remove(str(plan_number))

    if not args or not args[0].isdigit():
        print(json.dumps({
            "error": "Phase number required",
            "usage": "python -m erirpg.commands.execute_phase <phase-number> [--plan <n>]"
        }, indent=2))
        sys.exit(1)

    phase_number = int(args[0])
    execute_phase(phase_number, plan_number=plan_number, output_json=output_json)


if __name__ == "__main__":
    main()
