"""
Task list command - View project tasks from TASKS.md.
"""

import os
import re
import click
from pathlib import Path


def find_project_root(start_path: str = None) -> tuple[str, str]:
    """Find EriRPG project root and name from path.

    Returns:
        Tuple of (project_path, project_name) or (None, None) if not found
    """
    path = Path(start_path or os.getcwd()).resolve()

    for parent in [path] + list(path.parents):
        eri_dir = parent / ".eri-rpg"
        if eri_dir.is_dir():
            return str(parent), parent.name
        if parent == Path.home() or parent == Path("/"):
            break

    # Try global state
    state_file = Path.home() / ".eri-rpg" / "state.json"
    if state_file.exists():
        import json
        try:
            state = json.loads(state_file.read_text())
            project_name = state.get("active_project")
            if project_name:
                registry_file = Path.home() / ".eri-rpg" / "registry.json"
                if registry_file.exists():
                    registry = json.loads(registry_file.read_text())
                    projects = registry.get("projects", {})
                    if project_name in projects:
                        return projects[project_name].get("path"), project_name
        except:
            pass

    return None, None


def parse_tasks(content: str) -> dict:
    """Parse TASKS.md content into structured data."""
    result = {
        "pending": [],
        "completed": [],
        "bugs": [],
    }

    current_section = None

    for line in content.split("\n"):
        line_lower = line.lower()

        # Detect sections
        if "## pending" in line_lower:
            current_section = "pending"
        elif "## completed" in line_lower:
            current_section = "completed"
        elif "## bugs" in line_lower or "## issues" in line_lower:
            current_section = "bugs"
        elif line.startswith("## "):
            current_section = None

        # Parse task items
        if line.strip().startswith("- [ ]"):
            task = line.strip()[5:].strip()
            if current_section == "bugs" or "**BUG:" in line:
                result["bugs"].append(task)
            else:
                result["pending"].append(task)
        elif line.strip().startswith("- [x]"):
            task = line.strip()[5:].strip()
            result["completed"].append(task)

    return result


@click.command("task-list")
@click.argument("filter", default="all", required=False)
@click.option("-p", "--project", help="Project name or path")
@click.option("--raw", is_flag=True, help="Show raw TASKS.md content")
def task_list(filter: str, project: str, raw: bool):
    """View project tasks from TASKS.md.

    FILTER can be: all, pending, completed, bugs, or a search term.

    Examples:
        eri-rpg task-list              # Show all tasks
        eri-rpg task-list pending      # Show only pending
        eri-rpg task-list completed    # Show only completed
        eri-rpg task-list bugs         # Show only bugs/issues
        eri-rpg task-list auth         # Search for "auth" in tasks
    """
    # Find project
    if project:
        if os.path.isdir(project):
            project_path = project
            project_name = Path(project).name
        else:
            # Assume it's a project name, look in registry
            registry_file = Path.home() / ".eri-rpg" / "registry.json"
            if registry_file.exists():
                import json
                registry = json.loads(registry_file.read_text())
                projects = registry.get("projects", {})
                if project in projects:
                    project_path = projects[project].get("path")
                    project_name = project
                else:
                    click.echo(f"Project not found: {project}", err=True)
                    return
            else:
                click.echo(f"Registry not found", err=True)
                return
    else:
        project_path, project_name = find_project_root()

    if not project_path:
        click.echo("No EriRPG project found. Run from project directory or specify -p.", err=True)
        return

    # Find TASKS.md
    tasks_file = Path(project_path) / ".eri-rpg" / "TASKS.md"
    if not tasks_file.exists():
        click.echo(f"No TASKS.md found at {tasks_file}", err=True)
        return

    content = tasks_file.read_text()

    # Raw mode - just output the file
    if raw:
        click.echo(content)
        return

    # Parse and filter
    tasks = parse_tasks(content)
    filter_lower = filter.lower()

    # Output header
    click.echo(f"\n# Tasks: {project_name}\n")

    if filter_lower == "all":
        # Show all sections
        if tasks["pending"]:
            click.echo(f"## Pending ({len(tasks['pending'])})")
            for task in tasks["pending"]:
                click.echo(f"- [ ] {task}")
            click.echo()

        if tasks["bugs"]:
            click.echo(f"## Bugs/Issues ({len(tasks['bugs'])})")
            for task in tasks["bugs"]:
                click.echo(f"- [ ] {task}")
            click.echo()

        if tasks["completed"]:
            click.echo(f"## Completed ({len(tasks['completed'])})")
            for task in tasks["completed"][-10:]:  # Last 10
                click.echo(f"- [x] {task}")
            if len(tasks["completed"]) > 10:
                click.echo(f"  ... and {len(tasks['completed']) - 10} more")
            click.echo()

    elif filter_lower == "pending":
        click.echo(f"## Pending ({len(tasks['pending'])})")
        for task in tasks["pending"]:
            click.echo(f"- [ ] {task}")

    elif filter_lower == "completed":
        click.echo(f"## Completed ({len(tasks['completed'])})")
        for task in tasks["completed"]:
            click.echo(f"- [x] {task}")

    elif filter_lower == "bugs":
        click.echo(f"## Bugs/Issues ({len(tasks['bugs'])})")
        for task in tasks["bugs"]:
            click.echo(f"- [ ] {task}")

    else:
        # Search mode
        all_tasks = (
            [(t, "pending") for t in tasks["pending"]] +
            [(t, "bugs") for t in tasks["bugs"]] +
            [(t, "completed") for t in tasks["completed"]]
        )

        matches = [(t, s) for t, s in all_tasks if filter_lower in t.lower()]

        if matches:
            click.echo(f"## Search: '{filter}' ({len(matches)} matches)")
            for task, status in matches:
                marker = "[x]" if status == "completed" else "[ ]"
                click.echo(f"- {marker} {task}")
        else:
            click.echo(f"No tasks matching '{filter}'")


def register(cli: click.Group) -> None:
    """Register commands with CLI group."""
    cli.add_command(task_list)
