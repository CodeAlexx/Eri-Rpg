"""
Mode Commands - Core workflow commands for EriRPG.

Commands (lite tier):
- take: Transplant a feature from one project to another
- work: Modify an existing project
- done: Mark current work as complete
- next: Advance to next chunk in new project

Commands (full tier):
- research: Run research phase for a goal
- execute: Execute a plan in waves
- new: Create a new project from scratch
"""

import json
import os
import sys
import click

from erirpg.cli_commands.guards import tier_required


def _get_session_id(project_path: str) -> str:
    """Get session ID from state file."""
    from pathlib import Path

    state_file = Path(project_path) / ".eri-rpg" / "state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
                return state.get("session_id")
        except Exception:
            pass
    return None


def _get_project_name(project_path: str) -> str:
    """Get project name from config."""
    from pathlib import Path

    config_file = Path(project_path) / ".eri-rpg" / "config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get("project_name", os.path.basename(project_path))
        except Exception:
            pass
    return os.path.basename(project_path)


def _archive_session(project_path: str, summary: str):
    """Archive session decisions and regenerate STATUS.md."""
    from pathlib import Path

    try:
        from erirpg import storage
        from erirpg.generators.status_md import regenerate_status

        session_id = _get_session_id(project_path)
        project_name = _get_project_name(project_path)

        if session_id:
            # End the session with summary
            storage.end_session(session_id, summary=summary)

            # Archive decisions for this session
            archived_count = storage.archive_session_decisions(session_id)
            if archived_count > 0:
                click.echo(f"  Archived {archived_count} decision(s)")

        # Regenerate STATUS.md
        status_path = regenerate_status(project_name, project_path)
        click.echo(f"  Updated: {status_path}")

        # Clear session ID from state
        state_file = Path(project_path) / ".eri-rpg" / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                state.pop("session_id", None)
                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2)
            except Exception:
                pass

    except ImportError:
        # Storage module not available, skip
        pass
    except Exception as e:
        click.echo(f"  Warning: Could not archive session: {e}", err=True)


