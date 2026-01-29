"""
Analyze Commands - Pattern analysis and implementation.

Commands (full tier):
- analyze: Analyze project for patterns, conventions, and extension points
- implement: Implement a new feature using project patterns
- transplant: Transplant a feature from one project to another
- describe-feature: Extract feature description from a source file
"""

import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register analyze commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command()
    @click.argument("project")
    @click.option("--force", "-f", is_flag=True, help="Re-analyze even if patterns exist")
    @tier_required("full")
    def analyze(project: str, force: bool):
        """Analyze project for patterns, conventions, and extension points.

        Creates .eri-rpg/patterns.json with detected patterns that can be used
        by the implement and transplant commands.

        Example:
            eri-rpg analyze myproject
            eri-rpg analyze myproject --force
        """
        from erirpg.analyze import (
            analyze_project, load_patterns, save_patterns, format_patterns, get_patterns_path
        )

        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        patterns_path = get_patterns_path(proj.path)
        if patterns_path.exists() and not force:
            click.echo(f"Patterns already exist at {patterns_path}")
            click.echo("Use --force to re-analyze")
            patterns = load_patterns(proj.path)
            click.echo("")
            click.echo(format_patterns(patterns))
            return

        click.echo(f"Analyzing project {project}...")
        patterns = analyze_project(proj.path)
        save_patterns(proj.path, patterns)

        click.echo(f"Patterns saved to {patterns_path}")
        click.echo("")
        click.echo(format_patterns(patterns))

    @cli.command()
    @click.argument("project")
    @click.argument("feature")
    @click.option("--plan-only", is_flag=True, help="Only show plan, don't execute")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
    def implement(project: str, feature: str, plan_only: bool, yes: bool):
        """Implement a new feature using project patterns.

        Uses patterns detected by 'eri-rpg analyze' to plan implementation.
        Maps feature components to appropriate locations based on project
        conventions.

        Example:
            eri-rpg implement onetrainer "Klein LoRA - dynamic rank scheduler"
            eri-rpg implement myproject "Add caching layer" --plan-only
        """
        from erirpg.analyze import load_patterns, get_patterns_path, analyze_project, save_patterns
        from erirpg.implement import (
            plan_implementation, format_implementation_plan, plan_to_spec
        )

        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check patterns exist
        patterns_path = get_patterns_path(proj.path)
        if not patterns_path.exists():
            click.echo("No patterns found. Run 'eri-rpg analyze' first.")
            if click.confirm("Analyze now?"):
                patterns = analyze_project(proj.path)
                save_patterns(proj.path, patterns)
            else:
                sys.exit(1)

        # Generate plan
        plan = plan_implementation(proj.path, feature)

        # Show plan
        click.echo(format_implementation_plan(plan))

        if plan_only:
            return

        if not yes and not click.confirm("Proceed with implementation?"):
            return

        # Convert to spec
        spec = plan_to_spec(plan, proj.path)

        # Save spec
        from erirpg.specs import save_spec
        spec_path = save_spec(proj.path, spec)
        click.echo(f"Spec created: {spec_path}")

        # Offer to start work
        if click.confirm("Start EriRPG run?"):
            from erirpg.agent import Agent
            agent = Agent.from_spec(spec_path, project_path=proj.path)
            click.echo(f"Run started: {agent.run.id}")
            click.echo("Use Agent API or 'eri-rpg status' to continue.")

    @cli.command("transplant-feature")
    @click.option("--from", "source", required=True, help="Source: project:path or skill.md")
    @click.option("--to", "target", required=True, help="Target project")
    @click.option("--edit", is_flag=True, help="Edit description before implementing")
    def transplant_feature(source: str, target: str, edit: bool):
        """Transplant a feature from one project to another.

        Extracts a feature description from the source, then uses the target's
        patterns to plan implementation.

        Note: Named transplant-feature to avoid conflict with transplant module.

        Examples:
            eri-rpg transplant-feature --from simpletuner:training/klein.py --to onetrainer
            eri-rpg transplant-feature --from feature.md --to myproject
        """
        from erirpg.analyze import load_patterns, get_patterns_path
        from erirpg.implement import (
            describe_feature, plan_implementation, format_implementation_plan, plan_to_spec
        )
        from pathlib import Path

        # Get target project
        target_proj = registry.get(target)
        if not target_proj:
            click.echo(f"Error: Target project '{target}' not found", err=True)
            sys.exit(1)

        # Check target has patterns
        patterns_path = get_patterns_path(target_proj.path)
        if not patterns_path.exists():
            click.echo(f"No patterns found for {target}. Run 'eri-rpg analyze {target}' first.")
            sys.exit(1)

        # Extract feature description
        if source.endswith('.md'):
            # It's a markdown file
            source_path = Path(source)
            if not source_path.exists():
                click.echo(f"Error: File '{source}' not found", err=True)
                sys.exit(1)
            description = source_path.read_text()
        else:
            # It's project:path
            if ':' not in source:
                click.echo("Error: Source must be 'project:path' or a .md file", err=True)
                sys.exit(1)

            src_project, src_path = source.split(':', 1)
            src_proj = registry.get(src_project)
            if not src_proj:
                click.echo(f"Error: Source project '{src_project}' not found", err=True)
                sys.exit(1)

            description = describe_feature(src_proj.path, src_path)

        # Show extracted description
        click.echo("Feature description extracted:")
        click.echo("-" * 60)
        click.echo(description)
        click.echo("-" * 60)
        click.echo("")

        # Allow editing
        if edit:
            description = click.edit(description) or description

        # Generate plan for target
        plan = plan_implementation(target_proj.path, description)
        click.echo(format_implementation_plan(plan))

        if not click.confirm("Proceed with transplant?"):
            return

        # Convert to spec
        spec = plan_to_spec(plan, target_proj.path)
        spec["transplanted_from"] = source

        # Save spec
        from erirpg.specs import save_spec
        spec_path = save_spec(target_proj.path, spec)
        click.echo(f"Spec created: {spec_path}")

        # Offer to start work
        if click.confirm("Start EriRPG run?"):
            from erirpg.agent import Agent
            agent = Agent.from_spec(spec_path, project_path=target_proj.path)
            click.echo(f"Run started: {agent.run.id}")
            click.echo("Use Agent API or 'eri-rpg status' to continue.")

    @cli.command(name="describe-feature")
    @click.argument("project")
    @click.argument("file_path")
    def describe_feature_cmd(project: str, file_path: str):
        """Extract feature description from a source file.

        Useful for preparing transplant descriptions.

        Example:
            eri-rpg describe-feature simpletuner training/klein_lora.py
        """
        from erirpg.implement import describe_feature

        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        description = describe_feature(proj.path, file_path)
        click.echo(description)
