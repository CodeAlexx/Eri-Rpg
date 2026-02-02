"""
ERI Commands - EriRPG methodology commands.

Commands:
- eri-config: Configure ERI settings (mode, depth, model profile)
- eri-status: Show current ERI state and configuration
- spawn-agent: Spawn an ERI agent
- list-agents: List available agent types
"""

import sys
import json
import click


def register(cli):
    """Register ERI commands with CLI."""

    @cli.command("eri-config")
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
    @click.option("--show", is_flag=True, help="Show current ERI configuration")
    def eri_config_cmd(project: str, mode: str, depth: str, model_profile: str,
                       parallelization: bool, commit_docs: bool, show: bool):
        """Configure ERI methodology settings.

        Examples:
            eri-rpg eri-config myproject --show
            eri-rpg eri-config myproject --mode yolo
            eri-rpg eri-config myproject --depth comprehensive
            eri-rpg eri-config myproject --model-profile quality
        """
        from erirpg.config import (
            load_config, set_eri_mode, set_eri_depth, set_model_profile,
            set_parallelization, set_commit_docs, format_eri_summary
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
            click.echo(format_eri_summary(config.eri))
            return

        # Apply changes
        if mode is not None:
            set_eri_mode(proj.path, mode)
            click.echo(f"ERI mode: {mode}")

        if depth is not None:
            set_eri_depth(proj.path, depth)
            click.echo(f"ERI depth: {depth}")

        if model_profile is not None:
            set_model_profile(proj.path, model_profile)
            click.echo(f"Model profile: {model_profile}")

        if parallelization is not None:
            set_parallelization(proj.path, parallelization)
            click.echo(f"Parallelization: {'enabled' if parallelization else 'disabled'}")

        if commit_docs is not None:
            set_commit_docs(proj.path, commit_docs)
            click.echo(f"Commit docs: {'enabled' if commit_docs else 'disabled'}")

    @cli.command("eri-status")
    @click.argument("project")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def eri_status_cmd(project: str, output_json: bool):
        """Show current ERI state and configuration.

        Displays:
        - ERI configuration
        - Current phase (if any)
        - Active plans
        - Pending checkpoints

        Examples:
            eri-rpg eri-status myproject
            eri-rpg eri-status myproject --json
        """
        from erirpg.config import load_config, format_eri_summary, format_model_profile_summary
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
                "eri": config.eri.to_dict(),
                "state": state.to_dict() if state else None,
                "roadmap": roadmap.to_dict() if roadmap else None,
                "checkpoints": [cp.to_dict() for cp in checkpoints],
            }
            click.echo(json.dumps(output, indent=2))
            return

        # Text output
        click.echo(format_eri_summary(config.eri))
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
        """Spawn an ERI agent for execution.

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
        """List available ERI agent types.

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
        click.echo(format_model_profile_summary(config.eri.model_profile))

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

        # Parse plan_id format: "phase-N" (e.g., "foundation-1")
        try:
            parts = plan_id.rsplit("-", 1)
            if len(parts) != 2:
                raise ValueError("Invalid format")
            phase_name = parts[0]
            plan_number = int(parts[1])
        except (ValueError, IndexError):
            click.echo(f"Error: Invalid plan_id format '{plan_id}'. Expected 'phase-N' (e.g., 'foundation-1')", err=True)
            sys.exit(1)

        plan = load_plan(proj.path, phase_name, plan_number)
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

    @cli.command("eri-plan")
    @click.argument("project")
    @click.option("--show", is_flag=True, help="Show full plan with execution instructions")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def eri_plan_cmd(project: str, show: bool, output_json: bool):
        """Show ERI plan for a project.

        Displays the ERI plan with tasks, must-haves, and execution instructions.

        Examples:
            eri-rpg eri-plan myproject --show
            eri-rpg eri-plan myproject --json
        """
        from erirpg.eri_planner import load_eri_plan, format_plan_for_execution
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        plan = load_eri_plan(proj.path)
        if not plan:
            click.echo(f"Error: No ERI plan found for '{project}'", err=True)
            click.echo("Create one with: eri-rpg new <project> <description>")
            sys.exit(1)

        if output_json:
            click.echo(json.dumps(plan.to_dict(), indent=2))
            return

        if show:
            click.echo(format_plan_for_execution(plan))
        else:
            click.echo(f"Plan: {plan.id}")
            click.echo(f"Phase: {plan.phase}")
            click.echo(f"Objective: {plan.objective}")
            click.echo(f"Tasks: {len(plan.tasks)}")
            click.echo(f"Must-haves:")
            click.echo(f"  Truths: {len(plan.must_haves.truths)}")
            click.echo(f"  Artifacts: {len(plan.must_haves.artifacts)}")
            click.echo(f"  Key Links: {len(plan.must_haves.key_links)}")
            click.echo("")
            click.echo("Use --show for full execution instructions")

    @cli.command("eri-execute")
    @click.argument("project")
    @click.option("--task", type=int, default=None, help="Execute specific task number")
    @click.option("--dry-run", is_flag=True, help="Show what would be executed")
    def eri_execute_cmd(project: str, task: int, dry_run: bool):
        """Execute ERI plan for a project.

        Shows execution instructions for Claude to follow.
        This outputs the plan in a format that Claude can execute.

        Examples:
            eri-rpg eri-execute myproject
            eri-rpg eri-execute myproject --task 1
            eri-rpg eri-execute myproject --dry-run
        """
        from erirpg.eri_planner import load_eri_plan, format_plan_for_execution
        from erirpg.registry import Registry

        registry = Registry.get_instance()
        proj = registry.get(project)
        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        plan = load_eri_plan(proj.path)
        if not plan:
            click.echo(f"Error: No ERI plan found for '{project}'", err=True)
            sys.exit(1)

        if dry_run:
            click.echo("DRY RUN - Would execute:")
            click.echo(f"  Plan: {plan.id}")
            click.echo(f"  Tasks: {len(plan.tasks)}")
            for i, t in enumerate(plan.tasks, 1):
                click.echo(f"    {i}. {t.get('name', 'task')}: {t.get('action', '')[:50]}...")
            return

        if task is not None:
            # Execute specific task
            if task < 1 or task > len(plan.tasks):
                click.echo(f"Error: Task {task} not found. Plan has {len(plan.tasks)} tasks.")
                sys.exit(1)

            t = plan.tasks[task - 1]
            click.echo("=" * 60)
            click.echo(f"EXECUTE TASK {task}: {t.get('name', 'task')}")
            click.echo("=" * 60)
            click.echo("")
            click.echo(f"Action: {t.get('action', '')}")
            click.echo(f"Files: {', '.join(t.get('files', []))}")
            click.echo(f"Done when: {t.get('done', '')}")
            click.echo("")
            if t.get('details'):
                click.echo("Details:")
                click.echo(t['details'])
            click.echo("")
            click.echo(f"Verify: {t.get('verify', '')}")
        else:
            # Show full plan for execution
            click.echo(format_plan_for_execution(plan))