def register(cli):
    """Register mode commands with CLI."""
    from erirpg.registry import Registry
    from erirpg.state import State

    # Lite tier commands
    @cli.command()
    @click.argument("description")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    def take(description: str, verbose: bool):
        """Transplant a feature from one project to another.

        One command does it all: find → learn → spec → context → guide.

        \b
        Examples:
            eri-rpg take "masked_loss from onetrainer into eritrainer"
            eri-rpg take "gradient checkpointing from onetrainer"

        The second form uses current directory as target.
        """
        from erirpg.modes import run_take

        result = run_take(description, verbose=verbose)

        if not result['success']:
            click.echo(f"Error: {result['error']}", err=True)
            sys.exit(1)

        # Show guide
        click.echo(result['guide'])

        # Show knowledge hints if some modules need learning
        knowledge = result.get('knowledge_status', {})
        need_learning = knowledge.get('need_to_learn', [])

        if need_learning and len(need_learning) <= 3:
            click.echo("Tip: After understanding these modules, store learnings:")
            for path in need_learning:
                click.echo(f"  eri-rpg learn {result['source']} {path}")
            click.echo("")

    @cli.command()
    @click.argument("project", required=False)
    @click.argument("task")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    def work(project: str, task: str, verbose: bool):
        """Modify an existing project.

        Find relevant code, load knowledge, generate context, guide.

        \b
        Examples:
            eri-rpg work eritrainer "add dark mode to settings"
            eri-rpg work "fix the memory leak in dataloader"

        The second form uses current directory as project.
        """
        from erirpg.modes import run_work

        result = run_work(project, task, verbose=verbose)

        if not result['success']:
            click.echo(f"Error: {result['error']}", err=True)
            sys.exit(1)

        # Show guide
        click.echo(result['guide'])

        # Show knowledge hints
        knowledge = result.get('knowledge', {})
        unknown = knowledge.get('unknown', [])

        if unknown and len(unknown) <= 3:
            click.echo("Tip: After understanding these modules, store learnings:")
            for path in unknown:
                click.echo(f"  eri-rpg learn {result['project']} {path}")
            click.echo("")

    @cli.command()
    @click.option("--summary", "-s", default=None, help="Summary of what was accomplished")
    def done(summary: str):
        """Mark current work as complete.

        Updates state, archives session decisions, and regenerates STATUS.md.
        """
        state = State.load()

        if state.phase == "idle":
            click.echo("Nothing in progress.")
            return

        task = state.current_task or "Unknown task"
        state.log("done", f"Completed: {task}")

        # Archive session and regenerate STATUS.md
        project_path = os.getcwd()
        _archive_session(project_path, summary or task)

        state.reset()

        click.echo(f"✓ Marked complete: {task}")
        click.echo("")
        click.echo("If you learned something new, store it:")
        click.echo("  eri-rpg learn <project> <module>")

    # Full tier commands
    @cli.command()
    @click.argument("name")
    @click.option("--goal", default=None, help="Goal to research (loads from state if not provided)")
    @click.option("--level", type=int, default=None, help="Force discovery level (0-3)")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    @tier_required("full")
    def research(name: str, goal: str, level: int, verbose: bool):
        """Run research phase for a goal.

        Analyzes external libraries, pitfalls, and best practices.
        Generates RESEARCH.md with findings.

        \b
        Examples:
            eri-rpg research myproj --goal "add oauth login"
            eri-rpg research myproj --level 2
        """
        from erirpg.research import ResearchPhase
        from erirpg.discovery import detect_discovery_level

        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        # Get goal from state if not provided
        if not goal:
            state = State.load()
            goal = state.current_task
            if not goal:
                click.echo("Error: No goal specified and no active task", err=True)
                click.echo("Use: eri-rpg research myproj --goal \"your goal\"")
                sys.exit(1)

        # Detect discovery level if not forced
        if level is None:
            level, reason = detect_discovery_level(goal)
            if verbose:
                click.echo(f"Discovery level: {level} ({reason})")
        else:
            reason = "forced"

        if level == 0:
            click.echo("Discovery level 0 - no research needed")
            return

        # Run research phase
        if verbose:
            click.echo(f"Running research for: {goal}")
            click.echo(f"Level: {level}")

        phase = ResearchPhase(project.path, goal, level)
        findings = phase.execute()

        if findings:
            # Save to project
            output_dir = os.path.join(project.path, ".eri-rpg", "research")
            os.makedirs(output_dir, exist_ok=True)

            md_path = os.path.join(output_dir, "RESEARCH.md")
            with open(md_path, "w") as f:
                f.write(findings.to_markdown())

            json_path = os.path.join(output_dir, "research.json")
            with open(json_path, "w") as f:
                json.dump(findings.to_dict(), f, indent=2)

            click.echo(f"Research saved to: {md_path}")
            click.echo(f"  Confidence: {findings.confidence}")
            click.echo(f"  Stack: {len(findings.stack)} choices")
            click.echo(f"  Pitfalls: {len(findings.pitfalls)}")
            click.echo(f"  Anti-patterns: {len(findings.anti_patterns)}")
        else:
            click.echo("No research findings generated")

    @cli.command()
    @click.argument("name")
    @click.option("--plan-id", default=None, help="Plan ID to execute (loads latest if not provided)")
    @click.option("--wave", type=int, default=None, help="Start from specific wave")
    @click.option("--no-resume", is_flag=True, help="Don't resume from checkpoint")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    @tier_required("full")
    def execute(name: str, plan_id: str, wave: int, no_resume: bool, verbose: bool):
        """Execute a plan in waves.

        Runs plan steps with parallel support and checkpointing.
        Resumes from checkpoint if interrupted.

        \b
        Examples:
            eri-rpg execute myproj
            eri-rpg execute myproj --plan-id abc123
            eri-rpg execute myproj --no-resume
        """
        import asyncio
        from erirpg.planner import Plan
        from erirpg.executor import WaveExecutor

        registry = Registry.get_instance()
        project = registry.get(name)

        if not project:
            click.echo(f"Error: Project '{name}' not found", err=True)
            sys.exit(1)

        # Find plan
        plans_dir = os.path.join(project.path, ".eri-rpg", "plans")
        if not os.path.exists(plans_dir):
            click.echo(f"Error: No plans found for {name}", err=True)
            click.echo("Create a plan first with: eri-rpg work <project> \"goal\"")
            sys.exit(1)

        if plan_id:
            plan_file = os.path.join(plans_dir, f"{plan_id}.json")
            if not os.path.exists(plan_file):
                click.echo(f"Error: Plan {plan_id} not found", err=True)
                sys.exit(1)
        else:
            # Find most recent plan
            plans = sorted(
                [f for f in os.listdir(plans_dir) if f.endswith(".json")],
                key=lambda x: os.path.getmtime(os.path.join(plans_dir, x)),
                reverse=True
            )
            if not plans:
                click.echo(f"Error: No plans found for {name}", err=True)
                sys.exit(1)
            plan_file = os.path.join(plans_dir, plans[0])
            if verbose:
                click.echo(f"Using latest plan: {plans[0]}")

        # Load plan
        plan = Plan.load(plan_file)
        click.echo(f"Plan: {plan.goal}")
        click.echo(f"Steps: {len(plan.steps)}")

        # Show wave structure
        waves = plan.waves
        click.echo(f"Waves: {len(waves)}")
        for w_num, steps in sorted(waves.items()):
            step_ids = [s.id for s in steps]
            parallel = "parallel" if all(s.parallelizable for s in steps) else "sequential"
            click.echo(f"  Wave {w_num}: {step_ids} ({parallel})")

        # Execute
        executor = WaveExecutor(plan, project.path)
        resume = not no_resume

        if wave is not None and resume:
            # Modify checkpoint to start from specific wave
            checkpoint = executor.load_checkpoint()
            if checkpoint:
                checkpoint.current_wave = wave
                executor.save_checkpoint(wave - 1, checkpoint)

        click.echo("")
        click.echo("Starting execution...")

        result = asyncio.run(executor.execute(resume=resume))

        click.echo("")
        if result.success:
            click.echo("=" * 40)
            click.echo("Execution complete!")
            click.echo(f"Waves: {len(result.wave_results)}")
            for wr in result.wave_results:
                status = "✓" if wr.success else "✗"
                click.echo(f"  Wave {wr.wave_num}: {status}")
        else:
            click.echo("=" * 40)
            click.echo(f"Execution failed: {result.message}")
            sys.exit(1)

    @cli.command("new")
    @click.argument("description")
    @click.option("-o", "--output", default=None, help="Where to create project")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    @tier_required("full")
    def new_project(description: str, output: str, verbose: bool):
        """Create a new project from scratch.

        Asks questions, generates spec, creates structure, guides you.

        \b
        Example:
            eri-rpg new "video editor with timeline and effects"
        """
        from erirpg.modes import run_new
        from erirpg.questions import QUESTIONS

        # Interactive question flow
        click.echo("")
        click.echo(f"Creating: {description}")
        click.echo("")
        click.echo("I need a few details:")
        click.echo("")

        answers = {}

        for q in QUESTIONS:
            if q.options:
                # Multiple choice
                click.echo(f"{q.question}")
                click.echo(f"  ({q.why})")
                for i, opt in enumerate(q.options, 1):
                    default_marker = " [default]" if opt == q.default else ""
                    click.echo(f"  {i}. {opt}{default_marker}")

                while True:
                    choice = click.prompt("Choice", default=str(q.options.index(q.default) + 1) if q.default else "1")
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(q.options):
                            answers[q.id] = q.options[idx]
                            break
                    except ValueError:
                        # Maybe they typed the option name
                        if choice in q.options:
                            answers[q.id] = choice
                            break
                    click.echo("Invalid choice, try again")
            else:
                # Free text
                click.echo(f"{q.question}")
                click.echo(f"  ({q.why})")

                if q.required:
                    value = click.prompt(">")
                else:
                    value = click.prompt(">", default=q.default or "")

                answers[q.id] = value

            click.echo("")

        # Run new mode with answers
        result = run_new(description, output_dir=output, answers=answers, verbose=verbose)

        if not result['success']:
            if result.get('need_input'):
                click.echo("Error: Questions not answered", err=True)
            else:
                click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)

        # Show guide
        click.echo(result['guide'])

    @cli.command("next")
    @click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
    def next_chunk(verbose: bool):
        """Advance to next chunk in new project.

        Use after completing a chunk to get context for the next one.
        """
        from erirpg.modes import run_next

        result = run_next(verbose=verbose)

        if not result['success']:
            click.echo(f"Error: {result['error']}", err=True)
            sys.exit(1)

        if result.get('done'):
            click.echo("")
            click.echo("═" * 56)
            click.echo(f"🎉 PROJECT COMPLETE: {result['message']}")
            click.echo("═" * 56)
            click.echo("")
            click.echo("Next steps:")
            click.echo("  - Index the project: eri-rpg index <name>")
            click.echo("  - Store learnings: eri-rpg learn <name> <module>")
            click.echo("")
        else:
            click.echo(result['guide'])
            click.echo(f"Remaining chunks: {result['remaining']}")
            click.echo("")
