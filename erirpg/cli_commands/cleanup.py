"""
Cleanup Commands - Run management and housekeeping.

Commands (full tier):
- cleanup: List and prune abandoned runs
- runs: List runs for a project
"""

import json
import sys
import click
from datetime import datetime, timedelta
from pathlib import Path

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register cleanup commands with CLI."""

    @cli.command("cleanup")
    @click.argument("project")
    @click.option("--prune", is_flag=True, help="Delete stale/abandoned runs")
    @click.option("--days", default=7, help="Consider runs older than N days as stale (default: 7)")
    @click.option("--force", is_flag=True, help="Delete without confirmation")
    @tier_required("full")
    def cleanup_cmd(project: str, prune: bool, days: int, force: bool):
        """List and optionally prune abandoned runs.

        Stale runs are IN_PROGRESS runs that haven't been touched in N days.

        \b
        Examples:
            eri-rpg cleanup myproject          # List runs
            eri-rpg cleanup myproject --prune  # Delete stale runs
            eri-rpg cleanup myproject --prune --days 1  # Delete runs older than 1 day
        """
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        run_dir = Path(proj.path) / ".eri-rpg" / "runs"
        if not run_dir.exists():
            click.echo(f"No runs found for {project}")
            return

        runs = list(run_dir.glob("*.json"))
        if not runs:
            click.echo(f"No runs found for {project}")
            return

        # Analyze runs
        now = datetime.now()
        stale_threshold = now - timedelta(days=days)

        completed = []
        in_progress = []
        stale = []

        for run_file in runs:
            try:
                with open(run_file) as f:
                    run_data = json.load(f)

                run_id = run_data.get("id", run_file.stem)
                goal = run_data.get("spec", {}).get("goal", "Unknown")[:40]
                started = run_data.get("started_at", "")
                completed_at = run_data.get("completed_at")

                # Parse timestamp
                try:
                    if started:
                        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00").split("+")[0])
                    else:
                        started_dt = datetime.fromtimestamp(run_file.stat().st_mtime)
                except Exception:
                    started_dt = datetime.fromtimestamp(run_file.stat().st_mtime)

                run_info = {
                    "id": run_id,
                    "goal": goal,
                    "started": started_dt,
                    "file": run_file,
                }

                if completed_at:
                    completed.append(run_info)
                elif started_dt < stale_threshold:
                    stale.append(run_info)
                else:
                    in_progress.append(run_info)

            except Exception as e:
                click.echo(f"Warning: Could not parse {run_file.name}: {e}", err=True)

        # Show summary
        click.echo(f"Runs for {project}:")
        click.echo(f"  Completed: {len(completed)}")
        click.echo(f"  In Progress: {len(in_progress)}")
        click.echo(f"  Stale (>{days} days): {len(stale)}")
        click.echo("")

        if stale:
            click.echo("Stale runs:")
            for run in stale:
                age = (now - run["started"]).days
                click.echo(f"  {run['id']}: {run['goal']}... ({age} days old)")
            click.echo("")

        if in_progress:
            click.echo("Active runs:")
            for run in in_progress:
                age = (now - run["started"]).days
                click.echo(f"  {run['id']}: {run['goal']}... ({age} days old)")
            click.echo("")

        if prune and stale:
            if not force:
                click.confirm(f"Delete {len(stale)} stale run(s)?", abort=True)

            for run in stale:
                run["file"].unlink()
                click.echo(f"Deleted: {run['id']}")

            click.echo(f"\nPruned {len(stale)} stale run(s).")

            # Also clean up preflight state if no active runs
            if not in_progress:
                preflight_file = Path(proj.path) / ".eri-rpg" / "preflight_state.json"
                if preflight_file.exists():
                    preflight_file.unlink()
                    click.echo("Cleared stale preflight state.")
        elif prune:
            click.echo("No stale runs to prune.")

    @cli.command("runs")
    @click.argument("project")
    @click.option("--all", "show_all", is_flag=True, help="Show all runs including completed")
    def runs_cmd(project: str, show_all: bool):
        """List runs for a project.

        \b
        Example:
            eri-rpg runs myproject
            eri-rpg runs myproject --all
        """
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        run_dir = Path(proj.path) / ".eri-rpg" / "runs"
        if not run_dir.exists():
            click.echo(f"No runs found for {project}")
            return

        runs = sorted(run_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            click.echo(f"No runs found for {project}")
            return

        click.echo(f"Runs for {project}:")
        click.echo("")

        for run_file in runs:
            try:
                with open(run_file) as f:
                    run_data = json.load(f)

                run_id = run_data.get("id", run_file.stem)
                goal = run_data.get("spec", {}).get("goal", "Unknown")[:50]
                completed_at = run_data.get("completed_at")

                if completed_at and not show_all:
                    continue

                status = "COMPLETED" if completed_at else "IN_PROGRESS"
                status_icon = "✓" if completed_at else "○"

                # Get progress
                plan = run_data.get("plan", {})
                steps = plan.get("steps", [])
                completed_steps = sum(1 for s in steps if s.get("status") == "completed")
                total_steps = len(steps)

                click.echo(f"  {status_icon} {run_id}")
                click.echo(f"    Goal: {goal}...")
                click.echo(f"    Status: {status} ({completed_steps}/{total_steps} steps)")
                click.echo("")

            except Exception as e:
                click.echo(f"  ? {run_file.name} (error: {e})")

        click.echo("")
        click.echo("Resume a run: eri-rpg goal-status <project>")
        click.echo("Cleanup stale: eri-rpg cleanup <project> --prune")
