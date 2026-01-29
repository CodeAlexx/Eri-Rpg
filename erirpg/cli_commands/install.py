"""
Install Commands - Claude Code integration.

Commands:
- install: Install EriRPG commands and hooks for Claude Code
- uninstall: Remove EriRPG from Claude Code
- install-status: Check installation status
"""

import click


def register(cli):
    """Register install commands with CLI."""

    @cli.command()
    def install():
        """Install EriRPG commands and hooks for Claude Code."""
        from erirpg.install import install_claude_code
        install_claude_code()

    @cli.command()
    def uninstall():
        """Remove EriRPG from Claude Code."""
        from erirpg.install import uninstall_claude_code
        uninstall_claude_code()

    @cli.command("install-status")
    def install_status():
        """Check EriRPG installation status."""
        from erirpg.install import check_installation
        status = check_installation()
        click.echo("EriRPG Installation Status:")
        if status["commands_installed"]:
            click.echo(f"  Commands: {', '.join(status['commands'])}")
        else:
            click.echo("  Commands: Not installed")
        if status["hooks_installed"]:
            click.echo(f"  Hooks: {', '.join(status['hooks'])}")
        else:
            click.echo("  Hooks: Not installed")

    @cli.command("install-commands")
    def install_commands_cmd():
        """Sync slash commands from repo to ~/.claude/commands/eri/.

        Use this after pulling updates to sync new/changed commands.
        Does not modify hooks or other settings.

        Example:
            eri-rpg install-commands
        """
        from erirpg.install import install_commands
        install_commands()
