"""
Memory Commands - V2 knowledge storage management.

Commands:
- memory status: Show memory stats and staleness
- memory search: Search learnings by keyword
- memory stale: List stale learnings
- memory refresh: Update stale learning
- memory migrate: Migrate v1 knowledge to v2
"""

import os
import sys
import click
from datetime import datetime


def register(cli):
    """Register memory group commands with CLI."""

    @cli.group()
    def memory():
        """Memory management commands (v2 storage).

        The v2 memory system stores knowledge in a separate knowledge.json
        file that survives reindexing. Commands:

        \b
            memory status    - Show memory stats and staleness
            memory search    - Search learnings by keyword
            memory stale     - List stale learnings
            memory refresh   - Update stale learning
            memory migrate   - Migrate v1 knowledge to v2
        """
        pass

    @memory.command("status")
    @click.argument("project")
    def memory_status(project: str):
        """Show memory status for a project.

        Displays v2 knowledge store stats, staleness info, and health metrics.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, get_knowledge_path
        from erirpg.migration import get_migration_status

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Get migration status
        migration = get_migration_status(proj.path)

        click.echo(f"Memory Status for {project}")
        click.echo("=" * 40)
        click.echo("")

        # Storage info
        click.echo("Storage:")
        click.echo(f"  graph.json: {'exists' if migration['graph_exists'] else 'missing'}")
        click.echo(f"  knowledge.json: {'exists' if migration['knowledge_exists'] else 'missing'}")

        if migration['has_embedded_knowledge']:
            click.echo("")
            click.echo("WARNING: v1 knowledge embedded in graph.json")
            click.echo(f"  Embedded learnings: {migration['embedded_learnings']}")
            click.echo(f"  Run: eri-rpg memory migrate {project}")

        # v2 knowledge stats
        if migration['knowledge_exists']:
            knowledge_path = get_knowledge_path(proj.path)
            store = load_knowledge(proj.path, project)
            stats = store.stats()

            click.echo("")
            click.echo("v2 Knowledge Store:")
            click.echo(f"  Learnings: {stats['learnings']}")
            click.echo(f"  Decisions: {stats['decisions']}")
            click.echo(f"  Patterns: {stats['patterns']}")
            click.echo(f"  Runs tracked: {stats['runs']}")

            # Staleness check
            stale = store.get_stale_learnings(proj.path)
            fresh = store.get_fresh_learnings(proj.path)

            click.echo("")
            click.echo("Staleness:")
            click.echo(f"  Fresh: {len(fresh)}")
            click.echo(f"  Stale: {len(stale)}")

            if stale:
                click.echo("")
                click.echo("Stale learnings need refresh:")
                for path in stale[:5]:
                    click.echo(f"  - {path}")
                if len(stale) > 5:
                    click.echo(f"  ... and {len(stale) - 5} more")
                click.echo(f"\nRun: eri-rpg memory stale {project}")

            # Health score
            total = stats['learnings']
            if total > 0:
                health = (len(fresh) / total) * 100
                click.echo("")
                click.echo(f"Health Score: {health:.0f}%")
        else:
            click.echo("")
            click.echo("No v2 knowledge store yet.")
            click.echo(f"Create learnings with: eri-rpg learn {project} <module>")

    @memory.command("search")
    @click.argument("project")
    @click.argument("query")
    @click.option("-n", "--limit", default=10, help="Max results")
    def memory_search(project: str, query: str, limit: int):
        """Search learnings by keyword.

        Searches summaries, purposes, functions, and gotchas.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, get_knowledge_path

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        knowledge_path = get_knowledge_path(proj.path)
        if not os.path.exists(knowledge_path):
            click.echo(f"No knowledge.json found for {project}")
            click.echo(f"Create learnings first: eri-rpg learn {project} <module>")
            return

        store = load_knowledge(proj.path, project)
        results = store.search(query, limit=limit)

        if not results:
            click.echo(f"No learnings match: {query}")
            return

        click.echo(f"Search results for '{query}':")
        click.echo("")

        for path, learning, score in results:
            is_stale = learning.is_stale(proj.path)
            stale_marker = " [STALE]" if is_stale else ""
            click.echo(f"  {path} (score: {score:.2f}){stale_marker}")
            click.echo(f"    {learning.summary}")
            click.echo("")

    @memory.command("stale")
    @click.argument("project")
    def memory_stale(project: str):
        """List all stale learnings.

        Shows learnings whose source files have changed since
        the learning was created.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, get_knowledge_path

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        knowledge_path = get_knowledge_path(proj.path)
        if not os.path.exists(knowledge_path):
            click.echo(f"No knowledge.json found for {project}")
            return

        store = load_knowledge(proj.path, project)
        stale = store.get_stale_learnings(proj.path)

        if not stale:
            click.echo(f"All learnings are fresh!")
            return

        click.echo(f"Stale learnings in {project}:")
        click.echo("")

        for path in stale:
            learning = store.get_learning(path)
            if learning:
                age_days = (datetime.now() - learning.learned_at).days
                click.echo(f"  {path}")
                click.echo(f"    Learned: {age_days} days ago")
                click.echo(f"    Summary: {learning.summary}")
                click.echo("")

        click.echo("To refresh a learning:")
        click.echo(f"  eri-rpg memory refresh {project} <module_path>")
        click.echo("")
        click.echo("Or re-learn from scratch:")
        click.echo(f"  eri-rpg relearn {project} <module_path>")

    @memory.command("refresh")
    @click.argument("project")
    @click.argument("module_path")
    def memory_refresh(project: str, module_path: str):
        """Refresh a stale learning.

        Updates the CodeRef to current file state without changing
        the learning content. Use 'relearn' if content changed.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, save_knowledge, get_knowledge_path
        from erirpg.refs import CodeRef

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        knowledge_path = get_knowledge_path(proj.path)
        if not os.path.exists(knowledge_path):
            click.echo(f"No knowledge.json found for {project}")
            sys.exit(1)

        store = load_knowledge(proj.path, project)
        learning = store.get_learning(module_path)

        if not learning:
            click.echo(f"No learning found for: {module_path}")
            sys.exit(1)

        # Check if source file exists
        file_path = os.path.join(proj.path, module_path)
        if not os.path.exists(file_path):
            click.echo(f"Source file no longer exists: {module_path}")
            click.echo("Consider removing this learning or updating the path.")
            sys.exit(1)

        # Check if actually stale
        if not learning.is_stale(proj.path):
            click.echo(f"Learning is not stale: {module_path}")
            return

        # Create new CodeRef with current file state
        try:
            new_ref = CodeRef.from_file(proj.path, module_path)
            learning.source_ref = new_ref
            learning.version += 1
            store.add_learning(learning)
            save_knowledge(proj.path, store)

            click.echo(f"Refreshed learning: {module_path}")
            click.echo(f"  New version: {learning.version}")
            click.echo("")
            click.echo("Note: Only the CodeRef was updated. If the code logic changed,")
            click.echo(f"consider re-learning: eri-rpg relearn {project} {module_path}")
        except Exception as e:
            click.echo(f"Error refreshing: {e}", err=True)
            sys.exit(1)

    @memory.command("migrate")
    @click.argument("project")
    @click.option("--force", is_flag=True, help="Force migration even if knowledge.json exists")
    def memory_migrate(project: str, force: bool):
        """Migrate v1 knowledge to v2 format.

        Extracts knowledge from graph.json into separate knowledge.json
        and creates CodeRefs for learnings.
        """
        from erirpg.registry import Registry
        from erirpg.migration import (
            check_migration_needed,
            migrate_knowledge,
            get_migration_status,
        )

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check migration status
        status = get_migration_status(proj.path)

        if not status['has_embedded_knowledge']:
            click.echo("No v1 knowledge to migrate.")
            return

        if status['knowledge_exists'] and not force:
            click.echo("knowledge.json already exists.")
            click.echo("Use --force to overwrite.")
            return

        # Perform migration
        click.echo(f"Migrating knowledge for {project}...")

        result = migrate_knowledge(proj.path, project)

        if result['migrated']:
            click.echo("")
            click.echo("Migration complete:")
            click.echo(f"  Learnings: {result['learnings']}")
            click.echo(f"  Decisions: {result['decisions']}")
            click.echo(f"  Patterns: {result['patterns']}")
            click.echo(f"  CodeRefs created: {result['refs_created']}")
            if result['refs_failed'] > 0:
                click.echo(f"  CodeRefs failed (files missing): {result['refs_failed']}")
            click.echo("")
            click.echo("Knowledge now stored in knowledge.json (survives reindex)")
        else:
            click.echo(f"Migration failed: {result['error']}", err=True)
            sys.exit(1)
