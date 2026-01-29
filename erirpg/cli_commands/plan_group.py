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
    @tier_required("standard")  # Changed from full - planning is core functionality
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
    @click.option("--verify/--no-verify", default=True, help="Run verification after generation (default: yes)")
    def plan_generate(spec_path: str, output: str, project: str, verify: bool):
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

        # Auto-verification
        if verify:
            from erirpg.verifier import (
                verify_plan as run_verification,
                format_verification_result,
            )

            click.echo("")
            click.echo("Running verification...")
            click.echo("")

            result = run_verification(spec.to_dict(), plan.to_dict())
            click.echo(format_verification_result(result))

            if result.has_critical_gaps:
                click.echo("")
                click.echo("\u26a0\ufe0f  Critical gaps found. Review and revise plan before proceeding.")
                sys.exit(1)
            elif result.error:
                click.echo("")
                click.echo(f"\u26a0\ufe0f  Verification failed: {result.error}")
                click.echo("Plan generated but not verified. Use --no-verify to skip.")
            elif result.gap_count > 0:
                click.echo("")
                click.echo(f"\u2139\ufe0f  {result.gap_count} non-critical gaps found. Review before proceeding.")

    @plan_group.command("show")
    @click.argument("project_or_path")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @click.option("--verbose", "-v", is_flag=True, help="Show step details")
    def plan_show(project_or_path: str, as_json: bool, verbose: bool):
        """Display plan contents.

        Shows the plan with all steps and their status.
        Accepts either a project name or a direct path to a plan file.

        \b
        Example:
            eri-rpg plan show myproject
            eri-rpg plan show ./plans/my-plan.json --verbose
        """
        from erirpg.planner import Plan, list_plans
        from erirpg.registry import Registry

        # Try to resolve as project name FIRST (before checking file existence)
        registry = Registry.get_instance()
        proj = registry.get(project_or_path)

        if proj:
            # It's a registered project name - find its plans
            plans = list_plans(proj.path)
            if not plans:
                click.echo(f"No plans found for project '{project_or_path}'")
                click.echo("Generate one with: eri-rpg plan generate <spec>")
                sys.exit(1)
            elif len(plans) == 1:
                path = plans[0]
            else:
                click.echo(f"Multiple plans found for '{project_or_path}':")
                for i, p in enumerate(plans):
                    click.echo(f"  {i+1}. {os.path.basename(p)}")
                click.echo("\nSpecify the full path to show a specific plan.")
                sys.exit(1)
        elif os.path.exists(project_or_path) and os.path.isfile(project_or_path):
            # It's a file path
            path = project_or_path
        else:
            click.echo(f"Not found: '{project_or_path}' (not a project name or plan file)", err=True)
            sys.exit(1)

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
    @click.argument("project", default=None, required=False)
    @click.option("-p", "--path", default=None, help="Project path (default: current directory)")
    def plan_list(project: str, path: str):
        """List plans in a project.

        Shows all plans stored in the project's .eri-rpg/plans/ directory.

        \b
        Example:
            eri-rpg plan list
            eri-rpg plan list myproject
            eri-rpg plan list -p /path/to/project
        """
        from erirpg.planner import list_plans, Plan
        from erirpg.registry import Registry

        # Resolve project path
        if project:
            registry = Registry.get_instance()
            proj = registry.get(project)
            if proj:
                project_path = proj.path
            else:
                click.echo(f"Project not found: {project}", err=True)
                sys.exit(1)
        else:
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
    @click.argument("project_or_path")
    def plan_next(project_or_path: str):
        """Show next step to execute.

        Displays the next pending step that can be executed.
        Accepts either a project name or a direct path to a plan file.

        \b
        Example:
            eri-rpg plan next myproject
            eri-rpg plan next ./plans/my-plan.json
        """
        from erirpg.planner import Plan, list_plans
        from erirpg.registry import Registry

        # Try to resolve as project name FIRST (before checking file existence)
        registry = Registry.get_instance()
        proj = registry.get(project_or_path)

        if proj:
            # It's a registered project name
            plans = list_plans(proj.path)
            if not plans:
                click.echo(f"No plans found for project '{project_or_path}'")
                sys.exit(1)
            elif len(plans) == 1:
                path = plans[0]
            else:
                click.echo(f"Multiple plans found. Specify one:")
                for p in plans:
                    click.echo(f"  {os.path.basename(p)}")
                sys.exit(1)
        elif os.path.exists(project_or_path) and os.path.isfile(project_or_path):
            path = project_or_path
        else:
            click.echo(f"Not found: '{project_or_path}' (not a project or plan file)", err=True)
            sys.exit(1)

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

    @plan_group.command("verify")
    @click.argument("project_or_path")
    @click.option("-s", "--spec", "spec_path", default=None, help="Path to spec file")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @click.option(
        "--model",
        type=click.Choice(["auto", "sonnet", "opus"]),
        default="auto",
        help="Model to use: auto (default), sonnet, or opus",
    )
    @click.option(
        "--no-escalate",
        is_flag=True,
        help="Use sonnet only, skip auto-escalation",
    )
    def plan_verify(project_or_path: str, spec_path: str, as_json: bool, model: str, no_escalate: bool):
        """Verify plan covers all spec requirements.

        Uses adversarial Claude verification to find gaps between
        the spec (what should be done) and the plan (how to do it).

        Quantifier audit is mandatory - "all X" must cover ALL X.

        \b
        Model selection:
          --model auto      Sonnet first, escalate to Opus if needed (default)
          --model sonnet    Force Sonnet only
          --model opus      Force Opus only
          --no-escalate     Same as --model sonnet

        \b
        Example:
            eri-rpg plan verify myproject
            eri-rpg plan verify ./plans/my-plan.json --spec ./specs/my-spec.json
            eri-rpg plan verify myproject --model opus
        """
        from erirpg.planner import Plan, list_plans
        from erirpg.specs import load_spec as load_spec_file
        from erirpg.verifier import (
            verify_plan as run_verification,
            format_verification_result,
            format_verification_json,
            format_status_line,
            format_model_comparison,
            should_escalate,
        )
        from erirpg.registry import Registry

        # Model constants
        SONNET_MODEL = "claude-sonnet-4-20250514"
        OPUS_MODEL = "claude-opus-4-20250514"

        # Handle --no-escalate as alias for --model sonnet
        if no_escalate:
            model = "sonnet"

        # Resolve plan path
        registry = Registry.get_instance()
        proj = registry.get(project_or_path)

        if proj:
            # It's a project name
            plans = list_plans(proj.path)
            if not plans:
                click.echo(f"No plans found for project '{project_or_path}'")
                click.echo("Generate one with: eri-rpg plan generate <spec>")
                sys.exit(1)
            elif len(plans) == 1:
                plan_path = plans[0]
            else:
                click.echo(f"Multiple plans found for '{project_or_path}':")
                for i, p in enumerate(plans):
                    click.echo(f"  {i+1}. {os.path.basename(p)}")
                click.echo("\nSpecify the full path to verify a specific plan.")
                sys.exit(1)
            project_path = proj.path
        elif os.path.exists(project_or_path) and os.path.isfile(project_or_path):
            plan_path = project_or_path
            # Try to infer project path from plan location
            project_path = os.path.dirname(os.path.dirname(os.path.dirname(plan_path)))
        else:
            click.echo(f"Not found: '{project_or_path}' (not a project name or plan file)", err=True)
            sys.exit(1)

        # Load plan
        try:
            plan = Plan.load(plan_path)
        except Exception as e:
            click.echo(f"Error loading plan: {e}", err=True)
            sys.exit(1)

        # Find or load spec
        spec_data = None
        if spec_path:
            try:
                spec = load_spec_file(spec_path)
                spec_data = spec.to_dict()
            except Exception as e:
                click.echo(f"Error loading spec: {e}", err=True)
                sys.exit(1)
        else:
            # Try to find spec by ID from plan
            specs_dir = os.path.join(project_path, ".eri-rpg", "specs")
            if os.path.exists(specs_dir) and plan.spec_id:
                for filename in os.listdir(specs_dir):
                    if filename.endswith(".json"):
                        try:
                            spec = load_spec_file(os.path.join(specs_dir, filename))
                            if spec.id == plan.spec_id:
                                spec_data = spec.to_dict()
                                break
                        except Exception:
                            pass

        if not spec_data:
            click.echo("Could not find spec for this plan.", err=True)
            click.echo("Use --spec to specify the spec file path.", err=True)
            sys.exit(1)

        # JSON mode - simple single-model run
        if as_json:
            selected_model = OPUS_MODEL if model == "opus" else SONNET_MODEL
            result = run_verification(spec_data, plan.to_dict(), model=selected_model)
            click.echo(format_verification_json(result))
            sys.exit(1 if result.has_critical_gaps else (2 if result.error else 0))

        # Interactive mode with status lines
        sonnet_result = None
        opus_result = None
        final_result = None

        # Determine which models to run
        if model == "opus":
            # Force Opus only
            click.echo(format_status_line("Verifier", "opus", "eri:verify"))
            click.echo("")
            click.echo("Running verification with Opus...")
            click.echo("")
            opus_result = run_verification(spec_data, plan.to_dict(), model=OPUS_MODEL)
            final_result = opus_result

        elif model == "sonnet":
            # Force Sonnet only (or --no-escalate)
            click.echo(format_status_line("Verifier", "sonnet", "eri:verify"))
            click.echo("")
            click.echo("Running verification with Sonnet...")
            click.echo("")
            sonnet_result = run_verification(spec_data, plan.to_dict(), model=SONNET_MODEL)
            final_result = sonnet_result

        else:
            # Auto mode: Sonnet first, escalate if needed
            click.echo(format_status_line("Verifier", "sonnet", "eri:verify"))
            click.echo("")
            click.echo("Running verification with Sonnet...")
            click.echo("")
            sonnet_result = run_verification(spec_data, plan.to_dict(), model=SONNET_MODEL)

            # Check if we should escalate
            escalate, reason = should_escalate(sonnet_result)

            if escalate and not sonnet_result.error:
                click.echo("")
                click.echo(f"\u26a1 Escalating to Opus \u2014 {reason}")
                click.echo("")
                click.echo(format_status_line("Verifier", "opus", "eri:verify"))
                click.echo("")
                click.echo("Re-running full verification with Opus...")
                click.echo("")
                opus_result = run_verification(spec_data, plan.to_dict(), model=OPUS_MODEL)

                # Show comparison
                click.echo(format_model_comparison(sonnet_result, opus_result))
                click.echo("")

                final_result = opus_result
            else:
                final_result = sonnet_result

        # Output final results
        model_used = "Opus" if final_result is opus_result else "Sonnet"
        click.echo(f"{'=' * 59}")
        click.echo(f" ERI:VERIFY RESULTS ({model_used})")
        click.echo(f"{'=' * 59}")
        click.echo("")

        # Skip the header from format_verification_result since we added our own
        result_text = format_verification_result(final_result)
        # Remove the first 4 lines (header) from the result
        lines = result_text.split("\n")
        click.echo("\n".join(lines[4:]))

        # Return to ready state
        click.echo("")
        click.echo(format_status_line("Default", "sonnet", "ready"))
        click.echo("Verification complete.")

        # Exit code based on critical gaps
        if final_result.has_critical_gaps:
            sys.exit(1)
        elif final_result.error:
            sys.exit(2)
        else:
            sys.exit(0)
