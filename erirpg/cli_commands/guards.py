"""
CLI Command Guards - Tier-based command gating.

Provides decorators to gate commands by feature tier level.
Commands outside the current tier show an upgrade message.
"""

import functools
import sys
from typing import Callable, Optional

import click

from erirpg.config import (
    Tier, TIER_CONFIG, TIER_LEVELS,
    load_config, tier_allows, get_tier_for_command
)
from erirpg.registry import Registry


def get_project_path_from_context(ctx: click.Context, project_arg: Optional[str] = None) -> Optional[str]:
    """Extract project path from Click context or argument.

    Tries multiple strategies:
    1. If project_arg provided, look up in registry
    2. Check for 'project' or 'name' in params
    3. Fall back to current directory

    Args:
        ctx: Click context
        project_arg: Optional explicit project name

    Returns:
        Project path or None if not found
    """
    import os

    # Strategy 1: Explicit project argument
    if project_arg:
        registry = Registry.get_instance()
        project = registry.get(project_arg)
        if project:
            return project.path

    # Strategy 2: Check context params
    if ctx and ctx.params:
        for key in ("project", "name"):
            if key in ctx.params and ctx.params[key]:
                registry = Registry.get_instance()
                project = registry.get(ctx.params[key])
                if project:
                    return project.path

    # Strategy 3: Current directory
    cwd = os.getcwd()
    eri_rpg_dir = os.path.join(cwd, ".eri-rpg")
    if os.path.exists(eri_rpg_dir):
        return cwd

    return None


def tier_required(min_tier: Tier):
    """Decorator to gate commands by minimum tier level.

    If the project's tier is below the required tier, shows an
    upgrade message instead of running the command.

    Args:
        min_tier: Minimum tier required ("lite", "standard", or "full")

    Returns:
        Decorator function

    Example:
        @cli.command()
        @tier_required("standard")
        def discuss(...):
            ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Get click context
            ctx = click.get_current_context(silent=True)

            # Try to find project path
            project_arg = kwargs.get("project") or kwargs.get("name")
            project_path = get_project_path_from_context(ctx, project_arg)

            if project_path:
                config = load_config(project_path)
                current_tier = config.tier

                if not tier_allows(current_tier, min_tier):
                    # Get command name for message
                    cmd_name = f.__name__.replace("_", "-")

                    click.echo(f"Command '{cmd_name}' requires {min_tier} tier.", err=True)
                    click.echo(f"Current tier: {current_tier}", err=True)
                    click.echo("", err=True)

                    # Show tier descriptions
                    click.echo(f"Tier features:", err=True)
                    click.echo(f"  lite:     {TIER_CONFIG['lite']['description']}", err=True)
                    click.echo(f"  standard: {TIER_CONFIG['standard']['description']}", err=True)
                    click.echo(f"  full:     {TIER_CONFIG['full']['description']}", err=True)
                    click.echo("", err=True)

                    # Show upgrade command
                    if project_arg:
                        click.echo(f"Upgrade with: eri-rpg mode {project_arg} --{min_tier}", err=True)
                    else:
                        click.echo(f"Upgrade with: eri-rpg mode <project> --{min_tier}", err=True)

                    sys.exit(1)

            # Tier check passed (or no project context), run command
            return f(*args, **kwargs)

        return wrapper
    return decorator


def tier_hidden(min_tier: Tier):
    """Decorator to hide commands from --help if tier is below minimum.

    Unlike tier_required, this completely hides the command from
    help output for projects below the tier. The command still
    works if called directly (and tier_required handles the gate).

    Args:
        min_tier: Minimum tier to show in help

    Returns:
        Decorator function

    Note:
        This is more complex to implement with Click and may not
        be necessary for MVP. tier_required provides good UX.
    """
    def decorator(f: Callable) -> Callable:
        # For now, just pass through - tier_required handles gating
        # Future: Could use Click's hidden=True with dynamic check
        return f
    return decorator


# Convenience decorators for common tiers
def standard_tier(f: Callable) -> Callable:
    """Shorthand for @tier_required("standard")."""
    return tier_required("standard")(f)


def full_tier(f: Callable) -> Callable:
    """Shorthand for @tier_required("full")."""
    return tier_required("full")(f)
