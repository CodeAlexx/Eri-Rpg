"""
Setup Commands - Project registration and indexing.

Commands:
- add: Register a project
- remove: Remove a project
- list: List registered projects
- index: Index a project's codebase
"""

import json
import os
import shutil
import sys

import click

from erirpg.registry import Registry, detect_project_language
from erirpg.config import get_mode, get_tier
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

    def _get_remove_project_info(name: str) -> dict:
        """Gather info about what would be removed for a project."""
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            return {"error": f"Project '{name}' not found", "found": False}

        from erirpg.state import State
        from erirpg.storage import count_sessions_for_project, load_graph

        state = State.load()
        project_path = project.path

        # Check .eri-rpg/ dir
        eri_dir = os.path.join(project_path, ".eri-rpg")
        eri_exists = os.path.isdir(eri_dir)
        eri_file_count = 0
        if eri_exists:
            for _root, _dirs, files in os.walk(eri_dir):
                eri_file_count += len(files)

        # Check .planning/ dir
        planning_dir = os.path.join(project_path, ".planning")
        planning_exists = os.path.isdir(planning_dir)
        phase_count = 0
        if planning_exists:
            phases_dir = os.path.join(planning_dir, "phases")
            if os.path.isdir(phases_dir):
                phase_count = len([
                    d for d in os.listdir(phases_dir)
                    if os.path.isdir(os.path.join(phases_dir, d))
                ])

        # Check database
        session_count = count_sessions_for_project(name)
        has_graph = load_graph(name) is not None

        # Check active project
        is_active = state.get_active_project() == name

        return {
            "found": True,
            "name": name,
            "path": project_path,
            "lang": project.lang,
            "indexed_at": project.indexed_at.isoformat() if project.indexed_at else None,
            "is_active": is_active,
            "eri_dir": {"exists": eri_exists, "file_count": eri_file_count},
            "planning_dir": {"exists": planning_exists, "phase_count": phase_count},
            "database": {"session_count": session_count, "has_graph": has_graph},
        }

    def _remove_project(name: str, clean_eri: bool, clean_planning: bool, clean_db: bool) -> dict:
        """Execute project removal with specified cleanup options."""
        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            return {"error": f"Project '{name}' not found", "removed": False}

        project_path = project.path
        result = {"removed": True, "name": name, "cleaned": []}

        # Remove from registry
        registry.remove(name)
        result["cleaned"].append("registry")

        # Clear active project if it matches
        from erirpg.state import State
        state = State.load()
        if state.get_active_project() == name:
            state.clear_active_project()
            result["cleaned"].append("active_project")
            result["was_active"] = True

        # Clean database
        if clean_db:
            from erirpg.storage import delete_project, delete_sessions_for_project
            graph_deleted = delete_project(name)
            session_count = delete_sessions_for_project(name)
            result["cleaned"].append("database")
            result["graph_deleted"] = graph_deleted
            result["sessions_deleted"] = session_count

        # Clean .eri-rpg/ dir
        if clean_eri:
            eri_dir = os.path.join(project_path, ".eri-rpg")
            if os.path.isdir(eri_dir):
                shutil.rmtree(eri_dir, ignore_errors=True)
                result["cleaned"].append("eri_dir")

        # Clean .planning/ dir
        if clean_planning:
            planning_dir = os.path.join(project_path, ".planning")
            if os.path.isdir(planning_dir):
                shutil.rmtree(planning_dir, ignore_errors=True)
                result["cleaned"].append("planning_dir")

        return result

    @cli.command()
    @click.argument("name")
    @click.option("--clean", is_flag=True, help="Also remove .eri-rpg/ dir and database data")
    @click.option("--clean-planning", is_flag=True, help="Also remove .planning/ dir")
    @click.option("--clean-all", is_flag=True, help="Remove everything (registry + .eri-rpg/ + .planning/ + database)")
    @click.option("--force", is_flag=True, help="Skip confirmation prompt")
    @click.option("--json", "as_json", is_flag=True, help="Output JSON (implies --force)")
    @click.option("--info-only", is_flag=True, help="Show what would be removed without doing it")
    def remove(name: str, clean: bool, clean_planning: bool, clean_all: bool,
               force: bool, as_json: bool, info_only: bool):
        """Remove a project from registry.

        By default only removes the registry entry. Use --clean flags to
        also remove local data, planning artifacts, and database records.
        """
        if info_only:
            info = _get_remove_project_info(name)
            if as_json:
                click.echo(json.dumps(info, indent=2))
            else:
                if not info["found"]:
                    click.echo(f"Error: {info['error']}", err=True)
                    sys.exit(1)
                click.echo(f"Project: {info['name']}")
                click.echo(f"  Path: {info['path']}")
                click.echo(f"  Language: {info['lang']}")
                click.echo(f"  Active: {info['is_active']}")
                if info["eri_dir"]["exists"]:
                    click.echo(f"  .eri-rpg/: {info['eri_dir']['file_count']} files")
                if info["planning_dir"]["exists"]:
                    click.echo(f"  .planning/: {info['planning_dir']['phase_count']} phases")
                if info["database"]["has_graph"]:
                    click.echo(f"  Graph: yes")
                if info["database"]["session_count"]:
                    click.echo(f"  Sessions: {info['database']['session_count']}")
            return

        if not _get_remove_project_info(name)["found"]:
            if as_json:
                click.echo(json.dumps({"error": f"Project '{name}' not found", "removed": False}))
            else:
                click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        # Resolve flags
        if clean_all:
            clean = True
            clean_planning = True
        clean_db = clean  # --clean includes database

        # Confirm destructive ops
        if not as_json and not force and (clean or clean_planning):
            parts = ["registry entry"]
            if clean:
                parts.append(".eri-rpg/ directory")
                parts.append("database records")
            if clean_planning:
                parts.append(".planning/ directory")
            click.echo(f"Will remove: {', '.join(parts)}")
            if not click.confirm("Proceed?"):
                click.echo("Aborted.")
                return

        result = _remove_project(name, clean_eri=clean, clean_planning=clean_planning, clean_db=clean_db)

        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if result["removed"]:
                click.echo(f"Removed project: {name}")
                if "database" in result.get("cleaned", []):
                    click.echo(f"  Cleaned database ({result.get('sessions_deleted', 0)} sessions)")
                if "eri_dir" in result.get("cleaned", []):
                    click.echo(f"  Removed .eri-rpg/ directory")
                if "planning_dir" in result.get("cleaned", []):
                    click.echo(f"  Removed .planning/ directory")
                if result.get("was_active"):
                    click.echo(f"  Cleared active project")
            else:
                click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
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
            # Get mode and tier
            mode_str = get_mode(p.path)
            tier_str = get_tier(p.path)
            mode_badge = "[BOOTSTRAP]" if mode_str == "bootstrap" else "[MAINTAIN]"
            tier_badge = f"[{tier_str.upper()}]"

            status = "indexed" if p.is_indexed() else "not indexed"
            age = ""
            if p.index_age_days() is not None:
                days = p.index_age_days()
                if days < 1:
                    age = " (today)"
                else:
                    age = f" ({int(days)} days ago)"

            click.echo(f"{p.name} {tier_badge} {mode_badge}: {p.path} ({p.lang}, {status}{age})")

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
