#!/usr/bin/env python3
"""
EriRPG PreCompact Hook - Save state before context compaction.

This hook is called by Claude Code BEFORE context compaction occurs.
It saves the current run state and creates a resume file so the agent
can pick up where it left off after compaction.

Outputs a summary that will be included in the compacted context.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def log(msg: str):
    """Log to file for debugging."""
    try:
        with open("/tmp/erirpg-precompact.log", "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def find_project_root(start_path: str) -> str:
    """Find project root by looking for .eri-rpg directory."""
    check_path = Path(start_path)
    while check_path != check_path.parent:
        if (check_path / ".eri-rpg").exists():
            return str(check_path)
        check_path = check_path.parent
    return start_path


def get_active_run(project_path: str) -> dict:
    """Get the most recent active run."""
    run_dir = Path(project_path) / ".eri-rpg" / "runs"
    if not run_dir.exists():
        return None

    runs = list(run_dir.glob("*.json"))
    if not runs:
        return None

    # Get latest by mtime
    latest = max(runs, key=lambda p: p.stat().st_mtime)

    try:
        with open(latest) as f:
            run_state = json.load(f)

        if run_state.get("completed_at") is None:
            return run_state
    except Exception:
        pass

    return None


def get_quick_fix_state(project_path: str) -> dict:
    """Get active quick fix state."""
    state_file = Path(project_path) / ".eri-rpg" / "quick_fix_state.json"
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception:
        return None


def create_resume_file(project_path: str, run_state: dict, quick_fix: dict) -> str:
    """Create a resume.md file with instructions for continuing after compaction."""
    resume_path = Path(project_path) / ".eri-rpg" / "resume.md"

    lines = [
        "# EriRPG Resume Instructions",
        "",
        f"Created: {datetime.now().isoformat()}",
        "",
        "## State Saved Before Compaction",
        "",
    ]

    if run_state:
        goal = run_state.get("spec", {}).get("goal", "Unknown")
        run_id = run_state.get("id", "unknown")

        # Get progress
        plan = run_state.get("plan", {})
        steps = plan.get("steps", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        in_progress = [s for s in steps if s.get("status") == "in_progress"]

        lines.extend([
            f"### Active Run: {run_id}",
            f"**Goal**: {goal}",
            f"**Progress**: {completed}/{len(steps)} steps complete",
            "",
        ])

        if in_progress:
            current = in_progress[0]
            lines.extend([
                f"### Current Step",
                f"**ID**: {current.get('id')}",
                f"**Goal**: {current.get('goal')}",
                "",
            ])

        lines.extend([
            "### To Resume",
            "```python",
            "from erirpg.agent import Agent",
            f"agent = Agent.resume('{project_path}')",
            "# Continue from current step",
            "```",
            "",
        ])

    if quick_fix:
        lines.extend([
            "### Active Quick Fix",
            f"**File**: {quick_fix.get('target_file')}",
            f"**Description**: {quick_fix.get('description')}",
            "",
            "### To Complete Quick Fix",
            "```bash",
            "eri-rpg quick-done <project>",
            "```",
            "",
        ])

    if not run_state and not quick_fix:
        lines.extend([
            "No active run or quick fix at compaction time.",
            "",
        ])

    content = "\n".join(lines)

    resume_path.parent.mkdir(parents=True, exist_ok=True)
    with open(resume_path, "w") as f:
        f.write(content)

    return str(resume_path)


def main():
    """Main hook entry point."""
    log("=" * 50)
    log("PRECOMPACT HOOK INVOKED")

    try:
        # Read input from Claude Code
        raw_input = sys.stdin.read()
        log(f"Raw input: {raw_input[:200]}")

        input_data = json.loads(raw_input) if raw_input.strip() else {}
        cwd = input_data.get("cwd", os.getcwd())

        # Find project root
        project_path = find_project_root(cwd)
        log(f"Project path: {project_path}")

        # Get current state
        run_state = get_active_run(project_path)
        quick_fix = get_quick_fix_state(project_path)

        # Create resume file
        if run_state or quick_fix:
            resume_path = create_resume_file(project_path, run_state, quick_fix)
            log(f"Created resume file: {resume_path}")

        # Output summary for compaction
        summary_lines = []

        if run_state:
            goal = run_state.get("spec", {}).get("goal", "Unknown")[:50]
            run_id = run_state.get("id", "unknown")
            plan = run_state.get("plan", {})
            steps = plan.get("steps", [])
            completed = sum(1 for s in steps if s.get("status") == "completed")

            summary_lines.append(f"EriRPG Run Active: {run_id}")
            summary_lines.append(f"  Goal: {goal}...")
            summary_lines.append(f"  Progress: {completed}/{len(steps)} steps")

        if quick_fix:
            summary_lines.append(f"Quick Fix Active: {quick_fix.get('target_file')}")

        if summary_lines:
            summary_lines.append("")
            summary_lines.append("Resume with: /eri:execute or /eri:status")

        output = {
            "systemMessage": "\n".join(summary_lines) if summary_lines else None
        }

        print(json.dumps(output))
        log(f"Output: {output}")

    except Exception as e:
        log(f"Error: {e}")
        import traceback
        log(traceback.format_exc())
        print(json.dumps({"systemMessage": f"EriRPG precompact: {e}"}))


if __name__ == "__main__":
    main()
