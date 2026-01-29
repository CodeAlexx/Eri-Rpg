"""
Orchestration Commands - Task parsing and workflow coordination.

Commands:
- do: Smart mode - parse task and suggest steps
- status: Show current status and next step
- validate: Validate implementation
- diagnose: Diagnose what went wrong
- reset: Reset state to idle
"""

import os
import re
import sys
import click


def register(cli):
    """Register orchestration commands with CLI."""

    @cli.command("do")
    @click.argument("task")
    def do_task(task: str):
        """Smart mode - figure out steps for a task.

        Parses task description and suggests/executes steps.
        """
        from erirpg.state import State

        state = State.load()
        state.update(current_task=task, phase="idle")
        state.log("start", task)

        # Parse task patterns
        task_lower = task.lower()

        # Pattern: "transplant X from Y to Z"
        match = re.search(r"transplant\s+(.+?)\s+from\s+(\w+)\s+to\s+(\w+)", task_lower)
        if match:
            capability, source, target = match.groups()
            click.echo(f"Task: Transplant '{capability}' from {source} to {target}")
            click.echo("")
            click.echo("Steps:")
            click.echo(f"  1. eri-rpg extract {source} \"{capability}\" -o feature.json")
            click.echo(f"  2. eri-rpg plan feature.json {target}")
            click.echo(f"  3. eri-rpg context feature.json {target}")
            click.echo("  4. Give context to Claude Code")
            click.echo("  5. eri-rpg validate")
            return

        # Pattern: "find X in Y"
        match = re.search(r"find\s+(.+?)\s+in\s+(\w+)", task_lower)
        if match:
            capability, project = match.groups()
            click.echo(f"Finding '{capability}' in {project}...")
            # Actually run find
            from click.testing import CliRunner
            from erirpg.cli_commands.explore import register as explore_register

            # Create a temporary CLI group to get the find command
            temp_cli = click.Group()
            explore_register(temp_cli)
            find_cmd = temp_cli.commands.get('find')

            runner = CliRunner()
            result = runner.invoke(find_cmd, [project, capability])
            click.echo(result.output)
            return

        # Pattern: "what uses X in Y"
        match = re.search(r"what\s+uses\s+(.+?)\s+in\s+(\w+)", task_lower)
        if match:
            module, project = match.groups()
            click.echo(f"Analyzing impact of {module} in {project}...")
            from click.testing import CliRunner
            from erirpg.cli_commands.explore import register as explore_register

            # Create a temporary CLI group to get the impact command
            temp_cli = click.Group()
            explore_register(temp_cli)
            impact_cmd = temp_cli.commands.get('impact')

            runner = CliRunner()
            result = runner.invoke(impact_cmd, [project, module])
            click.echo(result.output)
            return

        # Unknown pattern
        click.echo("I don't recognize that task pattern.")
        click.echo("")
        click.echo("Supported patterns:")
        click.echo("  - transplant <capability> from <source> to <target>")
        click.echo("  - find <capability> in <project>")
        click.echo("  - what uses <module> in <project>")

    @cli.command()
    def status():
        """Show current status and next step."""
        from erirpg.state import State

        state = State.load()
        click.echo(state.format_status())

    @cli.command()
    def validate():
        """Validate Claude's implementation.

        Checks if transplant was completed correctly.
        """
        from erirpg.state import State
        from erirpg.ops import TransplantPlan
        from erirpg.registry import Registry

        state = State.load()

        if state.phase not in ["context_ready", "implementing"]:
            click.echo("Nothing to validate. Start a transplant first.")
            return

        if not state.plan_file or not os.path.exists(state.plan_file):
            click.echo("No plan file found. Cannot validate.")
            return

        transplant_plan = TransplantPlan.load(state.plan_file)
        registry = Registry.get_instance()
        target = registry.get(transplant_plan.target_project)

        if not target:
            click.echo(f"Target project '{transplant_plan.target_project}' not found.")
            return

        click.echo(f"Validating transplant to {transplant_plan.target_project}...")
        click.echo("")

        # Check mappings
        for m in transplant_plan.mappings:
            if m.action == "CREATE":
                click.echo(f"? {m.source_interface}: Manual check needed")
            elif m.action == "ADAPT":
                click.echo(f"? {m.source_interface} -> {m.target_interface}: Manual check needed")

        # Check wiring
        for w in transplant_plan.wiring:
            click.echo(f"? {w.file}: {w.action} - Manual check needed")

        click.echo("")
        click.echo("Manual verification required.")
        click.echo("If implementation is complete, run: eri-rpg status")

        state.update(phase="validating")

    @cli.command()
    def diagnose():
        """Diagnose what went wrong.

        Analyzes current state and suggests fixes.
        """
        from erirpg.state import State
        from erirpg.ops import TransplantPlan

        state = State.load()

        click.echo("Diagnosis:")
        click.echo("")

        if state.phase == "idle":
            click.echo("No active task. Start with: eri-rpg do '<task>'")
            return

        if not state.plan_file:
            click.echo("No plan file. Need to plan first.")
            return

        if not os.path.exists(state.plan_file):
            click.echo(f"Plan file missing: {state.plan_file}")
            return

        transplant_plan = TransplantPlan.load(state.plan_file)

        click.echo("Check these items:")
        click.echo("")

        for m in transplant_plan.mappings:
            if m.action == "CREATE":
                click.echo(f"1. Create {m.source_interface}")
                click.echo(f"   Suggested path: {m.notes}")
            elif m.action == "ADAPT":
                click.echo(f"1. Update {m.target_module} to include {m.source_interface} behavior")

        for w in transplant_plan.wiring:
            click.echo(f"2. {w.file}:")
            click.echo(f"   {w.details}")

    @cli.command()
    def reset():
        """Reset state to idle."""
        from erirpg.state import State

        state = State.load()
        state.reset()
        click.echo("State reset to idle.")
