#!/usr/bin/env python3
"""
EriRPG SessionStart Hook - Check for incomplete runs at session start.

This hook is called by Claude Code at the START of a new session.
It checks for incomplete runs and resume files, outputting a reminder
if there's work to continue.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def log(msg: str):
    """Log to file for debugging."""
    try:
        with open("/tmp/erirpg-sessionstart.log", "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)


def find_project_roots(start_path: str) -> list:
    """Find all project roots with .eri-rpg directories."""
    roots = []

    # Check start path and parents
    check_path = Path(start_path)
    while check_path != check_path.parent:
        if (check_path / ".eri-rpg").exists():
            roots.append(str(check_path))
            break  # Only get the nearest one for the main project
        check_path = check_path.parent

    return roots


def get_incomplete_runs(project_path: str) -> list:
    """Get list of incomplete runs."""
    run_dir = Path(project_path) / ".eri-rpg" / "runs"
    if not run_dir.exists():
        return []

    incomplete = []

    for run_file in run_dir.glob("*.json"):
        try:
            with open(run_file) as f:
                run_state = json.load(f)

            if run_state.get("completed_at") is None:
                goal = run_state.get("spec", {}).get("goal", "Unknown")[:40]
                run_id = run_state.get("id", run_file.stem)

                # Get progress
                plan = run_state.get("plan", {})
                steps = plan.get("steps", [])
                completed = sum(1 for s in steps if s.get("status") == "completed")

                # Check age
                started = run_state.get("started_at", "")
                try:
                    if started:
                        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00").split("+")[0])
                        age_days = (datetime.now() - started_dt).days
                    else:
                        age_days = 0
                except Exception as e:
                    pass  # date parse, use default
                    age_days = 0

                incomplete.append({
                    "id": run_id,
                    "goal": goal,
                    "progress": f"{completed}/{len(steps)}",
                    "age_days": age_days,
                })
        except Exception as e:
            import sys; print(f"[EriRPG] {e}", file=sys.stderr)

    return incomplete


def get_quick_fix_state(project_path: str) -> dict:
    """Get active quick fix state."""
    state_file = Path(project_path) / ".eri-rpg" / "quick_fix_state.json"
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr); return None


def get_resume_file(project_path: str) -> str:
    """Get contents of resume.md if it exists."""
    resume_path = Path(project_path) / ".eri-rpg" / "resume.md"
    if not resume_path.exists():
        return None

    try:
        return resume_path.read_text()
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr); return None


def main():
    """Main hook entry point."""
    log("=" * 50)
    log("SESSIONSTART HOOK INVOKED")

    try:
        # Read input from Claude Code
        raw_input = sys.stdin.read()
        log(f"Raw input: {raw_input[:200]}")

        input_data = json.loads(raw_input) if raw_input.strip() else {}
        cwd = input_data.get("cwd", os.getcwd())

        # Find project roots
        project_roots = find_project_roots(cwd)
        log(f"Project roots: {project_roots}")

        messages = []

        for project_path in project_roots:
            # Check for resume file (from previous compaction)
            resume_content = get_resume_file(project_path)
            if resume_content:
                messages.append(f"EriRPG resume file found at {project_path}")
                messages.append("Run /eri:status to see state")
                # Clean up resume file after notifying
                try:
                    (Path(project_path) / ".eri-rpg" / "resume.md").unlink()
                except Exception as e:
                    import sys; print(f"[EriRPG] {e}", file=sys.stderr)

            # Check for incomplete runs
            incomplete = get_incomplete_runs(project_path)
            if incomplete:
                recent = [r for r in incomplete if r["age_days"] < 7]
                stale = [r for r in incomplete if r["age_days"] >= 7]

                if recent:
                    messages.append(f"EriRPG: {len(recent)} incomplete run(s) in {Path(project_path).name}")
                    for run in recent[:2]:  # Show at most 2
                        messages.append(f"  - {run['id']}: {run['goal']}... ({run['progress']} steps)")
                    if len(recent) > 2:
                        messages.append(f"  ... and {len(recent) - 2} more")
                    messages.append("Resume: /eri:execute")

                if stale:
                    messages.append(f"EriRPG: {len(stale)} stale run(s) - consider /eri:cleanup")

            # Check for active quick fix
            quick_fix = get_quick_fix_state(project_path)
            if quick_fix and quick_fix.get("quick_fix_active"):
                messages.append(f"EriRPG: Quick fix active on {quick_fix.get('target_file')}")
                messages.append("Complete: eri-rpg quick-done or cancel: eri-rpg quick-cancel")

        # Output message if any
        if messages:
            output = {
                "systemMessage": "\n".join(messages)
            }
        else:
            output = {}

        print(json.dumps(output))
        log(f"Output: {output}")

    except Exception as e:
        log(f"Error: {e}")
        import traceback
        log(traceback.format_exc())
        # Don't output error on session start - just log it
        print(json.dumps({}))


if __name__ == "__main__":
    main()
