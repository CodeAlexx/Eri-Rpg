"""
EriRPG CLI - One tool. Three modes. No bloat.

Modes:
- new: Create new project from scratch
- take: Transplant feature from Project A to Project B
- work: Modify existing project

Commands are organized in modules under erirpg/cli_commands/.
"""

import click

from erirpg.cli_commands import register_all


@click.group()
@click.version_option(version="0.60.0")
def cli():
    """EriRPG - Cross-project feature transplant tool.

    Register projects, index codebases, find capabilities,
    extract features, and generate context for Claude Code.
    """
    pass


register_all(cli)


def main():
    cli()


if __name__ == "__main__":
    main()
