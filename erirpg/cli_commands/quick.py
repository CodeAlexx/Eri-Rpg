"""
Quick Fix Commands - Lightweight mode for simple changes.

Commands:
- quick: Start a quick fix on a single file
- quick-done: Complete a quick fix and commit
- quick-cancel: Cancel a quick fix and restore
- quick-status: Check if a quick fix is active
"""

import sys
import click


def register(cli):
    """Register quick fix commands with CLI."""

    @cli.command("quick")
    @click.argument("project")
    @click.argument("file_path")
    @click.argument("description")
    @click.option("--no-commit", is_flag=True, help="Don't auto-commit after edit")
    @click.option("--dry-run", is_flag=True, help="Show what would happen without doing it")
    def quick_cmd(project: str, file_path: str, description: str, no_commit: bool, dry_run: bool):
        """Start a quick fix on a single file.

        Lightweight mode for simple, focused changes without full spec ceremony.
        No run state, no steps - just snapshot, edit, commit.

        \b
        Examples:
            eri-rpg quick myproject src/utils.py "Fix off-by-one error"
            eri-rpg quick eritrainer train.py "Add debug logging"

        After editing, complete with: eri-rpg quick-done <project>
        Or cancel with: eri-rpg quick-cancel <project>
        """
        from erirpg.quick import quick_fix

        try:
            result = quick_fix(
                project=project,
                file_path=file_path,
                description=description,
                auto_commit=not no_commit,
                dry_run=dry_run,
            )
            if result == "ready":
                click.echo("")
                click.echo("Now edit the file. When done:")
                click.echo(f"  eri-rpg quick-done {project}")
                click.echo("")
                click.echo("To cancel and restore:")
                click.echo(f"  eri-rpg quick-cancel {project}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("quick-done")
    @click.argument("project")
    @click.option("--no-commit", is_flag=True, help="Don't commit changes")
    @click.option("-m", "--message", default=None, help="Custom commit message")
    def quick_done_cmd(project: str, no_commit: bool, message: str):
        """Complete a quick fix and commit changes.

        \b
        Example:
            eri-rpg quick-done myproject
            eri-rpg quick-done myproject -m "Better commit message"
        """
        from erirpg.quick import quick_done

        try:
            result = quick_done(
                project=project,
                auto_commit=not no_commit,
                commit_message=message,
            )
            if result:
                click.echo("")
                click.echo("Quick fix completed successfully.")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("quick-cancel")
    @click.argument("project")
    def quick_cancel_cmd(project: str):
        """Cancel a quick fix and restore the original file.

        \b
        Example:
            eri-rpg quick-cancel myproject
        """
        from erirpg.quick import quick_cancel

        try:
            quick_cancel(project)
            click.echo("")
            click.echo("Quick fix cancelled.")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("quick-status")
    @click.argument("project")
    def quick_status_cmd(project: str):
        """Check if a quick fix is active.

        \b
        Example:
            eri-rpg quick-status myproject
        """
        from erirpg.quick import load_quick_fix_state
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        state = load_quick_fix_state(proj.path)

        if not state or not state.get("quick_fix_active"):
            click.echo(f"No active quick fix for {project}")
            return

        click.echo(f"Quick fix active:")
        click.echo(f"  File: {state.get('target_file')}")
        click.echo(f"  Description: {state.get('description')}")
        click.echo(f"  Started: {state.get('timestamp')}")
        click.echo("")
        click.echo(f"Complete: eri-rpg quick-done {project}")
        click.echo(f"Cancel: eri-rpg quick-cancel {project}")
