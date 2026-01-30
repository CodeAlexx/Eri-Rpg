"""
GSD Commands - Get Shit Done methodology commands.

Commands:
- gsd-config: Configure GSD settings (mode, depth, model profile)
- gsd-status: Show current GSD state and configuration
- spawn-agent: Spawn a GSD agent
- list-agents: List available agent types
"""

import sys
import json
import click


def register(cli):
    """Register GSD commands with CLI."""

    @cli.command("gsd-config")
    @click.argument("project")
    @click.option("--mode", type=click.Choice(["yolo", "interactive"]), default=None,
                  help="Execution mode: yolo (auto-proceed) or interactive (confirm)")
    @click.option("--depth", type=click.Choice(["quick", "standard", "comprehensive"]), default=None,
                  help="Verification depth")
    @click.option("--model-profile", type=click.Choice(["quality", "balanced", "budget"]), default=None,
                  help="Model profile for agent selection")
    @click.option("--parallelization/--no-parallelization", default=None,
                  help="Enable/disable parallel plan execution")
    @click.option("--commit-docs/--no-commit-docs", default=None,
                  help="Enable/disable doc commits")
    @click.option("--show", is_flag=True, help="Show current GSD configuration")
    def gsd_config_cmd(project: str, mode: str, depth: str, model_profile: str,
                       parallelization: bool, commit_docs: bool, show: bool):
        """Configure GSD methodology settings.

        Examples:
            eri-rpg gsd-config myproject --show
            eri-rpg gsd-config myproject --mode yolo
            eri-rpg gsd-config myproject --depth comprehensive
            eri-rpg gsd-config myproject --model-profile quality
        """
        from erirpg.config import (
            load_config, set_gsd_mode, set_gsd_depth, set_model_profile,
            set_parallelization, set_commit_docs, format_gsd_summary
        )
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        config = load_config(proj.path)

        # Show if requested or no other action
        no_changes = all(x is None for x in [mode, depth, model_profile, parallelization, commit_docs])
        if show or no_changes:
            click.echo(format_gsd_summary(config.gsd))
            return

        # Apply changes
        if mode is not None:
            set_gsd_mode(proj.path, mode)
            click.echo(f"GSD mode: {mode}")

        if depth is not None:
            set_gsd_depth(proj.path, depth)
            click.echo(f"GSD depth: {depth}")

        if model_profile is not None:
            set_model_profile(proj.path, model_profile)
            click.echo(f"Model profile: {model_profile}")

        if parallelization is not None:
            set_parallelization(proj.path, parallelization)
            click.echo(f"Parallelization: {'enabled' if parallelization else 'disabled'}")

        if commit_docs is not None:
            set_commit_docs(proj.path, commit_docs)
            click.echo(f"Commit docs: {'enabled' if commit_docs else 'disabled'}")

    @cli.command("gsd-status")
    @click.argument("project")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def gsd_status_cmd(project: str, output_json: bool):
        """Show current GSD state and configuration.

        Displays:
        - GSD configuration
        - Current phase (if any)
        - Active plans
        - Pending checkpoints

        Examples:
            eri-rpg gsd-status myproject
            eri-rpg gsd-status myproject --json
        """
        from erirpg.config import load_config, format_gsd_summary, format_model_profile_summary
        from erirpg.models.state import load_state
        from erirpg.models.roadmap import load_roadmap
        from erirpg.execution.checkpoint_handler import list_pending_checkpoints, format_checkpoint_summary
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        config = load_config(proj.path)
        state = load_state(proj.path)
        roadmap = load_roadmap(proj.path)
        checkpoints = list_pending_checkpoints(proj.path)

        if output_json:
            output = {
                "gsd": config.gsd.to_dict(),
                "state": state.to_dict() if state else None,
                "roadmap": roadmap.to_dict() if roadmap else None,
                "checkpoints": [cp.to_dict() for cp in checkpoints],
            }
            click.echo(json.dumps(output, indent=2))
            return

        # Text output
        click.echo(format_gsd_summary(config.gsd))
        click.echo("")

        if state:
            click.echo(f"Current Phase: {state.position.phase or 'None'}")
            click.echo(f"Current Plan: {state.position.plan_id or 'None'}")
            click.echo(f"Status: {state.position.status}")
        else:
            click.echo("State: Not initialized")

        click.echo("")

        if roadmap:
            click.echo(f"Roadmap: {len(roadmap.phases)} phases")
            for phase in roadmap.phases:
                status = "✓" if phase.completed_at else "○"
                click.echo(f"  {status} {phase.id}: {phase.name}")
        else:
            click.echo("Roadmap: Not created")

        click.echo("")

        if checkpoints:
            click.echo(format_checkpoint_summary(checkpoints))
        else:
            click.echo("Checkpoints: None pending")

    @cli.command("spawn-agent")
    @click.argument("project")
    @click.argument("agent_type")
    @click.option("--context", "-c", default="", help="Context to pass to agent")
    @click.option("--show-prompt", is_flag=True, help="Show the agent prompt instead of spawning")
    def spawn_agent_cmd(project: str, agent_type: str, context: str, show_prompt: bool):
        """Spawn a GSD agent for execution.

        This prepares the Task tool call parameters for spawning an agent.
        The actual spawning happens in the Claude Code context.

        Agent types:
            planner, executor, verifier, plan-checker,
            project-researcher, phase-researcher, research-synthesizer,
            roadmapper, debugger, codebase-mapper, integration-checker

        Examples:
            eri-rpg spawn-agent myproject planner --context "Phase: foundation"
            eri-rpg spawn-agent myproject executor --show-prompt
        """
        from erirpg.agents import spawn_agent, get_agent_prompt, AGENT_TYPES
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        if agent_type not in AGENT_TYPES:
            click.echo(f"Error: Unknown agent type '{agent_type}'", err=True)
            click.echo(f"Valid types: {', '.join(AGENT_TYPES)}")
            sys.exit(1)

        if show_prompt:
            prompt = get_agent_prompt(agent_type, context)
            click.echo(prompt)
            return

        # Generate spawn parameters
        params = spawn_agent(proj.path, agent_type, context=context)
        click.echo(json.dumps(params, indent=2))

    @cli.command("list-agents")
    @click.option("--check", is_flag=True, help="Check if all agent prompts exist")
    def list_agents_cmd(check: bool):
        """List available GSD agent types.

        Examples:
            eri-rpg list-agents
            eri-rpg list-agents --check
        """
        from erirpg.agents.prompts import format_agent_list, validate_all_prompts

        if check:
            status = validate_all_prompts()
            all_ok = all(status.values())
            for agent_type, exists in status.items():
                icon = "✓" if exists else "✗"
                click.echo(f"{icon} {agent_type}")
            if not all_ok:
                click.echo("\nSome prompts are missing. Run 'eri-rpg init' to create them.")
                sys.exit(1)
        else:
            click.echo(format_agent_list())

    @cli.command("model-profile")
    @click.argument("project")
    @click.option("--show", is_flag=True, help="Show model assignments for current profile")
    def model_profile_cmd(project: str, show: bool):
        """Show or manage model profile assignments.

        Displays which model (opus/sonnet/haiku) is used for each agent type
        based on the current profile.

        Examples:
            eri-rpg model-profile myproject --show
        """
        from erirpg.config import load_config, format_model_profile_summary
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        config = load_config(proj.path)
        click.echo(format_model_profile_summary(config.gsd.model_profile))

    @cli.command("verify-plan")
    @click.argument("project")
    @click.argument("plan_id")
    @click.option("--level", type=click.Choice(["1", "2", "3"]), default="2",
                  help="Verification level: 1=existence, 2=substantive, 3=wired")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def verify_plan_cmd(project: str, plan_id: str, level: str, output_json: bool):
        """Verify a plan's must-haves.

        Verification levels:
            1 - Existence: Check files exist
            2 - Substantive: Check files aren't stubs
            3 - Wired: Check connections exist

        Examples:
            eri-rpg verify-plan myproject foundation-1
            eri-rpg verify-plan myproject foundation-1 --level 3
        """
        from erirpg.models.plan import load_plan
        from erirpg.verification.levels import verify_plan_must_haves
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        plan = load_plan(proj.path, plan_id)
        if not plan:
            click.echo(f"Error: Plan '{plan_id}' not found", err=True)
            sys.exit(1)

        report = verify_plan_must_haves(proj.path, plan, int(level))

        if output_json:
            click.echo(json.dumps(report.to_dict(), indent=2))
            return

        # Text output
        click.echo(f"Verification Report: {plan_id}")
        click.echo(f"Level: {level} ({['', 'existence', 'substantive', 'wired'][int(level)]})")
        click.echo(f"Status: {report.status.value}")
        click.echo("")

        if report.gaps:
            click.echo(f"Gaps Found: {len(report.gaps)}")
            for gap in report.gaps:
                click.echo(f"  - [{gap.severity}] {gap.description}")

    @cli.command("checkpoint-list")
    @click.argument("project")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def checkpoint_list_cmd(project: str, output_json: bool):
        """List pending checkpoints.

        Shows checkpoints waiting for human input.

        Examples:
            eri-rpg checkpoint-list myproject
        """
        from erirpg.execution.checkpoint_handler import list_pending_checkpoints, format_checkpoint_summary
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        checkpoints = list_pending_checkpoints(proj.path)

        if output_json:
            click.echo(json.dumps([cp.to_dict() for cp in checkpoints], indent=2))
            return

        click.echo(format_checkpoint_summary(checkpoints))

    @cli.command("checkpoint-resolve")
    @click.argument("project")
    @click.argument("checkpoint_id")
    @click.argument("response")
    def checkpoint_resolve_cmd(project: str, checkpoint_id: str, response: str):
        """Resolve a pending checkpoint.

        Provides a response to a checkpoint that's waiting for human input.

        Examples:
            eri-rpg checkpoint-resolve myproject cp-123 "Use PostgreSQL"
        """
        from erirpg.execution.checkpoint_handler import continue_from_checkpoint
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        context = continue_from_checkpoint(proj.path, checkpoint_id, response)
        if not context:
            click.echo(f"Error: Checkpoint '{checkpoint_id}' not found", err=True)
            sys.exit(1)

        click.echo("Checkpoint resolved. Continuation context:")
        click.echo(context)
