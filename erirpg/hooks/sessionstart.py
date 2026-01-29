#!/usr/bin/env python3
"""
EriRPG SessionStart Hook - Check for incomplete runs at session start.

This hook is called by Claude Code at the START of a new session.
It checks for incomplete runs, resume files, and SQLite session context,
outputting a summary if there's work to continue.

Presents compact context summary from SQLite:
- Last session phase/step/progress
- Decision count and blocker status
- Pending actions
"""

import json
import os
import sys
import uuid
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


def get_project_name(project_path: str) -> str:
    """Get project name from config or directory name."""
    config_path = Path(project_path) / ".eri-rpg" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                return config.get("project_name", Path(project_path).name)
        except Exception:
            pass
    return Path(project_path).name


def create_new_session_id(project_path: str) -> str:
    """Create a new session ID and save to state."""
    session_id = str(uuid.uuid4())[:8]

    state_file = Path(project_path) / ".eri-rpg" / "state.json"
    state = {}
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
        except Exception:
            pass

    state["session_id"] = session_id
    state["session_started_at"] = datetime.now().isoformat()

    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Failed to save session ID: {e}")

    return session_id


def get_sqlite_context_summary(project_path: str) -> str:
    """Get context summary from SQLite database."""
    try:
        from erirpg.generators.context_md import generate_compact_summary

        project_name = get_project_name(project_path)
        return generate_compact_summary(project_name)
    except ImportError as e:
        log(f"Import error (generators not available): {e}")
        return None
    except Exception as e:
        log(f"Failed to get SQLite context: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def get_git_branch(project_path: str) -> str:
    """Get current git branch name."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        log(f"Git branch error: {e}")
    return None


def start_new_sqlite_session(project_path: str) -> str:
    """Start a new SQLite session for this project."""
    try:
        from erirpg import storage

        project_name = get_project_name(project_path)
        session_id = create_new_session_id(project_path)
        branch = get_git_branch(project_path)

        # Create session in SQLite
        storage.create_session(
            session_id=session_id,
            project_name=project_name,
            branch=branch,
        )
        log(f"Created new session {session_id} for {project_name} on branch {branch}")
        return session_id
    except ImportError as e:
        log(f"Import error (storage not available): {e}")
        return None
    except Exception as e:
        log(f"Failed to create SQLite session: {e}")
        import traceback
        log(traceback.format_exc())
        return None


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
            # Get SQLite context summary (new - takes priority)
            sqlite_summary = get_sqlite_context_summary(project_path)
            if sqlite_summary:
                messages.append(sqlite_summary)

            # Start a new session for tracking
            session_id = start_new_sqlite_session(project_path)
            if session_id:
                log(f"Started session: {session_id}")

            # Check for resume file (from previous compaction)
            resume_content = get_resume_file(project_path)
            if resume_content:
                # Only show if no SQLite summary (avoid duplication)
                if not sqlite_summary:
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

                # Only show run details if no SQLite summary (it includes this info)
                if recent and not sqlite_summary:
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

        # Add personal todos summary
        try:
            from erirpg.todos import get_session_summary
            todo_summary = get_session_summary()
            if todo_summary:
                messages.append("")
                messages.append(todo_summary)
        except Exception as e:
            log(f"Todo summary error: {e}")

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
