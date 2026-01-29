"""
Configuration Commands - Project settings management.

Commands:
- config: Configure project settings (multi-agent, concurrency)
- env: Configure project environment (test, lint, build commands, etc.)
"""

import sys
import click


def register(cli):
    """Register configuration commands with CLI."""

    @cli.command("config")
    @click.argument("project")
    @click.option("--multi-agent", type=click.Choice(["on", "off"]), default=None,
                  help="Enable or disable multi-agent mode")
    @click.option("--concurrency", type=int, default=None,
                  help="Max concurrent sub-agents (1-15)")
    @click.option("--show", is_flag=True, help="Show current configuration")
    def config_cmd(project: str, multi_agent: str, concurrency: int, show: bool):
        """Configure project settings.

        Examples:
            eri-rpg config myproject --show
            eri-rpg config myproject --multi-agent on
            eri-rpg config myproject --concurrency 5
        """
        from erirpg.config import load_config, set_multi_agent, set_concurrency, format_env_summary
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        config = load_config(proj.path)

        if show or (multi_agent is None and concurrency is None):
            click.echo(f"Configuration for {project}:")
            click.echo(f"  Mode: {config.mode}")
            click.echo(f"  Tier: {config.tier}")
            click.echo(f"  Multi-agent: {'enabled' if config.multi_agent.enabled else 'disabled'}")
            click.echo(f"  Max concurrency: {config.multi_agent.max_concurrency}")
            click.echo("")
            click.echo("Environment:")
            env_summary = format_env_summary(config.env)
            for line in env_summary.split("\n"):
                click.echo(f"  {line}")
            return

        if multi_agent is not None:
            enabled = multi_agent == "on"
            config = set_multi_agent(proj.path, enabled)
            click.echo(f"Multi-agent mode: {'enabled' if enabled else 'disabled'}")

        if concurrency is not None:
            config = set_concurrency(proj.path, concurrency)
            click.echo(f"Max concurrency: {config.multi_agent.max_concurrency}")

    @cli.command("env")
    @click.argument("project")
    @click.option("--set", "set_cmd", nargs=2, multiple=True, metavar="NAME VALUE",
                  help="Set a command/path: --set test 'uv run pytest'")
    @click.option("--var", nargs=2, multiple=True, metavar="KEY VALUE",
                  help="Set environment variable: --var DEBUG 1")
    @click.option("--unset-var", multiple=True, metavar="KEY",
                  help="Remove environment variable")
    @click.option("--detect", is_flag=True, help="Auto-detect environment from project files")
    @click.option("--show", is_flag=True, help="Show current environment config")
    def env_cmd(project: str, set_cmd: tuple, var: tuple, unset_var: tuple, detect: bool, show: bool):
        """Configure project environment (commands, paths, variables).

        Store per-project settings so Claude doesn't have to guess.

        \b
        Fields you can set:
          runner    - Package manager (uv, pip, poetry, cargo, npm)
          test      - Test command (e.g., "uv run pytest")
          lint      - Lint command (e.g., "uv run ruff check")
          format    - Format command (e.g., "uv run ruff format")
          build     - Build command (e.g., "uv build")
          run       - Run command (e.g., "uv run python main.py")
          typecheck - Type check command (e.g., "uv run mypy")
          python    - Python path (e.g., ".venv/bin/python")
          venv      - Virtual env path (e.g., ".venv")
          src_dir   - Source directory (e.g., "src")
          test_dir  - Test directory (e.g., "tests")

        \b
        Examples:
            eri-rpg env myproject --show
            eri-rpg env myproject --detect
            eri-rpg env myproject --set runner uv
            eri-rpg env myproject --set test "uv run pytest"
            eri-rpg env myproject --var PYTHONPATH ./src
        """
        from erirpg.config import (
            load_config, set_env_command, set_env_var, unset_env_var,
            auto_detect_and_save, format_env_summary
        )
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Auto-detect if requested
        if detect:
            config = auto_detect_and_save(proj.path)
            click.echo(f"Auto-detected environment for {project}:")
            click.echo(format_env_summary(config.env))
            return

        # Set commands
        for name, value in set_cmd:
            try:
                set_env_command(proj.path, name, value)
                click.echo(f"Set {name}: {value}")
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)

        # Set environment variables
        for key, value in var:
            set_env_var(proj.path, key, value)
            click.echo(f"Set env var {key}={value}")

        # Unset environment variables
        for key in unset_var:
            unset_env_var(proj.path, key)
            click.echo(f"Removed env var {key}")

        # Show if requested or no other action
        if show or (not set_cmd and not var and not unset_var):
            config = load_config(proj.path)
            click.echo(f"Environment for {project}:")
            click.echo(format_env_summary(config.env))
