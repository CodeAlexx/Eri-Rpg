"""
Configuration Commands - Project settings management.

Commands:
- config: Configure project settings (multi-agent, concurrency)
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
        from erirpg.config import load_config, set_multi_agent, set_concurrency
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        config = load_config(proj.path)

        if show or (multi_agent is None and concurrency is None):
            click.echo(f"Configuration for {project}:")
            click.echo(f"  Multi-agent mode: {'enabled' if config.multi_agent.enabled else 'disabled'}")
            click.echo(f"  Max concurrency: {config.multi_agent.max_concurrency}")
            click.echo(f"  Parallel steps: {'enabled' if config.multi_agent.parallel_steps else 'disabled'}")
            return

        if multi_agent is not None:
            enabled = multi_agent == "on"
            config = set_multi_agent(proj.path, enabled)
            click.echo(f"Multi-agent mode: {'enabled' if enabled else 'disabled'}")

        if concurrency is not None:
            config = set_concurrency(proj.path, concurrency)
            click.echo(f"Max concurrency: {config.multi_agent.max_concurrency}")
