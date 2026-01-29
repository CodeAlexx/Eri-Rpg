"""
Exploration Commands - Project structure and module discovery.

Commands:
- show: Show project structure and metadata
- find: Find modules matching a query
- impact: Analyze impact of changing a module
"""

import sys
import click
from datetime import datetime


def register(cli):
    """Register exploration commands with CLI."""

    @cli.command()
    @click.argument("project")
    def show(project: str):
        """Show project structure and metadata."""
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Project header
        click.echo(f"Project: {project}")
        if proj.description:
            click.echo(f"Description: {proj.description}")
        click.echo(f"Path: {proj.path}")
        click.echo(f"Language: {proj.lang}")

        # Index status
        if proj.indexed_at:
            age_days = (datetime.now() - proj.indexed_at).days
            age_str = "today" if age_days == 0 else f"{age_days}d ago"
            click.echo(f"Indexed: {age_str}")
        else:
            click.echo("Indexed: not indexed")

        click.echo("")

        # TODOs
        if proj.todos:
            click.echo("TODOs:")
            for i, todo in enumerate(proj.todos):
                click.echo(f"  [{i}] {todo}")
            click.echo("")

        # Notes
        if proj.notes:
            click.echo("Notes:")
            for line in proj.notes.split('\n'):
                click.echo(f"  {line}")
            click.echo("")

        # Try to load graph for stats
        try:
            graph = get_or_load_graph(proj)
            stats = graph.stats()

            # Use v2 knowledge storage for stats
            store = load_knowledge(proj.path, project)
            k_stats = store.stats()

            click.echo(f"Modules: {stats['modules']}")
            click.echo(f"Lines: {stats['total_lines']:,}")
            click.echo(f"Patterns: {k_stats['patterns']} stored")
            click.echo(f"Decisions: {k_stats['decisions']} stored")
            click.echo(f"Learnings: {k_stats['learnings']} stored")
            click.echo("")

            # Group by top-level directory
            dirs = {}
            for mod_path in sorted(graph.modules.keys()):
                parts = mod_path.split("/")
                top = parts[0] if len(parts) > 1 else "(root)"
                if top not in dirs:
                    dirs[top] = []
                dirs[top].append(mod_path)

            for dir_name, modules in sorted(dirs.items()):
                click.echo(f"{dir_name}/")
                for mod in modules[:5]:  # Show first 5
                    m = graph.get_module(mod)
                    ifaces = ", ".join(i.name for i in m.interfaces[:3])
                    if len(m.interfaces) > 3:
                        ifaces += "..."
                    click.echo(f"  {mod}: {ifaces}")
                if len(modules) > 5:
                    click.echo(f"  ... and {len(modules) - 5} more")

        except ValueError:
            click.echo("(not indexed - run: eri-rpg index {})".format(project))

    @cli.command()
    @click.argument("project")
    @click.argument("query")
    @click.option("-n", "--limit", default=10, help="Max results")
    def find(project: str, query: str, limit: int):
        """Find modules matching a query.

        Searches summaries, interface names, and docstrings.
        """
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph
        from erirpg.ops import find_modules

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        try:
            graph = get_or_load_graph(proj)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        results = find_modules(graph, query, limit=limit)

        if not results:
            click.echo(f"No modules match: {query}")
            click.echo("Try broader terms or: eri-rpg show {project}")
            return

        click.echo(f"Matching modules in {project}:")
        click.echo("")
        for mod, score in results:
            summary = mod.summary[:60] + "..." if len(mod.summary) > 60 else mod.summary
            click.echo(f"  {mod.path} ({score:.2f})")
            if summary:
                click.echo(f"    {summary}")

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    def impact(project: str, module_path: str):
        """Analyze impact of changing a module.

        Shows direct and transitive dependents.
        """
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph
        from erirpg.ops import analyze_impact

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        try:
            graph = get_or_load_graph(proj)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        try:
            analysis = analyze_impact(graph, module_path)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        click.echo(f"Impact analysis for {module_path}:")
        click.echo("")

        if analysis["summary"]:
            click.echo(f"Summary: {analysis['summary']}")

        click.echo(f"Interfaces: {', '.join(analysis['interfaces'])}")
        click.echo("")

        click.echo(f"Direct dependents ({len(analysis['direct_dependents'])}):")
        for d in analysis["direct_dependents"]:
            click.echo(f"  - {d}")

        if analysis["transitive_dependents"]:
            click.echo(f"\nTransitive dependents ({len(analysis['transitive_dependents'])}):")
            for d in analysis["transitive_dependents"][:5]:
                click.echo(f"  - {d}")
            if len(analysis["transitive_dependents"]) > 5:
                click.echo(f"  ... and {len(analysis['transitive_dependents']) - 5} more")

        click.echo(f"\nTotal affected: {analysis['total_affected']}")
        click.echo(f"Risk: {analysis['risk']}")
