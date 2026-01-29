"""
Goal Commands - Spec-driven execution commands.

Commands (full tier):
- goal-plan: Generate a spec from a goal
- goal-run: Execute a spec for a project
- goal-status: Show spec execution status for a project
"""

import os
import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register goal commands with CLI."""
    from erirpg.registry import Registry
    from erirpg.indexer import get_or_load_graph
    from erirpg.memory import load_knowledge

    @cli.command("goal-plan")
    @click.argument("project")
    @click.argument("goal")
    @click.option("-o", "--output", default=None, help="Output spec file path")
    @tier_required("full")
    def goal_plan(project: str, goal: str, output: str):
        """Generate a spec from a goal.

        Creates a structured spec with ordered steps from a natural language goal.
        This is the entry point for spec-driven execution.

        \b
        Example:
            eri-rpg goal-plan eritrainer "add logging to config.py"
            eri-rpg goal-plan myproject "refactor auth module" -o spec.yaml
        """
        from erirpg.spec import Spec
        from erirpg.planner import Planner

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            click.echo(f"\nAdd it first: eri-rpg add {project} /path/to/project")
            sys.exit(1)

        # Load graph and knowledge for intelligent planning
        graph = None
        knowledge = None
        try:
            graph = get_or_load_graph(proj)
        except Exception as e:
            import sys; print(f"[EriRPG] {e}", file=sys.stderr)

        try:
            knowledge = load_knowledge(proj.path, project)
        except Exception as e:
            import sys; print(f"[EriRPG] {e}", file=sys.stderr)

        # Generate spec
        planner = Planner(project, graph, knowledge)
        spec = planner.plan(goal)

        # Save spec
        if output:
            spec_path = output
        else:
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            os.makedirs(spec_dir, exist_ok=True)
            spec_path = os.path.join(spec_dir, f"{spec.id}.yaml")

        spec.save(spec_path)

        click.echo(f"Generated spec: {spec_path}")
        click.echo("")
        click.echo(spec.format_status())
        click.echo("")
        click.echo(f"Execute with: eri-rpg goal-run {project}")

    @cli.command("goal-run")
    @click.argument("project")
    @click.option("--spec", "spec_path", default=None, help="Specific spec file to run")
    @click.option("--resume", "resume_run", is_flag=True, help="Resume incomplete run")
    def goal_run(project: str, spec_path: str, resume_run: bool):
        """Execute a spec for a project.

        Runs the latest spec (or specified spec) step by step.
        Agent refuses to proceed if verification fails.

        \b
        Example:
            eri-rpg goal-run eritrainer
            eri-rpg goal-run myproject --spec ./spec.yaml
            eri-rpg goal-run myproject --resume
        """
        from erirpg.spec import Spec
        from erirpg.agent import Agent

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check for resume
        if resume_run:
            agent = Agent.resume(proj.path)
            if agent:
                click.echo(f"Resumed run: {agent._run.id if agent._run else 'unknown'}")
                click.echo("")
                click.echo(agent.get_spec_status())
                return
            else:
                click.echo("No incomplete run to resume.")

        # Load spec
        if spec_path:
            spec = Spec.load(spec_path)
        else:
            # Find latest spec
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            if not os.path.exists(spec_dir):
                click.echo("No specs found.")
                click.echo(f"\nGenerate one: eri-rpg goal-plan {project} \"<goal>\"")
                sys.exit(1)

            specs = sorted([
                os.path.join(spec_dir, f)
                for f in os.listdir(spec_dir)
                if f.endswith(".yaml")
            ], key=os.path.getmtime, reverse=True)

            if not specs:
                click.echo("No specs found.")
                click.echo(f"\nGenerate one: eri-rpg goal-plan {project} \"<goal>\"")
                sys.exit(1)

            spec = Spec.load(specs[0])
            click.echo(f"Using latest spec: {specs[0]}")
            click.echo("")

        # Create agent from spec
        agent = Agent.from_new_spec(spec, proj.path)

        click.echo(f"Started run: {agent._run.id if agent._run else 'new'}")
        click.echo("")
        click.echo(agent.get_spec_status())
        click.echo("")
        click.echo("Use the Agent API in Claude Code:")
        click.echo("  agent = Agent.resume(project_path)")
        click.echo("  step = agent.next_step()")
        click.echo("  # Execute step")
        click.echo("  if agent.verify_step():")
        click.echo("      agent.complete_step()")

    @cli.command("goal-status")
    @click.argument("project")
    def goal_status(project: str):
        """Show spec execution status for a project.

        Displays progress, current step, and any blockers.

        \b
        Example:
            eri-rpg goal-status eritrainer
        """
        from erirpg.agent import Agent

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Try to resume existing run
        agent = Agent.resume(proj.path)

        if not agent:
            click.echo(f"No active run for {project}.")
            click.echo("")

            # Check for specs
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            if os.path.exists(spec_dir):
                specs = [f for f in os.listdir(spec_dir) if f.endswith(".yaml")]
                if specs:
                    click.echo(f"Found {len(specs)} spec(s).")
                    click.echo(f"Start with: eri-rpg goal-run {project}")
                else:
                    click.echo(f"Generate a spec: eri-rpg goal-plan {project} \"<goal>\"")
            else:
                click.echo(f"Generate a spec: eri-rpg goal-plan {project} \"<goal>\"")
            return

        click.echo(agent.get_spec_status())
