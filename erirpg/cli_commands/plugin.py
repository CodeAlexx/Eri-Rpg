"""Plugin build and validation commands."""
import json
import os
import re
import click
from pathlib import Path


def get_erirpg_root() -> Path:
    """Get the root directory of the erirpg package."""
    # Walk up from this file to find pyproject.toml
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback to current working directory
    return Path.cwd()


@click.group(name="plugin")
def plugin_group():
    """Plugin build and validation commands."""
    pass


@plugin_group.command(name="build")
@click.option("--check", is_flag=True, help="Validate without building")
def build_cmd(check: bool):
    """Build and validate plugin structure."""
    root = get_erirpg_root()
    plugin_dir = root / ".claude-plugin"

    if not plugin_dir.exists():
        click.echo("Plugin directory not found: .claude-plugin/")
        click.echo("Create with the plugin structure first.")
        raise SystemExit(1)

    # Check required files
    required = [
        "plugin.json",
        "README.md",
        "hooks/pretooluse",
        "hooks/precompact",
        "hooks/sessionstart",
        "hooks/posttooluse",
    ]

    missing = []
    for path in required:
        if not (plugin_dir / path).exists():
            missing.append(path)

    if missing:
        click.echo("Missing required files:")
        for m in missing:
            click.echo(f"  - {m}")
        raise SystemExit(1)

    # Validate plugin.json
    try:
        manifest = json.loads((plugin_dir / "plugin.json").read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Invalid plugin.json: {e}")
        raise SystemExit(1)

    # Check version sync with pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'version = "([^"]+)"', content)
        if match:
            py_version = match.group(1)
            if manifest.get("version") != py_version:
                click.echo(f"Version mismatch:")
                click.echo(f"  plugin.json:   {manifest.get('version')}")
                click.echo(f"  pyproject.toml: {py_version}")
                raise SystemExit(1)

    # Validate hooks are executable
    for hook in ["pretooluse", "precompact", "sessionstart", "posttooluse"]:
        hook_path = plugin_dir / "hooks" / hook
        if hook_path.exists():
            mode = hook_path.stat().st_mode
            if not (mode & 0o111):  # Check any execute bit
                click.echo(f"Hook not executable: hooks/{hook}")
                click.echo(f"  Fix with: chmod +x {hook_path}")
                raise SystemExit(1)

    # Count resources
    skills = list((plugin_dir / "skills").glob("*/SKILL.md")) if (plugin_dir / "skills").exists() else []
    agents = [a for a in (plugin_dir / "agents").glob("*.md") if a.name != "README.md"] if (plugin_dir / "agents").exists() else []

    if check:
        click.echo("Plugin structure valid")
        click.echo(f"  Skills: {len(skills)}")
        click.echo(f"  Agents: {len(agents)}")
        click.echo(f"  Hooks: 4")
        return

    click.echo("Plugin validated successfully")
    click.echo(f"\nPlugin location: {plugin_dir}")
    click.echo(f"Skills: {len(skills)}, Agents: {len(agents)}, Hooks: 4")
    click.echo(f"\nTest with: claude --plugin-dir {plugin_dir}")


@plugin_group.command(name="info")
def info_cmd():
    """Show plugin information."""
    root = get_erirpg_root()
    plugin_dir = root / ".claude-plugin"
    manifest_file = plugin_dir / "plugin.json"

    if not manifest_file.exists():
        click.echo("Plugin not found at .claude-plugin/")
        click.echo("Build with: eri-rpg plugin build")
        raise SystemExit(1)

    manifest = json.loads(manifest_file.read_text())
    click.echo(f"Name: {manifest.get('name', 'unknown')}")
    click.echo(f"Version: {manifest.get('version', 'unknown')}")
    click.echo(f"Description: {manifest.get('description', 'N/A')}")
    click.echo(f"Location: {plugin_dir}")

    # Count resources
    skills = list((plugin_dir / "skills").glob("*/SKILL.md")) if (plugin_dir / "skills").exists() else []
    agents = [a for a in (plugin_dir / "agents").glob("*.md") if a.name != "README.md"] if (plugin_dir / "agents").exists() else []

    click.echo(f"\nResources:")
    click.echo(f"  Skills: {len(skills)}")
    for s in sorted(skills):
        click.echo(f"    - {s.parent.name}")
    click.echo(f"  Agents: {len(agents)}")
    for a in sorted(agents):
        click.echo(f"    - {a.stem}")
    click.echo(f"  Hooks: 4")


def register(cli: click.Group) -> None:
    """Register plugin commands with the CLI."""
    cli.add_command(plugin_group)
