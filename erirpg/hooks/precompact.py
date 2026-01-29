#!/usr/bin/env python3
"""
EriRPG PreCompact Hook - Save state before context compaction.

This hook is called by Claude Code BEFORE context compaction occurs.
It saves the current run state and creates a resume file so the agent
can pick up where it left off after compaction.

Additionally captures session context to SQLite for cross-session continuity:
- Current phase/step/progress
- Decisions made (from conversation)
- Blockers encountered
- Next actions queue
- Files modified (from git)

Outputs a summary that will be included in the compacted context.
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path


def log(msg: str):
    """Log to file for debugging."""
    try:
        with open("/tmp/erirpg-precompact.log", "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)


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
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)

    return None


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


def get_git_modified_files(project_path: str) -> list:
    """Get list of modified files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            files = result.stdout.strip().split("\n")
            return [f for f in files if f]
    except Exception as e:
        log(f"Git error: {e}")
    return []


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


def get_session_state(project_path: str) -> dict:
    """Get current session state from state.json."""
    state_file = Path(project_path) / ".eri-rpg" / "state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_or_create_session_id(project_path: str) -> str:
    """Get existing session ID or create a new one."""
    state = get_session_state(project_path)
    session_id = state.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        # Save session ID to state
        state_file = Path(project_path) / ".eri-rpg" / "state.json"
        state["session_id"] = session_id
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            log(f"Failed to save session ID: {e}")

    return session_id


def save_session_to_sqlite(project_path: str, run_state: dict, quick_fix: dict) -> str:
    """Save session context to SQLite database.

    Returns the session ID.
    """
    try:
        # Import storage module
        from erirpg import storage
        from erirpg.generators.context_md import generate_context_md

        project_name = get_project_name(project_path)
        session_id = get_or_create_session_id(project_path)

        # Check if session exists
        existing = storage.get_session(session_id)

        # Determine phase and step from run state
        phase = None
        step = None
        progress_pct = 0

        if run_state:
            plan = run_state.get("plan", {})
            steps = plan.get("steps", [])
            completed = sum(1 for s in steps if s.get("status") == "completed")
            in_progress = [s for s in steps if s.get("status") == "in_progress"]

            if steps:
                progress_pct = int((completed / len(steps)) * 100)

            if in_progress:
                current = in_progress[0]
                step = f"{completed + 1}/{len(steps)} - {current.get('goal', 'Unknown')[:50]}"

            spec = run_state.get("spec", {})
            phase = spec.get("phase", "implementing")
        elif quick_fix:
            phase = "quick_fix"
            step = quick_fix.get("target_file", "unknown")

        # Get modified files
        files_modified = get_git_modified_files(project_path)

        if existing:
            # Update existing session
            storage.update_session(
                session_id,
                phase=phase,
                step=step,
                progress_pct=progress_pct,
                files_modified=files_modified,
            )
            log(f"Updated session {session_id}")
        else:
            # Create new session
            storage.create_session(
                session_id=session_id,
                project_name=project_name,
                phase=phase,
                step=step,
            )
            if files_modified:
                storage.update_session(session_id, files_modified=files_modified)
            log(f"Created session {session_id}")

        # Generate CONTEXT.md
        context_path = Path(project_path) / ".eri-rpg" / "CONTEXT.md"
        generate_context_md(project_name, session_id, str(context_path))
        log(f"Generated CONTEXT.md")

        return session_id

    except ImportError as e:
        log(f"Import error (storage not available): {e}")
        return None
    except Exception as e:
        log(f"Failed to save session to SQLite: {e}")
        import traceback
        log(traceback.format_exc())
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

        # Create resume file (legacy)
        if run_state or quick_fix:
            resume_path = create_resume_file(project_path, run_state, quick_fix)
            log(f"Created resume file: {resume_path}")

        # Save session context to SQLite (new)
        session_id = save_session_to_sqlite(project_path, run_state, quick_fix)
        log(f"Session ID: {session_id}")

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

        if session_id:
            summary_lines.append(f"Session: {session_id}")

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
