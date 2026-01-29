"""
Plan Commands - Plan management for executable workflows.

Commands (full tier):
- plan generate: Generate plan from spec
- plan show: Display plan contents
- plan list: List plans in project
- plan next: Show next step to execute
- plan step: Update step status
"""

import json
import os
import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register plan group commands with CLI."""

    @cli.group("plan")
    @tier_required("full")
    def plan_group():
        """Plan management commands.

        Plans convert specs into executable step-by-step workflows.
        They track dependencies, risk levels, and progress.

        \b
            plan generate <spec>  - Generate plan from spec
            plan show <plan>      - Display plan contents
            plan list             - List plans in project
            plan next <plan>      - Show next step to execute
        """
        pass

    @plan_group.command("generate")
    @click.argument("spec_path", type=click.Path(exists=True))
    @click.option("-o", "--output", default=None, help="Output path (default: .eri-rpg/plans/)")
    @click.option("-p", "--project", default=None, help="Project path for context")
    def plan_generate(spec_path: str, output: str, project: str):
        """Generate a plan from a spec.

        Creates an execution plan with ordered steps.

        \b
        Example:
            eri-rpg plan generate ./specs/my-task.json
            eri-rpg plan generate ./specs/transplant.json -p ./myproject
        """
        from erirpg.specs import load_spec
        from erirpg.planner import generate_plan, save_plan_to_project
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph

        try:
            spec = load_spec(spec_path)
        except Exception as e:
            click.echo(f"Error loading spec: {e}", err=True)
            sys.exit(1)

        # Get graph and knowledge if project specified
        graph = None
        knowledge = None
        if project:
            registry = Registry.get_instance()
            proj = registry.get(project)
            if proj:
                try:
                    graph = get_or_load_graph(proj)
                    knowledge = graph.knowledge if hasattr(graph, 'knowledge') else None
                except ValueError:
                    pass  # Expected if not indexed

        # Generate plan
        try:
            plan = generate_plan(spec, graph, knowledge)
        except Exception as e:
            click.echo(f"Error generating plan: {e}", err=True)
            sys.exit(1)

        # Save plan
        if output:
            plan.save(output)
            output_path = output
        else:
            project_path = project or os.getcwd()
            output_path = save_plan_to_project(plan, project_path)

        click.echo(f"Generated plan: {output_path}")
        click.echo("")
        click.echo(plan.format_summary())

    @plan_group.command("show")
    @click.argument("path", type=click.Path(exists=True))
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @click.option("--verbose", "-v", is_flag=True, help="Show step details")
    def plan_show(path: str, as_json: bool, verbose: bool):
        """Display plan contents.

        Shows the plan with all steps and their status.

        \b
        Example:
            eri-rpg plan show ./plans/my-plan.json
            eri-rpg plan show ./plans/my-plan.json --verbose
        """
        from erirpg.planner import Plan

        try:
            plan = Plan.load(path)
        except Exception as e:
            click.echo(f"Error loading plan: {e}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(plan.to_dict(), indent=2))
            return

        click.echo(f"Plan: {plan.name or plan.id}")
        click.echo("=" * 50)
        click.echo(f"Spec: {plan.spec_id} ({plan.spec_type})")
        click.echo(f"Status: {plan.status}")
        click.echo(f"Created: {plan.created_at.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"Progress: {plan.completed_steps}/{plan.total_steps} steps")
        click.echo("")
        click.echo("Steps:")

        for step in sorted(plan.steps, key=lambda s: s.order):
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "failed": "✗",
                "skipped": "○",
            }.get(step.status, "?")

            risk_badge = f" [{step.risk}]" if step.risk != "low" else ""
            click.echo(f"  {status_icon} {step.order}. [{step.step_type}] {step.action}{risk_badge}")

            if verbose:
                if step.details:
                    click.echo(f"      Details: {step.details}")
                if step.depends_on:
                    click.echo(f"      Depends on: {', '.join(step.depends_on)}")
                if step.verify_command:
                    click.echo(f"      Verify: {step.verify_command}")
                if step.error:
                    click.echo(f"      Error: {step.error}")
                click.echo("")

    @plan_group.command("list")
    @click.option("-p", "--path", default=None, help="Project path (default: current directory)")
    def plan_list(path: str):
        """List plans in a project.

        Shows all plans stored in the project's .eri-rpg/plans/ directory.

        \b
        Example:
            eri-rpg plan list
            eri-rpg plan list -p /path/to/project
        """
        from erirpg.planner import list_plans, Plan

        project_path = path or os.getcwd()
        plans = list_plans(project_path)

        if not plans:
            click.echo("No plans found.")
            click.echo("\nGenerate one with: eri-rpg plan generate <spec>")
            return

        click.echo(f"Plans in {project_path}:")
        click.echo("")

        for plan_path in plans:
            try:
                p = Plan.load(plan_path)
                status_icon = {
                    "pending": "○",
                    "in_progress": "◐",
                    "completed": "●",
                    "failed": "✗",
                }.get(p.status, "?")

                click.echo(f"  {status_icon} {p.name or p.id}")
                click.echo(f"    Status: {p.status} ({p.completed_steps}/{p.total_steps} steps)")
                click.echo(f"    Path: {plan_path}")
            except Exception as e:
                click.echo(f"  [error] {plan_path}: {e}")
            click.echo("")

    @plan_group.command("next")
    @click.argument("path", type=click.Path(exists=True))
    def plan_next(path: str):
        """Show next step to execute.

        Displays the next pending step that can be executed.

        \b
        Example:
            eri-rpg plan next ./plans/my-plan.json
        """
        from erirpg.planner import Plan

        try:
            plan = Plan.load(path)
        except Exception as e:
            click.echo(f"Error loading plan: {e}", err=True)
            sys.exit(1)

        if plan.status == "completed":
            click.echo("Plan is complete!")
            return

        if plan.status == "failed":
            # Find failed step
            for step in plan.steps:
                if step.status == "failed":
                    click.echo(f"Plan failed at step {step.order}: {step.action}")
                    click.echo(f"Error: {step.error}")
                    return

        next_step = plan.get_next_step()

        if not next_step:
            click.echo("No steps ready to execute.")
            click.echo("All pending steps may be blocked by incomplete dependencies.")
            return

        click.echo(f"Next step: {next_step.order}. {next_step.action}")
        click.echo("")
        click.echo(f"Type: {next_step.step_type}")
        click.echo(f"Target: {next_step.target}")
        if next_step.details:
            click.echo(f"Details: {next_step.details}")
        if next_step.risk != "low":
            click.echo(f"Risk: {next_step.risk} - {next_step.risk_reason}")
        if next_step.verify_command:
            click.echo(f"Verify with: {next_step.verify_command}")

        click.echo("")
        click.echo(f"To mark complete: eri-rpg plan step {path} {next_step.id} complete")

    @plan_group.command("step")
    @click.argument("path", type=click.Path(exists=True))
    @click.argument("step_id")
    @click.argument("action", type=click.Choice(["start", "complete", "fail", "skip"]))
    @click.option("--error", default="", help="Error message (for fail action)")
    def plan_step(path: str, step_id: str, action: str, error: str):
        """Update step status.

        Mark a step as started, completed, failed, or skipped.

        \b
        Example:
            eri-rpg plan step ./plan.json step-00-abc123 start
            eri-rpg plan step ./plan.json step-00-abc123 complete
            eri-rpg plan step ./plan.json step-00-abc123 fail --error "Import error"
        """
        from erirpg.planner import Plan

        try:
            plan = Plan.load(path)
        except Exception as e:
            click.echo(f"Error loading plan: {e}", err=True)
            sys.exit(1)

        step = plan.get_step(step_id)
        if not step:
            click.echo(f"Step not found: {step_id}", err=True)
            sys.exit(1)

        if action == "start":
            step.mark_in_progress()
            click.echo(f"Started: {step.action}")
        elif action == "complete":
            step.mark_completed()
            click.echo(f"Completed: {step.action}")
        elif action == "fail":
            step.mark_failed(error or "Unknown error")
            click.echo(f"Failed: {step.action}")
        elif action == "skip":
            step.mark_skipped()
            click.echo(f"Skipped: {step.action}")

        plan.update_stats()
        plan.save(path)

        click.echo(f"\nPlan progress: {plan.completed_steps}/{plan.total_steps} steps")
        if plan.status == "completed":
            click.echo("Plan complete!")
