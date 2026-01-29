"""
Session Commands - Session state and gap closure.

Commands:
- session: Show or update current session state
- handoff: Generate handoff summary for next session
- gaps: Show gaps from verification failures
"""

import sys
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

        Example:
            eri-rpg switch myapp
            eri-rpg switch eritrainer
        """
        from erirpg.state import State
        from erirpg.memory import get_latest_session, save_session_state

        state = State.load()

        # Validate target project exists
        target_proj = registry.get(project)
        if not target_proj:
            click.echo(f"Project '{project}' not found in registry")
            click.echo("")
            click.echo("Registered projects:")
            for p in registry.list():
                click.echo(f"  - {p.name}: {p.path}")
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

        # Switch to new project
        state.set_active_project(project)
        click.echo(f"Switched to: {project}")
        click.echo(f"Path: {target_proj.path}")

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
