"""
UI Commands - Web dashboard.

Commands:
- serve: Start the EriRPG web dashboard
"""

import sys
import click


def register(cli):
    """Register UI commands with CLI."""

    @cli.command()
    @click.option('--port', default=8080, help='Port to serve on')
    @click.option('--host', default='127.0.0.1', help='Host to bind to')
    @click.option('--open', 'open_browser', is_flag=True, help='Open browser automatically')
    def serve(port: int, host: str, open_browser: bool):
        """Start the EriRPG web dashboard (v0.0.1-alpha).

        Local dashboard for watching EriRPG state while Claude Code works.
        View projects, runs, learnings, decisions, and more in real-time.

        Examples:
            eri-rpg serve
            eri-rpg serve --port 3000
            eri-rpg serve --open
        """
        try:
            from erirpg.ui.server import create_app
            import uvicorn
        except ImportError as e:
            click.echo("UI dependencies not installed.", err=True)
            click.echo("Run: pip install erirpg[ui]", err=True)
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        app = create_app()
        url = f"http://{host}:{port}"

        click.echo("EriRPG Dashboard v0.0.1-alpha")
        click.echo(f"URL: {url}")
        click.echo("Press Ctrl+C to stop")
        click.echo("")

        if open_browser:
            import webbrowser
            webbrowser.open(url)

        uvicorn.run(app, host=host, port=port, log_level="warning")
