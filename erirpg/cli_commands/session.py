"""
Session Commands - Session state and gap closure.

Commands:
- session: Show or update current session state
- handoff: Generate handoff summary for next session
- gaps: Show gaps from verification failures
- status: Show full session context from SQLite
- snapshot: Save checkpoint before risky operations
- decision: Record a decision with rationale
- blocker: Add or resolve blockers
- action: Add next actions
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import click


def register(cli):
    """Register session commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command(name="session")
    @click.argument("project")
    @click.option("--note", "-n", default=None, help="Add a note to current session")
    @click.option("--action", "-a", default=None, help="Add a next action")
    @click.option("--blocker", "-b", default=None, help="Add a blocker")
    def session_cmd(project: str, note: str, action: str, blocker: str):
        """Show or update current session state.

        Example:
            eri-rpg session myproj
            eri-rpg session myproj --note "Need to revisit auth flow"
            eri-rpg session myproj --action "Fix failing tests"
            eri-rpg session myproj --blocker "API rate limiting issue"
        """
        from erirpg.memory import get_latest_session, save_session_state

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        session = get_latest_session(proj.path)

        if not session:
            click.echo("No active session found")
            click.echo("Start a run with: eri-rpg goal-run <project>")
            return

        # Handle updates
        if note:
            session.notes = (session.notes + "\n" if session.notes else "") + note
            session.touch()
            save_session_state(proj.path, session)
            click.echo(f"Added note to session {session.run_id}")

        if action:
            session.add_next_action(action)
            session.touch()
            save_session_state(proj.path, session)
            click.echo(f"Added next action: {action}")

        if blocker:
            b = session.add_blocker(blocker)
            session.touch()
            save_session_state(proj.path, session)
            click.echo(f"Added blocker: {b.id} - {blocker}")

        # Show session state
        if not (note or action or blocker):
            click.echo(session.format_handoff())

    @cli.command(name="handoff")
    @click.argument("project")
    def handoff_cmd(project: str):
        """Generate handoff summary for next session.

        Example:
            eri-rpg handoff myproj
        """
        from erirpg.memory import get_latest_session

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        session = get_latest_session(proj.path)

        if not session:
            click.echo("No active session found")
            return

        click.echo(session.format_handoff())

    @cli.command(name="gaps")
    @click.argument("project")
    @click.option("--run", "-r", "run_id", default=None, help="Run ID to analyze (default: latest)")
    def gaps_cmd(project: str, run_id: str):
        """Show gaps from verification failures.

        Example:
            eri-rpg gaps myproj
            eri-rpg gaps myproj --run run-abc123
        """
        from erirpg.memory import analyze_gaps, load_gaps
        from pathlib import Path

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        # Find run ID if not specified
        if not run_id:
            runs_dir = Path(proj.path) / ".eri-rpg" / "runs"
            if runs_dir.exists():
                runs = list(runs_dir.glob("*.json"))
                if runs:
                    latest = max(runs, key=lambda p: p.stat().st_mtime)
                    run_id = latest.stem
                else:
                    click.echo("No runs found")
                    return
            else:
                click.echo("No runs found")
                return

        # Try loading existing gaps first
        gaps = load_gaps(proj.path, run_id)

        # If no cached gaps, analyze
        if not gaps:
            gaps = analyze_gaps(proj.path, run_id)

        if not gaps:
            click.echo(f"No gaps found for run {run_id}")
            click.echo("All steps passed verification!")
            return

        click.echo(f"Gaps from run {run_id} ({len(gaps)} found):")
        click.echo("=" * 60)

        for g in gaps:
            status = "✓ Fixed" if g.fixed else "○ Open"
            click.echo(f"[{g.id}] {status}")
            click.echo(f"  Step: {g.source_step}")
            click.echo(f"  Failure: {g.failure}")
            click.echo(f"  Suggested fix: {g.suggested_fix}")
            if g.fix_spec_id:
                click.echo(f"  Fix spec: {g.fix_spec_id}")
            click.echo("")

    @cli.command(name="switch")
    @click.argument("project")
    def switch_cmd(project: str):
        """Switch active project context.

        Saves current session (if any) and switches to the target project.
        State persists across /clear and new sessions.

        If PROJECT is a path to an existing directory, auto-registers it.

        Example:
            eri-rpg switch myapp
            eri-rpg switch eritrainer
            eri-rpg switch /home/user/projects/newapp  # auto-registers
        """
        from erirpg.state import State
        from erirpg.memory import get_latest_session, save_session_state
        from erirpg.registry import detect_project_language

        state = State.load()

        # Check if project exists in registry
        target_proj = registry.get(project)

        # If not found, check if it's a path that exists
        if not target_proj:
            expanded_path = os.path.expanduser(project)
            if os.path.isdir(expanded_path):
                abs_path = os.path.abspath(expanded_path)

                # First check if this path is already registered under a different name
                for existing in registry.list():
                    if os.path.abspath(existing.path) == abs_path:
                        target_proj = existing
                        project = existing.name
                        click.echo(f"Path matches registered project: {existing.name}")
                        break

                # If still not found, auto-register
                if not target_proj:
                    # Use directory name as project name
                    proj_name = Path(abs_path).name
                    # Make name unique if collision
                    base_name = proj_name
                    counter = 1
                    while registry.get(proj_name):
                        proj_name = f"{base_name}_{counter}"
                        counter += 1
                    # Detect language
                    lang = detect_project_language(abs_path)
                    if lang == "unknown":
                        lang = "python"  # Default
                    # Register it
                    target_proj = registry.add(proj_name, abs_path, lang)
                    click.echo(f"Auto-registered project: {proj_name}")
                    click.echo(f"  Path: {abs_path}")
                    click.echo(f"  Language: {lang}")
                    click.echo("")
                    # Update project var to use the registered name
                    project = proj_name
            else:
                click.echo(f"Project '{project}' not found in registry")
                click.echo("")
                click.echo("Registered projects:")
                for p in registry.list():
                    click.echo(f"  - {p.name}: {p.path}")
                click.echo("")
                click.echo("Tip: You can also pass a path to auto-register:")
                click.echo(f"  eri-rpg switch /path/to/project")
                raise SystemExit(1)

        # Check if switching to same project
        if state.active_project == project:
            click.echo(f"Already on project: {project}")
            session = get_latest_session(target_proj.path)
            if session:
                click.echo("")
                click.echo(session.format_handoff())
            return

        # Save current session if we have an active project
        if state.active_project:
            current_proj = registry.get(state.active_project)
            if current_proj:
                session = get_latest_session(current_proj.path)
                if session:
                    session.touch()
                    save_session_state(current_proj.path, session)
                    click.echo(f"Saved session for '{state.active_project}'")

        # Switch to new project (sets target_project which persists)
        state.set_active_project(project, target_proj.path)
        click.echo(f"Switched to: {project}")
        click.echo(f"Path: {target_proj.path}")

        # Find where .planning/ lives (might be in a subdirectory)
        def find_coder_planning(base_path: Path) -> Path:
            """Find coder workflow .planning/ directory."""
            # Check base path
            planning = base_path / ".planning"
            if planning.is_dir() and (
                (planning / "phases").is_dir() or
                (planning / "STATE.md").exists() or
                (planning / "ROADMAP.md").exists()
            ):
                return base_path
            # Check one level down
            for subdir in base_path.iterdir():
                if subdir.is_dir():
                    planning = subdir / ".planning"
                    if planning.is_dir() and (
                        (planning / "phases").is_dir() or
                        (planning / "STATE.md").exists() or
                        (planning / "ROADMAP.md").exists()
                    ):
                        return subdir
            return base_path

        proj_path = Path(target_proj.path)
        work_path = find_coder_planning(proj_path)
        if work_path != proj_path:
            click.echo(f"")
            click.echo(f"Coder workflow at: {work_path}")
            click.echo(f"Run: cd {work_path}")

        # Show handoff from target project
        session = get_latest_session(target_proj.path)
        if session:
            click.echo("")
            click.echo(session.format_handoff())
        else:
            click.echo("")
            click.echo("No previous session found")
            click.echo("Start a run with: eri-rpg goal-run " + project)

    @cli.command(name="resume")
    @click.option("--project", "-p", default=None, help="Project to resume (default: active)")
    def resume_cmd(project: str):
        """Resume work on active or specified project.

        Shows the latest session handoff for quick context recovery.
        Use at the start of a new Claude Code session.

        Example:
            eri-rpg resume
            eri-rpg resume -p myapp
        """
        from erirpg.state import State
        from erirpg.memory import get_latest_session

        state = State.load()

        # Determine which project to resume
        target_name = project or state.active_project

        if not target_name:
            click.echo("No active project set")
            click.echo("")
            click.echo("Registered projects:")
            for p in registry.list():
                marker = " (active)" if p.name == state.active_project else ""
                click.echo(f"  - {p.name}{marker}: {p.path}")
            click.echo("")
            click.echo("Switch with: eri-rpg switch <project>")
            raise SystemExit(1)

        # Get the project
        proj = registry.get(target_name)
        if not proj:
            click.echo(f"Project '{target_name}' not found in registry")
            raise SystemExit(1)

        # Update active project if resuming a specific one
        if project and project != state.active_project:
            state.set_active_project(project)
            click.echo(f"Switched to: {project}")

        click.echo(f"Project: {target_name}")
        click.echo(f"Path: {proj.path}")

        # Show session handoff
        try:
            session = get_latest_session(proj.path)
            if session:
                click.echo("")
                click.echo(session.format_handoff())
            else:
                click.echo("")
                click.echo("No previous session found")
                click.echo(f"Start a run with: eri-rpg goal-run {target_name}")
        except Exception as e:
            click.echo(f"Error loading session: {e}")
            click.echo(f"Start fresh with: eri-rpg goal-run {target_name}")

        # Also show decisions from latest run
        try:
            from erirpg.agent.run import get_latest_run
            run = get_latest_run(proj.path)
            if run and run.decisions:
                click.echo("")
                click.echo(f"### Key Decisions ({len(run.decisions)})")
                for d in run.decisions[-5:]:  # Last 5
                    click.echo(f"- **{d.decision}**")
                    if d.rationale:
                        click.echo(f"  ↳ {d.rationale}")
        except Exception:
            pass  # No run decisions to show

    # ==========================================================================
    # New SQLite-backed session commands
    # ==========================================================================

    def _get_project_name(project_path: str) -> str:
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

    def _get_session_id(project_path: str) -> str:
        """Get session ID from state file, or create one."""
        state_file = Path(project_path) / ".eri-rpg" / "state.json"
        state = {}
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
            except Exception:
                pass

        session_id = state.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
            state["session_id"] = session_id
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        return session_id

    @cli.command(name="status")
    @click.option("--full", "-f", is_flag=True, help="Show full context with all details")
    @click.option("--project", "-p", default=None, help="Project path (default: current directory)")
    def status_cmd(full: bool, project: str):
        """Show session context from SQLite.

        Displays current session status, decisions, blockers, and next actions.

        Example:
            eri-rpg status
            eri-rpg status --full
        """
        try:
            from erirpg import storage
            from erirpg.generators.context_md import generate_compact_summary, generate_context_md
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)

        if full:
            # Full context from CONTEXT.md generator
            content = generate_context_md(project_name)
            click.echo(content)
        else:
            # Compact summary
            summary = generate_compact_summary(project_name)
            click.echo(summary)

    @cli.command(name="snapshot")
    @click.option("--note", "-n", default=None, help="Note about this checkpoint")
    @click.option("--alias", "-a", default=None, help="Human-readable session name")
    @click.option("--project", "-p", default=None, help="Project path (default: current directory)")
    def snapshot_cmd(note: str, alias: str, project: str):
        """Save a checkpoint before risky operations.

        Creates a snapshot of current session state. Useful before
        major refactors or experimental changes.

        Example:
            eri-rpg snapshot --note "Before auth refactor"
            eri-rpg snapshot --alias "auth-rework" -n "Testing new approach"
        """
        try:
            from erirpg import storage
            from erirpg.generators.context_md import generate_context_md
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)
        session_id = _get_session_id(project_path)

        # Ensure session exists in SQLite
        existing = storage.get_session(session_id)
        if not existing:
            storage.create_session(session_id, project_name, alias=alias)
            click.echo(f"Created session: {session_id}" + (f" ({alias})" if alias else ""))
        elif alias and not existing.alias:
            # Update alias if provided and not already set
            storage.update_session(session_id, alias=alias)
            click.echo(f"Session alias set: {alias}")

        # Generate CONTEXT.md as snapshot
        context_path = Path(project_path) / ".eri-rpg" / "CONTEXT.md"
        generate_context_md(project_name, session_id, str(context_path))

        # Also save a timestamped snapshot
        snapshots_dir = Path(project_path) / ".eri-rpg" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = snapshots_dir / f"snapshot_{timestamp}.md"
        generate_context_md(project_name, session_id, str(snapshot_path))

        # Add note as learning if provided
        if note:
            storage.add_session_learning(session_id, "Snapshot Note", note)

        click.echo(f"✓ Snapshot saved")
        click.echo(f"  Session: {session_id}")
        click.echo(f"  Context: {context_path}")
        click.echo(f"  Archive: {snapshot_path}")

    @cli.command(name="decision")
    @click.argument("context")
    @click.argument("choice")
    @click.option("--why", "-w", default=None, help="Rationale for the decision")
    @click.option("--project", "-p", default=None, help="Project path (default: current directory)")
    def decision_cmd(context: str, choice: str, why: str, project: str):
        """Record a decision with rationale.

        Decisions are stored in SQLite for cross-session recall.

        Example:
            eri-rpg decision "Session storage" "SQLite" --why "Fast queries"
            eri-rpg decision "Auth method" "JWT" -w "Stateless, scales well"
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)
        session_id = _get_session_id(project_path)

        # Ensure session exists
        existing = storage.get_session(session_id)
        if not existing:
            storage.create_session(session_id, project_name)

        # Add decision
        decision = storage.add_decision(session_id, context, choice, why)
        click.echo(f"✓ Decision recorded")
        click.echo(f"  Context: {context}")
        click.echo(f"  Choice: {choice}")
        if why:
            click.echo(f"  Why: {why}")

    @cli.command(name="add-blocker")
    @click.argument("description")
    @click.option("--severity", "-s", type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                  default=None, help="Blocker severity (optional)")
    @click.option("--project", "-p", default=None, help="Project path (default: current directory)")
    def add_blocker_cmd(description: str, severity: str, project: str):
        """Add a blocker to current session.

        Example:
            eri-rpg add-blocker "API rate limiting issue" --severity HIGH
            eri-rpg add-blocker "Missing test fixtures"
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)
        session_id = _get_session_id(project_path)

        # Ensure session exists
        existing = storage.get_session(session_id)
        if not existing:
            storage.create_session(session_id, project_name)

        # Add blocker
        blocker = storage.add_blocker(session_id, description, severity)
        severity_str = f" [{severity}]" if severity else ""
        click.echo(f"✓ Blocker added{severity_str}")
        click.echo(f"  ID: {blocker.id}")
        click.echo(f"  {description}")

    @cli.command(name="resolve-blocker")
    @click.argument("blocker_id", type=int)
    @click.argument("resolution")
    def resolve_blocker_cmd(blocker_id: int, resolution: str):
        """Mark a blocker as resolved.

        Example:
            eri-rpg resolve-blocker 1 "Implemented retry logic"
            eri-rpg resolve-blocker 3 "Skipped - not needed"
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        success = storage.resolve_blocker(blocker_id, resolution)
        if success:
            click.echo(f"✓ Blocker {blocker_id} resolved")
            click.echo(f"  Resolution: {resolution}")
        else:
            click.echo(f"Blocker {blocker_id} not found", err=True)
            raise SystemExit(1)

    @cli.command(name="add-action")
    @click.argument("action")
    @click.option("--priority", "-p", type=int, default=0, help="Priority (higher = more important)")
    @click.option("--project", default=None, help="Project path (default: current directory)")
    def add_action_cmd(action: str, priority: int, project: str):
        """Add a next action to the queue.

        Example:
            eri-rpg add-action "Implement SQLite tables" --priority 5
            eri-rpg add-action "Write tests for auth"
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)
        session_id = _get_session_id(project_path)

        # Ensure session exists
        existing = storage.get_session(session_id)
        if not existing:
            storage.create_session(session_id, project_name)

        # Add action
        next_action = storage.add_next_action(session_id, action, priority)
        click.echo(f"✓ Action added")
        click.echo(f"  ID: {next_action.id}")
        click.echo(f"  {action}")
        if priority > 0:
            click.echo(f"  Priority: {priority}")

    @cli.command(name="complete-action")
    @click.argument("action_id", type=int)
    def complete_action_cmd(action_id: int):
        """Mark a next action as completed.

        Example:
            eri-rpg complete-action 1
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        success = storage.complete_action(action_id)
        if success:
            click.echo(f"✓ Action {action_id} completed")
        else:
            click.echo(f"Action {action_id} not found", err=True)
            raise SystemExit(1)

    @cli.command(name="recall-decision")
    @click.option("--last", "-n", type=int, default=10, help="Show last N decisions")
    @click.option("--session", "-s", default=None, help="Filter by session ID")
    @click.option("--project", "-p", default=None, help="Project path (default: current directory)")
    def recall_decision_cmd(last: int, session: str, project: str):
        """List recent decisions chronologically.

        Example:
            eri-rpg recall-decision              # Last 10 decisions
            eri-rpg recall-decision --last 20   # Last 20 decisions
            eri-rpg recall-decision -s abc123   # Decisions from session abc123
        """
        try:
            from erirpg import storage
        except ImportError as e:
            click.echo(f"Error: Required modules not available: {e}", err=True)
            raise SystemExit(1)

        project_path = project or os.getcwd()
        project_name = _get_project_name(project_path)

        if session:
            decisions = storage.get_session_decisions(session)
        else:
            decisions = storage.get_recent_decisions(project_name, limit=last)

        if not decisions:
            click.echo("No decisions found")
            return

        click.echo(f"Decisions ({len(decisions)} found):")
        click.echo("")
        for d in decisions:
            date_str = d.timestamp.strftime("%Y-%m-%d %H:%M")
            click.echo(f"[{date_str}] {d.context}")
            click.echo(f"  → {d.decision}")
            if d.rationale:
                click.echo(f"    Why: {d.rationale}")
            click.echo("")
