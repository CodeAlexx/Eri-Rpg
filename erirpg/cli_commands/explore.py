"""
Exploration Commands - Project structure and module discovery.

Commands (standard tier):
- show: Show project structure and metadata
- find: Find modules matching a query
- impact: Analyze impact of changing a module
"""

import sys
import click
from datetime import datetime

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register exploration commands with CLI."""

    @cli.command()
    @click.argument("project")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @tier_required("standard")
    def show(project: str, as_json: bool):
        """Show project structure and metadata."""
        import json as json_lib
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Try to load graph for stats
        try:
            graph = get_or_load_graph(proj)
            stats = graph.stats()

            # Use v2 knowledge storage for stats
            store = load_knowledge(proj.path, project)
            k_stats = store.stats()

            if as_json:
                # JSON output
                output = {
                    "project": project,
                    "description": proj.description,
                    "path": proj.path,
                    "language": proj.lang,
                    "indexed_at": proj.indexed_at.isoformat() if proj.indexed_at else None,
                    "stats": {
                        "modules": stats['modules'],
                        "lines": stats['total_lines'],
                        "interfaces": stats['total_interfaces'],
                        "edges": stats['edges'],
                        "patterns": k_stats['patterns'],
                        "decisions": k_stats['decisions'],
                        "learnings": k_stats['learnings'],
                    }
                }
                click.echo(json_lib.dumps(output, indent=2))
            else:
                # Human-readable output
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

                click.echo(f"Modules: {stats['modules']}")
                click.echo(f"Lines: {stats['total_lines']:,}")
                click.echo(f"Interfaces: {stats['total_interfaces']}")
                click.echo(f"Edges: {stats['edges']}")
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
            if as_json:
                click.echo(json_lib.dumps({"error": "not indexed"}, indent=2))
            else:
                click.echo("(not indexed - run: eri-rpg index {})".format(project))

    @cli.command()
    @click.argument("project")
    @click.argument("query")
    @click.option("-n", "--limit", default=10, help="Max results")
    @tier_required("standard")
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
    @click.option("--depth", type=int, default=None, help="Maximum dependency depth to analyze")
    @tier_required("standard")
    def impact(project: str, module_path: str, depth: int):
        """Analyze impact of changing a module.

        Shows direct and transitive dependents.
        """
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph

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
            analysis = graph.impact_analysis(module_path, depth=depth)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        click.echo(f"Impact analysis for {module_path}:")
        click.echo("")

        if analysis["summary"]:
            click.echo(f"Summary: {analysis['summary']}")

        click.echo(f"Interfaces: {', '.join(analysis['interfaces'])}")
        click.echo(f"Lines: {analysis['lines']}")
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

    @cli.command()
    @click.argument("interface_name")
    @click.option("--all-projects", is_flag=True, help="Search across all projects")
    @tier_required("standard")
    def search(interface_name: str, all_projects: bool):
        """Find interface by name.

        Searches for interfaces matching the given name.
        """
        if all_projects:
            from erirpg.storage import find_interface_across_projects

            results = find_interface_across_projects(f"%{interface_name}%")

            if not results:
                click.echo(f"No interfaces match: {interface_name}")
                return

            click.echo(f"Found {len(results)} interfaces matching '{interface_name}':")
            click.echo("")

            current_project = None
            for result in results:
                if result.project != current_project:
                    current_project = result.project
                    click.echo(f"\n{current_project}:")

                click.echo(f"  {result.module_path}:{result.line}")
                click.echo(f"    {result.match_type} {result.match_name}")
                if result.context:
                    context = result.context[:70] + "..." if len(result.context) > 70 else result.context
                    click.echo(f"    {context}")
        else:
            click.echo("Error: --all-projects flag is required for search command", err=True)
            sys.exit(1)

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    @click.option("--reverse", is_flag=True, help="Show dependents instead of dependencies")
    @tier_required("standard")
    def deps(project: str, module_path: str, reverse: bool):
        """Show dependencies or dependents of a module.

        By default shows dependencies. Use --reverse to show dependents.
        """
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph

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

        module = graph.get_module(module_path)
        if not module:
            click.echo(f"Error: Module not found: {module_path}", err=True)
            sys.exit(1)

        if reverse:
            # Show dependents
            direct = graph.get_dependents(module_path)
            transitive = graph.get_transitive_dependents(module_path)

            click.echo(f"Dependents of {module_path}:")
            click.echo("")
            click.echo(f"Direct ({len(direct)}):")
            for d in direct:
                click.echo(f"  - {d}")

            transitive_only = [t for t in transitive if t not in direct]
            if transitive_only:
                click.echo(f"\nTransitive ({len(transitive_only)}):")
                for d in transitive_only[:10]:
                    click.echo(f"  - {d}")
                if len(transitive_only) > 10:
                    click.echo(f"  ... and {len(transitive_only) - 10} more")
        else:
            # Show dependencies
            deps_info = graph.get_dependencies(module_path, include_external=True)

            click.echo(f"Dependencies of {module_path}:")
            click.echo("")
            click.echo(f"Internal ({len(deps_info['internal'])}):")
            for d in deps_info['internal']:
                click.echo(f"  - {d}")

            if deps_info.get('external'):
                click.echo(f"\nExternal ({len(deps_info['external'])}):")
                for d in deps_info['external']:
                    click.echo(f"  - {d}")
