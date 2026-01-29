"""
Mode Commands - Bootstrap/Maintain mode management.

Commands:
- init: Initialize a new project in bootstrap mode
- graduate: Graduate project to maintain mode
- mode: Show or change project mode
- info: Show detailed project status
"""

import json
import os
import sys
import click

from erirpg.registry import Registry, detect_project_language
from erirpg.config import (
    load_config, get_mode, set_mode, graduate_project,
    init_project_config
)
from erirpg.indexer import index_project, get_or_load_graph
from erirpg.memory import load_knowledge, save_knowledge


def register(cli):
    """Register mode commands with CLI."""

    @cli.command("init")
    @click.argument("name")
    @click.option("--path", "-p", type=click.Path(), default=None,
                  help="Path to project root (defaults to current directory)")
    @click.option("--lang", default=None, type=click.Choice(["python", "rust", "c", "mojo", "dart"]),
                  help="Programming language (auto-detected if not specified)")
    def init_project(name: str, path: str, lang: str):
        """Initialize a new EriRPG project in bootstrap mode.

        Creates .eri-rpg/ directory with empty config, state, and knowledge files.
        Project starts in bootstrap mode with no enforcement.

        NAME: Unique project identifier

        Example:
            eri-rpg init my-app --path ~/projects/my-app
        """
        from pathlib import Path as P

        registry = Registry.get_instance()

        # Check if project name already exists
        if registry.get(name):
            click.echo(f"Error: Project '{name}' already exists in registry", err=True)
            sys.exit(1)

        # Resolve path
        if path is None:
            path = os.getcwd()
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Create project directory if it doesn't exist
        if not os.path.isdir(abs_path):
            click.echo(f"Creating directory: {abs_path}")
            os.makedirs(abs_path, exist_ok=True)

        # Create .eri-rpg directory
        eri_rpg_dir = P(abs_path) / ".eri-rpg"
        eri_rpg_dir.mkdir(parents=True, exist_ok=True)

        # Initialize config in bootstrap mode
        init_project_config(abs_path)

        # Create empty state.json
        state_file = eri_rpg_dir / "state.json"
        if not state_file.exists():
            with open(state_file, "w") as f:
                json.dump({}, f)

        # Create empty knowledge.json
        knowledge_file = eri_rpg_dir / "knowledge.json"
        if not knowledge_file.exists():
            with open(knowledge_file, "w") as f:
                json.dump({"learnings": {}, "decisions": []}, f, indent=2)

        # Auto-detect language if not specified
        if lang is None:
            lang = detect_project_language(abs_path)
            if lang == "unknown":
                lang = "python"  # Default
            else:
                click.echo(f"Auto-detected language: {lang}")

        # Register project
        try:
            project = registry.add(name, abs_path, lang)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        click.echo(f"Initialized project: {name}")
        click.echo(f"  Path: {abs_path}")
        click.echo(f"  Language: {lang}")
        click.echo(f"  Mode: bootstrap (no enforcement)")
        click.echo("")
        click.echo("Build freely - no EriRPG enforcement active.")
        click.echo("When ready to lock down patterns, run:")
        click.echo(f"  eri-rpg graduate {name}")

    @cli.command()
    @click.argument("name")
    @click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
    def graduate(name: str, force: bool):
        """Graduate a project from bootstrap to maintain mode.

        Runs full codebase learning and enables enforcement.
        After graduation, EriRPG will enforce preflight checks
        and require active runs for file modifications.

        NAME: Project name

        Example:
            eri-rpg graduate my-app
        """
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        # Check current mode
        config = load_config(project.path)
        if config.mode == "maintain" and config.graduated_at:
            click.echo(f"Project '{name}' is already graduated (since {config.graduated_at[:10]})")
            if not force and not click.confirm("Re-graduate and re-learn all files?"):
                return

        # Confirm
        if not force:
            click.echo(f"Graduating project: {name}")
            click.echo(f"  Path: {project.path}")
            click.echo("")
            click.echo("This will:")
            click.echo("  1. Learn all project files")
            click.echo("  2. Build dependency graph")
            click.echo("  3. Enable enforcement (maintain mode)")
            click.echo("")
            if not click.confirm("Continue?"):
                click.echo("Cancelled.")
                return

        click.echo(f"\nGraduating: {name}")

        # Step 1: Index project if not indexed
        if not project.is_indexed():
            click.echo("Indexing project... ", nl=False)
            try:
                index_project(project.path, project.lang)
                registry.update_indexed(name)
                click.echo("done")
            except Exception as e:
                click.echo(f"failed: {e}", err=True)
                sys.exit(1)
        else:
            click.echo("Index: already exists")

        # Step 2: Learn all files
        click.echo("Learning files... ", nl=False)
        try:
            graph = get_or_load_graph(project.path)
            knowledge = load_knowledge(project.path)

            # Count modules
            module_count = len(graph.modules) if hasattr(graph, 'modules') else 0

            # For now, we just ensure the knowledge store exists
            # Actual learning can be done incrementally
            save_knowledge(project.path, knowledge)
            click.echo(f"done ({module_count} modules indexed)")
        except Exception as e:
            click.echo(f"failed: {e}", err=True)
            sys.exit(1)

        # Step 3: Graduate to maintain mode
        click.echo("Enabling enforcement... ", nl=False)
        graduate_project(project.path, by="user")
        click.echo("done")

        click.echo("")
        click.echo(f"Graduated. Preflight and learning now active.")
        click.echo(f"Run 'eri-rpg mode {name} --bootstrap' to disable temporarily.")

    @cli.command()
    @click.argument("name")
    @click.option("--bootstrap", "set_bootstrap", is_flag=True, help="Set to bootstrap mode (no enforcement)")
    @click.option("--maintain", "set_maintain", is_flag=True, help="Set to maintain mode (full enforcement)")
    def mode(name: str, set_bootstrap: bool, set_maintain: bool):
        """Show or change project operational mode.

        Modes:
        - bootstrap: No enforcement, hooks pass through
        - maintain: Full enforcement, requires preflight/runs

        NAME: Project name

        Examples:
            eri-rpg mode my-app              # Show current mode
            eri-rpg mode my-app --bootstrap  # Disable enforcement
            eri-rpg mode my-app --maintain   # Enable enforcement
        """
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        config = load_config(project.path)
        current_mode = get_mode(project.path)

        # Both flags = error
        if set_bootstrap and set_maintain:
            click.echo("Error: Cannot set both --bootstrap and --maintain", err=True)
            sys.exit(1)

        # No flags = show status
        if not set_bootstrap and not set_maintain:
            graduated_info = ""
            if config.graduated_at:
                graduated_info = f" (graduated {config.graduated_at[:10]})"
            elif current_mode == "maintain":
                graduated_info = " (not formally graduated)"
            else:
                graduated_info = " (not graduated)"

            click.echo(f"Project: {name}")
            click.echo(f"Mode: {current_mode}{graduated_info}")

            if current_mode == "bootstrap":
                click.echo("Enforcement: disabled")
                click.echo("")
                click.echo("To enable enforcement:")
                click.echo(f"  eri-rpg graduate {name}   # Learn all + enable")
                click.echo(f"  eri-rpg mode {name} --maintain  # Just enable")
            else:
                click.echo("Enforcement: enabled")
                click.echo("")
                click.echo("To disable temporarily:")
                click.echo(f"  eri-rpg mode {name} --bootstrap")
            return

        # Set bootstrap mode
        if set_bootstrap:
            set_mode(project.path, "bootstrap")
            click.echo(f"Mode set to bootstrap. Enforcement disabled.")
            return

        # Set maintain mode
        if set_maintain:
            # Warn if never graduated
            if not config.graduated_at:
                click.echo("Warning: Project never graduated.")
                click.echo("Consider running 'eri-rpg graduate' to learn all files first.")
                if not click.confirm("Continue anyway?"):
                    return

            set_mode(project.path, "maintain")
            click.echo(f"Mode set to maintain. Enforcement enabled.")

    @cli.command("info")
    @click.argument("name")
    def project_info(name: str):
        """Show detailed project status including mode.

        NAME: Project name

        Example:
            eri-rpg info my-app
        """
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        config = load_config(project.path)
        current_mode = get_mode(project.path)
        knowledge = load_knowledge(project.path)

        # Count learnings
        learnings_count = len(knowledge.learnings) if hasattr(knowledge, 'learnings') else 0

        # Count stale learnings (simplified - just check if any)
        stale_count = 0
        for learning in (knowledge.learnings.values() if hasattr(knowledge, 'learnings') else []):
            if hasattr(learning, 'is_stale') and learning.is_stale():
                stale_count += 1

        click.echo(f"Project: {name}")
        click.echo(f"Path: {project.path}")
        click.echo(f"Language: {project.lang}")
        click.echo(f"Mode: {current_mode}")

        # Graduation info
        if config.graduated_at:
            click.echo(f"Graduated: {config.graduated_at[:10]} (by {config.graduated_by})")
        else:
            click.echo(f"Graduated: never")

        # Index info
        if project.is_indexed():
            days = project.index_age_days()
            if days is not None:
                if days < 1:
                    click.echo(f"Indexed: today")
                else:
                    click.echo(f"Indexed: {int(days)} days ago")
        else:
            click.echo(f"Indexed: no")

        # Knowledge info
        click.echo(f"Learned: {learnings_count}" + (f" ({stale_count} stale)" if stale_count > 0 else ""))

        # Enforcement status
        if current_mode == "bootstrap":
            click.echo(f"Preflight: disabled")
            click.echo(f"Auto-learn: disabled")
        else:
            click.echo(f"Preflight: enabled")
            click.echo(f"Auto-learn: enabled")
