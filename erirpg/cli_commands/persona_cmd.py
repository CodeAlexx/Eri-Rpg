"""
Persona Commands - Persona and context management (SuperClaude replacement).

Commands (full tier):
- persona: Show or set persona for context generation
- workflow: Show workflow stages and their default personas
- ctx: Generate dynamic CLAUDE.md context
- commands: Show EriRPG slash commands
"""

import os
import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register persona commands with CLI."""
    from erirpg.registry import Registry

    @cli.command(name="persona")
    @click.argument("name", required=False)
    @click.option("--list", "-l", "list_all", is_flag=True, help="List available personas")
    @tier_required("full")
    def persona_cmd(name: str = None, list_all: bool = False):
        """Show or set persona for context generation.

        Personas affect how EriRPG frames context and suggestions:
        - architect: Systems thinking, tradeoffs, structure
        - dev: Pragmatic, ship it, working code
        - critic: Find issues, security, edge cases
        - analyst: Root cause, debugging, investigation
        - mentor: Explain, teach, build understanding

        \b
        Examples:
            eri-rpg persona --list       # List all personas
            eri-rpg persona architect    # Show architect details
            eri-rpg persona              # Show current/default
        """
        from erirpg.persona import Persona, get_persona, get_persona_by_name, PERSONAS

        if list_all:
            click.echo("Available Personas:\n")
            for p, config in PERSONAS.items():
                click.echo(f"  {p.name.lower():12} - {config.identity}")
            click.echo("")
            click.echo("Use: eri-rpg context --persona <name>")
            return

        if name:
            persona = get_persona_by_name(name)
            if not persona:
                click.echo(f"Unknown persona: {name}", err=True)
                click.echo("Use --list to see available personas")
                sys.exit(1)
            config = get_persona(persona)
        else:
            # Default to DEV
            config = get_persona(Persona.DEV)

        click.echo(config.to_prompt())
        click.echo(f"**Triggers**: {', '.join(config.triggers)}")
        click.echo(f"**Thinking**: {config.thinking_style}")

    @cli.command(name="workflow")
    @click.argument("stage", required=False)
    @click.option("--list", "-l", "list_all", is_flag=True, help="List workflow stages")
    def workflow_cmd(stage: str = None, list_all: bool = False):
        """Show workflow stages and their default personas.

        Each workflow stage implies a default persona:
        - analyze -> architect (systems thinking)
        - discuss -> architect (planning)
        - implement -> dev (building)
        - review -> critic (finding issues)
        - debug -> analyst (investigation)

        \b
        Examples:
            eri-rpg workflow --list      # List all stages
            eri-rpg workflow implement   # Show implement stage details
        """
        from erirpg.workflow import (
            Stage, get_stage_by_name, get_stage_description,
            get_persona_for_stage, STAGE_PERSONA
        )
        from erirpg.persona import get_persona

        if list_all:
            click.echo("Workflow Stages:\n")
            for s in Stage:
                persona = get_persona_for_stage(s)
                desc = get_stage_description(s)
                click.echo(f"  {s.name.lower():12} -> {persona.name.lower():10} | {desc}")
            click.echo("")
            click.echo("Use: eri-rpg context --stage <name>")
            return

        if stage:
            s = get_stage_by_name(stage)
            if not s:
                click.echo(f"Unknown stage: {stage}", err=True)
                click.echo("Use --list to see available stages")
                sys.exit(1)
        else:
            s = Stage.IDLE

        persona = get_persona_for_stage(s)
        config = get_persona(persona)

        click.echo(f"## Stage: {s.name}")
        click.echo(f"**Description**: {get_stage_description(s)}")
        click.echo(f"**Default Persona**: {persona.name.lower()}")
        click.echo("")
        click.echo(config.to_prompt())

    @cli.command(name="ctx")
    @click.argument("project", required=False)
    @click.option("--stage", type=click.Choice(["idle", "analyze", "discuss", "implement", "review", "debug"]),
                  default="idle", help="Workflow stage")
    @click.option("--persona", type=click.Choice(["architect", "dev", "critic", "analyst", "mentor"]),
                  default=None, help="Override persona")
    @click.option("--task", default=None, help="Current task description")
    @click.option("--write", "-w", is_flag=True, help="Write to CLAUDE.md")
    @click.option("--compact", "-c", is_flag=True, help="Minimize token usage")
    def context_cmd(project: str = None, stage: str = "idle", persona: str = None,
                    task: str = None, write: bool = False, compact: bool = False):
        """Generate dynamic CLAUDE.md context.

        Builds project-aware context from knowledge.json:
        - Learned patterns from this codebase
        - Recent decisions
        - Current workflow stage and persona
        - Current task (if any)

        This replaces SuperClaude's static 20k token system prompt
        with ~2-3k tokens of project-specific knowledge.

        \b
        Examples:
            eri-rpg ctx                        # Context for current dir
            eri-rpg ctx myproject              # Context for named project
            eri-rpg ctx --stage implement      # Set stage (and persona)
            eri-rpg ctx --persona critic       # Override persona
            eri-rpg ctx --write                # Write to CLAUDE.md
            eri-rpg ctx --compact              # Minimal tokens
        """
        from erirpg.workflow import Stage, get_stage_by_name
        from erirpg.persona import Persona, get_persona_by_name
        from erirpg.claudemd import generate_claude_md_from_store, write_claude_md, generate_minimal_claude_md

        registry = Registry.get_instance()

        # Get project path
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
            project_name = project
        else:
            project_path = os.getcwd()
            project_name = os.path.basename(project_path)

        # Parse stage and persona
        stage_enum = get_stage_by_name(stage) or Stage.IDLE
        persona_enum = get_persona_by_name(persona) if persona else None

        # Check if knowledge exists
        knowledge_path = os.path.join(project_path, ".eri-rpg", "knowledge.json")
        if not os.path.exists(knowledge_path):
            click.echo("No knowledge.json found. Run 'eri-rpg sync --learn' first.", err=True)
            if write:
                content = generate_minimal_claude_md(project_name)
                path = write_claude_md(project_path, content)
                click.echo(f"Wrote minimal CLAUDE.md to {path}")
            return

        # Generate context
        content = generate_claude_md_from_store(
            project_path=project_path,
            project_name=project_name,
            stage=stage_enum,
            persona=persona_enum,
            current_task=task,
            compact=compact,
        )

        if write:
            path = write_claude_md(project_path, content)
            click.echo(f"Wrote {path}")
        else:
            click.echo(content)

    @cli.command(name="commands")
    def commands_cmd():
        """Show EriRPG slash commands.

        Lists all available slash commands for use in Claude Code:
        - Workflow stages (/analyze, /implement, etc.)
        - Persona overrides (/architect, /critic, etc.)
        - Project management (/status, /learn, etc.)
        """
        from erirpg.commands import get_help_text
        click.echo(get_help_text())
