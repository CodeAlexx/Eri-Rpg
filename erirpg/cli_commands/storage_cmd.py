"""
Storage CLI commands for SQLite graph operations.

Commands:
- db-stats: Show database statistics
- db-migrate: Migrate all JSON graphs to SQLite
- db-export: Export a project's graph to JSON
- find-interface: Find interfaces across all projects
- find-package: Find usage of external packages across projects
- find-dependents: Find dependents of a module across projects
"""

import click
from typing import Optional

from erirpg import storage


@click.command("db-stats")
def db_stats_cmd():
    """Show SQLite database statistics.

    Displays:
    - Total projects, modules, interfaces, edges
    - Database file size
    - Per-project breakdown
    """
    try:
        stats = storage.get_db_stats()
    except Exception as e:
        click.echo(f"Database not initialized: {e}")
        click.echo("Run 'eri-rpg index <project>' to create it.")
        return

    click.echo("=== Database Statistics ===")
    click.echo(f"Projects: {stats['projects']}")
    click.echo(f"Modules: {stats['total_modules']}")
    click.echo(f"Interfaces: {stats['total_interfaces']}")
    click.echo(f"Edges: {stats['total_edges']}")

    size_kb = stats['db_size_bytes'] / 1024
    if size_kb > 1024:
        click.echo(f"Size: {size_kb/1024:.1f} MB")
    else:
        click.echo(f"Size: {size_kb:.1f} KB")

    # Per-project stats
    project_stats = storage.get_project_stats()
    if project_stats:
        click.echo("\n=== Per-Project ===")
        for name, ps in sorted(project_stats.items()):
            click.echo(f"  {name}: {ps['modules']} modules, {ps['interfaces']} interfaces, {ps['lines']} lines")


@click.command("db-migrate")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def db_migrate_cmd(verbose: bool):
    """Migrate all JSON graphs to SQLite database.

    Reads all registered projects and imports their graph.json files
    into the central SQLite database.
    """
    click.echo("Migrating JSON graphs to SQLite...")

    results = storage.migrate_all_projects()

    if not results:
        click.echo("No projects found to migrate.")
        return

    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    for name, ok in sorted(results.items()):
        status = "✓" if ok else "✗"
        if verbose or not ok:
            click.echo(f"  {status} {name}")

    click.echo(f"\nMigrated: {success}/{len(results)} projects")
    if failed:
        click.echo(f"Failed: {failed} (may not have graph.json)")


@click.command("db-export")
@click.argument("project")
@click.argument("output", required=False)
def db_export_cmd(project: str, output: Optional[str]):
    """Export a project's graph from SQLite to JSON.

    Arguments:
        project: Project name to export
        output: Output file path (default: <project>-graph.json)
    """
    output_path = output or f"{project}-graph.json"

    if storage.export_to_json(project, output_path):
        click.echo(f"Exported to: {output_path}")
    else:
        click.echo(f"Project '{project}' not found in database.")


@click.command("find-interface")
@click.argument("name")
@click.option("--type", "-t", "iface_type", help="Filter by type: class, function, method, const")
def find_interface_cmd(name: str, iface_type: Optional[str]):
    """Find interfaces across all projects.

    Searches for classes, functions, methods, and constants
    by name across all indexed projects.

    Supports LIKE patterns with %:
        find-interface "Auth%"     # Starts with Auth
        find-interface "%Manager"  # Ends with Manager
        find-interface "%auth%"    # Contains auth

    Examples:
        eri-rpg find-interface AuthManager
        eri-rpg find-interface "parse%" --type function
    """
    results = storage.find_interface_across_projects(name, iface_type)

    if not results:
        click.echo(f"No interfaces found matching '{name}'")
        return

    click.echo(f"Found {len(results)} matches:\n")

    current_project = None
    for r in results:
        if r.project != current_project:
            current_project = r.project
            click.echo(f"[{r.project}]")

        loc = f":{r.line}" if r.line else ""
        doc = f" - {r.context[:50]}..." if r.context else ""
        click.echo(f"  {r.match_type} {r.match_name} ({r.module_path}{loc}){doc}")


@click.command("find-package")
@click.argument("package")
def find_package_cmd(package: str):
    """Find usage of an external package across projects.

    Shows all modules that import the specified package.

    Examples:
        eri-rpg find-package requests
        eri-rpg find-package click
        eri-rpg find-package torch
    """
    results = storage.find_external_dep_usage(package)

    if not results:
        click.echo(f"Package '{package}' not used in any indexed project.")
        return

    click.echo(f"Found {len(results)} usages of '{package}':\n")

    current_project = None
    for project, module_path in results:
        if project != current_project:
            current_project = project
            click.echo(f"[{project}]")
        click.echo(f"  {module_path}")


@click.command("find-dependents")
@click.argument("module_path")
def find_dependents_cmd(module_path: str):
    """Find modules depending on a path across projects.

    Useful for finding impact when a commonly-used module
    pattern exists in multiple codebases.

    Examples:
        eri-rpg find-dependents utils.py
        eri-rpg find-dependents config.py
    """
    results = storage.find_dependents_across_projects(module_path)

    if not results:
        click.echo(f"No modules depend on '{module_path}' across projects.")
        return

    click.echo(f"Found {len(results)} dependents of '{module_path}':\n")

    current_project = None
    for project, dep_path in results:
        if project != current_project:
            current_project = project
            click.echo(f"[{project}]")
        click.echo(f"  {dep_path}")


def register(cli: click.Group) -> None:
    """Register storage commands with the CLI."""
    cli.add_command(db_stats_cmd)
    cli.add_command(db_migrate_cmd)
    cli.add_command(db_export_cmd)
    cli.add_command(find_interface_cmd)
    cli.add_command(find_package_cmd)
    cli.add_command(find_dependents_cmd)
