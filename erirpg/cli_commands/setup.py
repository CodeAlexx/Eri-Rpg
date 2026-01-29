"""
Setup Commands - Project registration and indexing.

Commands:
- add: Register a project
- remove: Remove a project
- list: List registered projects
- index: Index a project's codebase
"""

import sys
import click

from erirpg.registry import Registry, detect_project_language
from erirpg.config import get_mode
from erirpg.indexer import index_project


def register(cli):
    """Register setup commands with CLI."""

    @cli.command()
    @click.argument("name")
    @click.argument("path", type=click.Path())
    @click.option("--lang", default=None, type=click.Choice(["python", "rust", "c", "mojo"]),
                  help="Programming language (auto-detected if not specified). Supported: python, rust, c, mojo.")
    def add(name: str, path: str, lang: str):
        """Register a project.

        NAME: Unique project identifier
        PATH: Path to project root
        """
        registry = Registry.get_instance()

        # Auto-detect language if not specified
        if lang is None:
            lang = detect_project_language(path)
            if lang == "unknown":
                click.echo("Warning: Could not detect language, defaulting to 'python'", err=True)
                lang = "python"
            else:
                click.echo(f"Auto-detected language: {lang}")

        try:
            project = registry.add(name, path, lang)
            click.echo(f"Added project: {name}")
            click.echo(f"  Path: {project.path}")
            click.echo(f"  Language: {lang}")
            click.echo(f"\nNext: eri-rpg index {name}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.argument("name")
    def remove(name: str):
        """Remove a project from registry."""
        registry = Registry.get_instance()

        if registry.remove(name):
            click.echo(f"Removed project: {name}")
        else:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

    @cli.command("list")
    def list_projects():
        """List registered projects."""
        registry = Registry.get_instance()
        projects = registry.list()

        if not projects:
            click.echo("No projects registered.")
            click.echo("Add one with: eri-rpg add <name> <path>")
            return

        for p in projects:
            # Get mode
            mode_str = get_mode(p.path)
            mode_badge = "[BOOTSTRAP]" if mode_str == "bootstrap" else "[MAINTAIN]"

            status = "indexed" if p.is_indexed() else "not indexed"
            age = ""
            if p.index_age_days() is not None:
                days = p.index_age_days()
                if days < 1:
                    age = " (today)"
                else:
                    age = f" ({int(days)} days ago)"

            click.echo(f"{p.name} {mode_badge}: {p.path} ({p.lang}, {status}{age})")

    @cli.command()
    @click.argument("name")
    @click.option("-v", "--verbose", is_flag=True, help="Show progress")
    def index(name: str, verbose: bool):
        """Index a project's codebase.

        Parses all files, extracts interfaces, builds dependency graph.
        """
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            click.echo("Add it with: eri-rpg add <name> <path>")
            sys.exit(1)

        click.echo(f"Indexing {name}...")
        try:
            graph = index_project(project, verbose=verbose)
            registry.update_indexed(name)

            stats = graph.stats()
            click.echo(f"\nIndexed:")
            click.echo(f"  Modules: {stats['modules']}")
            click.echo(f"  Dependencies: {stats['edges']}")
            click.echo(f"  Lines: {stats['total_lines']:,}")
            click.echo(f"  Interfaces: {stats['total_interfaces']}")
            click.echo(f"\nSaved to: {project.graph_path}")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
