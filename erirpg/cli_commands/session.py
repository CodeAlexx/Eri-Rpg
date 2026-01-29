"""
Session Commands - Session state and gap closure (GSD-inspired).

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
