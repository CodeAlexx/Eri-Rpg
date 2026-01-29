"""
Run Commands - Execution management for plans.

Commands:
- run start: Start executing a plan
- run resume: Resume a paused run
- run list: List all runs
- run show: Show run details
- run report: Generate run report
- run step: Update step status in a run
"""

import json
import os
import sys
import click


def register(cli):
    """Register run group commands with CLI."""

    @cli.group("run")
    def run_group():
        """Run management commands.

        Runs execute plans step-by-step with pause/resume support.

        \b
            run start <plan>   - Start executing a plan
            run resume <run>   - Resume a paused run
            run list           - List all runs
            run show <run>     - Show run details
            run report <run>   - Generate run report
        """
        pass

    @run_group.command("start")
    @click.argument("plan_path", type=click.Path(exists=True))
    @click.option("-p", "--project", default=None, help="Project path")
    def run_start(plan_path: str, project: str):
        """Start executing a plan.

        Creates a new run and shows the first step to execute.

        \b
        Example:
            eri-rpg run start ./plans/my-plan.json
        """
        from erirpg.planner import Plan
        from erirpg.runner import Runner

        project_path = project or os.getcwd()

        try:
            plan = Plan.load(plan_path)
        except Exception as e:
            click.echo(f"Error loading plan: {e}", err=True)
            sys.exit(1)

        runner = Runner(plan, project_path)
        run = runner.start()

        click.echo(f"Started run: {run.id}")
        click.echo(f"Plan: {plan.name or plan.id}")
        click.echo("")

        next_step = runner.get_next_step()
        if next_step:
            ctx = runner.prepare_step(next_step)
            click.echo(f"First step: {next_step.action}")
            click.echo(f"Context: {ctx.context_file}")
            click.echo("")
            click.echo("Give the context to Claude, then mark complete:")
            click.echo(f"  eri-rpg run step {run.id} {next_step.id} complete")
        else:
            click.echo("No steps to execute.")

    @run_group.command("resume")
    @click.argument("run_id")
    @click.option("-p", "--project", default=None, help="Project path")
    def run_resume(run_id: str, project: str):
        """Resume a paused run.

        Continues from where the run left off.

        \b
        Example:
            eri-rpg run resume run-my-plan-20240101-120000
        """
        from erirpg.runner import Runner

        project_path = project or os.getcwd()

        try:
            runner = Runner.resume(run_id, project_path)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        click.echo(f"Resumed run: {run_id}")
        progress = runner.get_progress()
        click.echo(f"Progress: {progress['completed_steps']}/{progress['total_steps']} steps")
        click.echo("")

        next_step = runner.get_next_step()
        if next_step:
            ctx = runner.prepare_step(next_step)
            click.echo(f"Next step: {next_step.action}")
            click.echo(f"Context: {ctx.context_file}")
        elif progress['status'] == 'completed':
            click.echo("Run is complete!")
        elif progress['status'] == 'failed':
            click.echo("Run has failed. Check the report for details.")
        else:
            click.echo("No steps ready to execute.")

    @run_group.command("list")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("-n", "--limit", default=10, help="Max runs to show")
    def run_list_cmd(project: str, limit: int):
        """List all runs in a project.

        \b
        Example:
            eri-rpg run list
            eri-rpg run list -n 5
        """
        from erirpg.runner import list_runs

        project_path = project or os.getcwd()
        runs = list_runs(project_path)

        if not runs:
            click.echo("No runs found.")
            click.echo("\nStart one with: eri-rpg run start <plan>")
            return

        click.echo(f"Runs in {project_path}:")
        click.echo("")

        for run in runs[:limit]:
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "paused": "⏸",
                "completed": "●",
                "failed": "✗",
                "cancelled": "○",
            }.get(run.status, "?")

            click.echo(f"  {status_icon} {run.id}")
            click.echo(f"    Plan: {run.plan_id}")
            click.echo(f"    Status: {run.status} ({run.completed_steps} steps done)")
            click.echo(f"    Started: {run.started_at.strftime('%Y-%m-%d %H:%M')}")
            click.echo("")

        if len(runs) > limit:
            click.echo(f"  ... and {len(runs) - limit} more")

    @run_group.command("show")
    @click.argument("run_id")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def run_show(run_id: str, project: str, as_json: bool):
        """Show run details.

        \b
        Example:
            eri-rpg run show run-my-plan-20240101-120000
        """
        from erirpg.runs import load_run

        project_path = project or os.getcwd()
        run = load_run(project_path, run_id)

        if not run:
            click.echo(f"Run not found: {run_id}", err=True)
            sys.exit(1)

        if as_json:
            click.echo(json.dumps(run.to_dict(), indent=2))
            return

        click.echo(run.format_summary())
        click.echo("")

        if run.step_results:
            click.echo("Step Results:")
            for result in run.step_results:
                status_icon = {
                    "pending": "○",
                    "in_progress": "◐",
                    "completed": "●",
                    "failed": "✗",
                    "skipped": "○",
                }.get(result.status, "?")

                click.echo(f"  {status_icon} {result.step_id}: {result.status}")
                if result.error:
                    click.echo(f"      Error: {result.error}")
                if result.duration:
                    click.echo(f"      Duration: {result.duration:.1f}s")

    @run_group.command("report")
    @click.argument("run_id")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("-o", "--output", default=None, help="Output file path")
    def run_report(run_id: str, project: str, output: str):
        """Generate a run report.

        \b
        Example:
            eri-rpg run report run-my-plan-20240101-120000
            eri-rpg run report run-my-plan-20240101-120000 -o report.md
        """
        from erirpg.runner import Runner

        project_path = project or os.getcwd()

        try:
            runner = Runner.resume(run_id, project_path)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        report = runner.get_report()

        if output:
            with open(output, "w") as f:
                f.write(report)
            click.echo(f"Report saved to: {output}")
        else:
            click.echo(report)

    @run_group.command("step")
    @click.argument("run_id")
    @click.argument("step_id")
    @click.argument("action", type=click.Choice(["start", "complete", "fail", "skip"]))
    @click.option("--error", default="", help="Error message (for fail action)")
    @click.option("-p", "--project", default=None, help="Project path")
    def run_step(run_id: str, step_id: str, action: str, error: str, project: str):
        """Update step status in a run.

        \b
        Example:
            eri-rpg run step run-xxx step-00-abc start
            eri-rpg run step run-xxx step-00-abc complete
            eri-rpg run step run-xxx step-00-abc fail --error "Import failed"
        """
        from erirpg.runner import Runner

        project_path = project or os.getcwd()

        try:
            runner = Runner.resume(run_id, project_path)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        step = runner.plan.get_step(step_id)
        if not step:
            click.echo(f"Step not found: {step_id}", err=True)
            sys.exit(1)

        if action == "start":
            runner.mark_step_started(step)
            click.echo(f"Started: {step.action}")
        elif action == "complete":
            runner.mark_step_completed(step)
            click.echo(f"Completed: {step.action}")
        elif action == "fail":
            runner.mark_step_failed(step, error or "Unknown error")
            click.echo(f"Failed: {step.action}")
        elif action == "skip":
            runner.mark_step_skipped(step)
            click.echo(f"Skipped: {step.action}")

        progress = runner.get_progress()
        click.echo(f"\nProgress: {progress['completed_steps']}/{progress['total_steps']} steps")

        if progress['status'] == 'completed':
            click.echo("Run complete!")
        else:
            next_step = runner.get_next_step()
            if next_step:
                click.echo(f"\nNext step: {next_step.action}")
