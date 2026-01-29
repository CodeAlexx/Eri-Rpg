"""
Verify Commands - Code verification and quality checks.

Commands:
- verify run: Run verification for a run
- verify config: Show/create verification config
- verify results: Show verification results
"""

import json
import os
import sys
import click


def register(cli):
    """Register verify group commands with CLI."""

    @cli.group("verify")
    def verify_group():
        """Verification commands.

        Run lint, test, and other validation commands to ensure code quality.

        \b
            verify run <run_id>       - Run verification for a run
            verify config             - Show/create verification config
            verify results <run_id>   - Show verification results
        """
        pass

    @verify_group.command("run")
    @click.argument("run_id")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("--step", default=None, help="Run for specific step only")
    def verify_run(run_id: str, project: str, step: str):
        """Run verification commands for a run.

        Executes all configured verification commands and saves results.

        \b
        Example:
            eri-rpg verify run run-my-plan-20240101-120000
            eri-rpg verify run run-xxx --step step-00-abc
        """
        from erirpg.runs import load_run
        from erirpg.verification import (
            Verifier,
            load_verification_config,
            save_verification_result,
            VerificationConfig,
        )

        project_path = project or os.getcwd()
        run = load_run(project_path, run_id)

        if not run:
            click.echo(f"Run not found: {run_id}", err=True)
            sys.exit(1)

        # Load config
        config = load_verification_config(project_path)
        if not config:
            click.echo("No verification config found.", err=True)
            click.echo("Create one with: eri-rpg verify config --init")
            sys.exit(1)

        verifier = Verifier(config, project_path)

        if step:
            # Run for single step
            result = verifier.run_verification(step)
            save_verification_result(project_path, run_id, result)
            click.echo(result.format_report())
        else:
            # Run for all steps
            click.echo(f"Running verification for {len(run.step_results)} steps...")
            click.echo("")

            for step_result in run.step_results:
                if step_result.status == "completed":
                    click.echo(f"Verifying: {step_result.step_id}")
                    result = verifier.run_verification(step_result.step_id)
                    save_verification_result(project_path, run_id, result)

                    if result.passed:
                        click.echo(f"  ✓ Passed")
                    else:
                        click.echo(f"  ✗ Failed")
                        for cmd_result in result.failed_commands:
                            click.echo(f"    - {cmd_result.name}: exit {cmd_result.exit_code}")

            click.echo("")
            click.echo("Verification complete.")

    @verify_group.command("config")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("--init", "init_config", is_flag=True, help="Create default config")
    @click.option("--type", "project_type", type=click.Choice(["python", "node"]), default="python", help="Project type for default config")
    def verify_config(project: str, init_config: bool, project_type: str):
        """Show or create verification config.

        \b
        Example:
            eri-rpg verify config              # Show current config
            eri-rpg verify config --init       # Create default Python config
            eri-rpg verify config --init --type node  # Create Node.js config
        """
        from erirpg.verification import (
            load_verification_config,
            save_verification_config,
            get_default_python_config,
            get_default_node_config,
        )

        project_path = project or os.getcwd()

        if init_config:
            if project_type == "python":
                config = get_default_python_config()
            else:
                config = get_default_node_config()

            path = save_verification_config(project_path, config)
            click.echo(f"Created verification config: {path}")
            click.echo("")
            click.echo("Commands:")
            for cmd in config.commands:
                req = "required" if cmd.required else "optional"
                click.echo(f"  {cmd.name}: {cmd.command} ({req})")
            return

        config = load_verification_config(project_path)
        if not config:
            click.echo("No verification config found.")
            click.echo("Create one with: eri-rpg verify config --init")
            return

        click.echo("Verification Config")
        click.echo("=" * 40)
        click.echo(f"Run after each step: {config.run_after_each_step}")
        click.echo(f"Run at checkpoints: {config.run_at_checkpoints}")
        click.echo(f"Stop on failure: {config.stop_on_failure}")
        click.echo("")
        click.echo("Commands:")
        for cmd in config.commands:
            req = "required" if cmd.required else "optional"
            click.echo(f"  {cmd.name}: {cmd.command} ({req})")
            if cmd.run_on:
                click.echo(f"    Only on: {', '.join(cmd.run_on)}")

    @verify_group.command("results")
    @click.argument("run_id")
    @click.option("-p", "--project", default=None, help="Project path")
    @click.option("--step", default=None, help="Show results for specific step")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def verify_results(run_id: str, project: str, step: str, as_json: bool):
        """Show verification results for a run.

        \b
        Example:
            eri-rpg verify results run-my-plan-20240101-120000
            eri-rpg verify results run-xxx --step step-00-abc
        """
        from erirpg.verification import (
            list_verification_results,
            load_verification_result,
            format_verification_summary,
        )

        project_path = project or os.getcwd()

        if step:
            result = load_verification_result(project_path, run_id, step)
            if not result:
                click.echo(f"No verification result for step: {step}", err=True)
                sys.exit(1)

            if as_json:
                click.echo(json.dumps(result.to_dict(), indent=2))
            else:
                click.echo(result.format_report())
        else:
            results = list_verification_results(project_path, run_id)

            if not results:
                click.echo("No verification results found.")
                click.echo(f"Run verification with: eri-rpg verify run {run_id}")
                return

            if as_json:
                click.echo(json.dumps([r.to_dict() for r in results], indent=2))
            else:
                click.echo(format_verification_summary(results))
