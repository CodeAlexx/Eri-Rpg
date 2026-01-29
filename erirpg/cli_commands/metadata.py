"""
Metadata Commands - Project metadata management.

Commands (standard tier):
- describe: Set project description
- todo: Manage project TODOs
- notes: Manage project notes
- decision: Record an architectural decision
- decisions: List all architectural decisions
- log: Log an action to project history
- knowledge: Show all stored knowledge for a project
"""

import sys
import click
from datetime import datetime

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register metadata commands with CLI."""

    @cli.command("describe")
    @click.argument("project")
    @click.argument("description")
    @tier_required("standard")
    def set_description(project: str, description: str):
        """Set project description.

        Example:
            eri-rpg describe myproject "ML training toolkit for LoRA/SDXL"
        """
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        proj.description = description
        registry.save()

        click.echo(f"✓ Description set for {project}")
        click.echo(f"  {description}")

    @cli.command("todo")
    @click.argument("project")
    @click.argument("item", required=False)
    @click.option("-l", "--list", "list_todos", is_flag=True, help="List all todos")
    @click.option("-d", "--done", "done_index", type=int, help="Mark todo as done by index")
    def manage_todos(project: str, item: str, list_todos: bool, done_index: int):
        """Manage project TODOs.

        Examples:
            eri-rpg todo myproject "Add config validation"
            eri-rpg todo myproject --list
            eri-rpg todo myproject --done 0
        """
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # List todos
        if list_todos or (not item and done_index is None):
            if not proj.todos:
                click.echo(f"No TODOs for {project}.")
                click.echo(f"\nAdd one: eri-rpg todo {project} \"<item>\"")
                return

            click.echo(f"TODOs for {project}:")
            for i, todo in enumerate(proj.todos):
                click.echo(f"  [{i}] {todo}")
            return

        # Mark as done
        if done_index is not None:
            if done_index < 0 or done_index >= len(proj.todos):
                click.echo(f"Error: Invalid index {done_index}. Valid: 0-{len(proj.todos)-1}", err=True)
                sys.exit(1)

            removed = proj.todos.pop(done_index)
            registry.save()
            click.echo(f"✓ Marked done: {removed}")
            return

        # Add new todo
        if item:
            proj.todos.append(item)
            registry.save()
            click.echo(f"✓ Added TODO [{len(proj.todos)-1}]: {item}")

    @cli.command("notes")
    @click.argument("project")
    @click.argument("note", required=False)
    @click.option("--show", "show_notes", is_flag=True, help="Show notes")
    @click.option("--clear", "clear_notes", is_flag=True, help="Clear all notes")
    @click.option("--append", "append_mode", is_flag=True, help="Append to existing notes")
    def manage_notes(project: str, note: str, show_notes: bool, clear_notes: bool, append_mode: bool):
        """Manage project notes.

        Examples:
            eri-rpg notes myproject "Needs CUDA 12.1+"
            eri-rpg notes myproject --show
            eri-rpg notes myproject "Additional info" --append
            eri-rpg notes myproject --clear
        """
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Show notes
        if show_notes or (not note and not clear_notes):
            if not proj.notes:
                click.echo(f"No notes for {project}.")
                click.echo(f"\nAdd notes: eri-rpg notes {project} \"<note>\"")
                return

            click.echo(f"Notes for {project}:")
            click.echo("-" * 40)
            click.echo(proj.notes)
            return

        # Clear notes
        if clear_notes:
            proj.notes = ""
            registry.save()
            click.echo(f"✓ Notes cleared for {project}")
            return

        # Set/append notes
        if note:
            if append_mode and proj.notes:
                proj.notes = proj.notes + "\n" + note
            else:
                proj.notes = note
            registry.save()
            click.echo(f"✓ Notes {'appended' if append_mode else 'set'} for {project}")

    @cli.command("decision")
    @click.argument("project")
    @click.argument("title")
    @click.option("--reason", "-r", required=True, help="Reason for the decision")
    @click.option("--affects", "-a", help="Comma-separated list of affected files")
    @click.option("--alternatives", help="Comma-separated list of alternatives considered")
    def add_decision(project: str, title: str, reason: str, affects: str, alternatives: str):
        """Record an architectural decision.

        Example:
            eri-rpg decision myproject "Use PostgreSQL" \\
                --reason "Need concurrent writes" \\
                --affects "src/db.py,src/models.py" \\
                --alternatives "SQLite,MySQL"
        """
        from erirpg.registry import Registry
        from erirpg.memory import StoredDecision, load_knowledge, save_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Use v2 knowledge storage
        store = load_knowledge(proj.path, project)

        # Parse comma-separated lists
        affects_list = [a.strip() for a in affects.split(",")] if affects else []
        alternatives_list = [a.strip() for a in alternatives.split(",")] if alternatives else []

        # Create decision ID
        decision_id = f"dec-{len(store.decisions) + 1:03d}"

        decision = StoredDecision(
            id=decision_id,
            date=datetime.now(),
            title=title,
            reason=reason,
            affects=affects_list,
            alternatives=alternatives_list,
        )

        store.add_decision(decision)
        save_knowledge(proj.path, store)

        click.echo(f"✓ Recorded decision: {decision_id}")
        click.echo(f"  Title: {title}")
        click.echo(f"  Reason: {reason}")
        if affects_list:
            click.echo(f"  Affects: {', '.join(affects_list)}")
        if alternatives_list:
            click.echo(f"  Alternatives: {', '.join(alternatives_list)}")

    @cli.command("decisions")
    @click.argument("project")
    def list_decisions(project: str):
        """List all architectural decisions for a project.

        Example:
            eri-rpg decisions myproject
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Use v2 knowledge storage
        store = load_knowledge(proj.path, project)
        decisions = store.decisions

        if not decisions:
            click.echo("No decisions recorded.")
            click.echo(f"\nAdd one: eri-rpg decision {project} \"<title>\" --reason \"<why>\"")
            return

        click.echo(f"Decisions for {project}:")
        click.echo("=" * 50)
        for d in decisions:
            age_days = (datetime.now() - d.date).days
            age_str = "today" if age_days == 0 else f"{age_days}d ago"
            click.echo(f"\n[{d.id}] {d.title} ({age_str})")
            click.echo(f"  Reason: {d.reason}")
            if d.affects:
                click.echo(f"  Affects: {', '.join(d.affects)}")
            if d.alternatives:
                click.echo(f"  Alternatives: {', '.join(d.alternatives)}")

    @cli.command()
    @click.argument("action")
    @click.option("--feature", "-f", help="Feature name")
    @click.option("--from-proj", help="Source project")
    @click.option("--to-path", help="Target path")
    def log(action: str, feature: str, from_proj: str, to_path: str):
        """Log an action to project history.

        Records transplants, modifications, and other actions.

        Example:
            eri-rpg log "Transplanted masked loss" \\
                -f masked_loss --from-proj onetrainer \\
                --to-path eritrainer/training/masked_loss.py
        """
        from erirpg.state import State
        from erirpg.knowledge import HistoryEntry

        entry = HistoryEntry(
            date=datetime.now(),
            action="transplant" if "transplant" in action.lower() else "modify",
            description=action,
            feature=feature,
            from_project=from_proj,
            to_path=to_path,
        )

        state = State.load()
        state.log(entry.action, action)

        click.echo(f"✓ Logged: {action}")
        if feature:
            click.echo(f"  Feature: {feature}")
        if from_proj:
            click.echo(f"  From: {from_proj}")
        if to_path:
            click.echo(f"  To: {to_path}")

    @cli.command("knowledge")
    @click.argument("project")
    def show_knowledge(project: str):
        """Show all stored knowledge for a project.

        Displays learnings, patterns, decisions, and statistics.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Use v2 knowledge storage
        store = load_knowledge(proj.path, project)
        stats = store.stats()

        click.echo(f"Knowledge for {project}")
        click.echo("=" * 40)
        click.echo("")

        click.echo(f"Learnings: {stats['learnings']}")
        if store.learnings:
            for path, learning in sorted(store.learnings.items()):
                age_days = (datetime.now() - learning.learned_at).days
                age_str = "today" if age_days == 0 else f"{age_days}d ago"
                click.echo(f"  • {path} ({age_str})")
                click.echo(f"    {learning.summary}")

        click.echo("")
        click.echo(f"Patterns: {stats['patterns']}")
        if store.patterns:
            for name, desc in sorted(store.patterns.items()):
                click.echo(f"  • {name}: {desc[:60]}{'...' if len(desc) > 60 else ''}")

        click.echo("")
        click.echo(f"Decisions: {stats['decisions']}")
        if store.decisions:
            for d in store.decisions[:5]:  # Show first 5
                click.echo(f"  • [{d.id}] {d.title}")
            if len(store.decisions) > 5:
                click.echo(f"  ... and {len(store.decisions) - 5} more")

        click.echo("")
        click.echo(f"Runs: {stats['runs']}")

        # Token savings estimate
        if stats['learnings'] > 0:
            click.echo("")
            click.echo("Token savings estimate:")
            # Rough estimate: 500 tokens per learning vs 2000 tokens for source
            saved = stats['learnings'] * 1500
            click.echo(f"  ~{saved:,} tokens saved per context generation")
