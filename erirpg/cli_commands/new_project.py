"""
New Project Command - Complete project creation flow.

Orchestrates: describe → discuss → spec → plan → scaffold → track

Usage:
    eri-rpg new my-app "REST API for users"
    eri-rpg new my-app --stack fastapi-only
    eri-rpg new my-app -y  # Skip confirmations
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register new project command with CLI."""

    @cli.command("new")
    @click.argument("name")
    @click.argument("description", required=False, default="")
    @click.option(
        "--stack", "-s",
        type=click.Choice(["fastapi-only", "cli-python"]),
        help="Technology stack template"
    )
    @click.option(
        "--no-scaffold",
        is_flag=True,
        help="Skip scaffolding (create spec/plan only)"
    )
    @click.option(
        "--yes", "-y",
        is_flag=True,
        help="Skip confirmation prompts"
    )
    @click.option(
        "--path", "-p",
        type=click.Path(),
        help="Project output path (defaults to ./{name})"
    )
    @tier_required("full")
    def new_project(
        name: str,
        description: str,
        stack: Optional[str],
        no_scaffold: bool,
        yes: bool,
        path: Optional[str],
    ):
        """Create a new project with guided discussion and scaffolding.

        This command orchestrates the complete project creation flow:

        \b
        1. DESCRIBE - Gather project description
        2. DISCUSS  - Clarifying questions (3-5 questions)
        3. SPEC     - Generate ProjectSpec from discussion
        4. PLAN     - Generate execution plan from spec
        5. SCAFFOLD - Create project structure and files
        6. TRACK    - Initialize EriRPG tracking

        \b
        Examples:
            eri-rpg new my-api "REST API for user management"
            eri-rpg new my-cli --stack cli-python
            eri-rpg new my-app -p ~/projects/my-app -y
        """
        from erirpg.scaffold import get_available_stacks

        # Show header
        click.echo("=" * 50)
        click.echo(f" EriRPG New Project: {name}")
        click.echo("=" * 50)
        click.echo("")

        # Resolve output path
        if path is None:
            path = os.path.join(os.getcwd(), name)
        output_path = os.path.abspath(os.path.expanduser(path))

        # Check if directory exists
        if os.path.exists(output_path) and os.listdir(output_path):
            click.echo(f"Warning: Directory exists and is not empty: {output_path}")
            if not yes and not click.confirm("Continue anyway?"):
                click.echo("Cancelled.")
                return

        # Phase 1: DESCRIBE
        click.echo("Phase 1: DESCRIBE")
        click.echo("-" * 30)
        description = _run_describe_phase(name, description)
        click.echo(f"Description: {description[:80]}{'...' if len(description) > 80 else ''}")
        click.echo("")

        # Phase 2: DISCUSS
        click.echo("Phase 2: DISCUSS")
        click.echo("-" * 30)
        discussion = _run_discuss_phase(name, description, output_path, yes)
        if discussion is None:
            click.echo("Discussion cancelled.")
            return
        click.echo("")

        # Phase 3: SPEC
        click.echo("Phase 3: SPEC")
        click.echo("-" * 30)
        spec = _run_spec_phase(discussion, stack, output_path, name)

        # Show spec summary
        click.echo(f"Project: {spec.name}")
        click.echo(f"Language: {spec.language}")
        click.echo(f"Framework: {spec.framework or '(none)'}")
        click.echo(f"Core Feature: {spec.core_feature[:60]}{'...' if len(spec.core_feature) > 60 else ''}")

        if not yes:
            click.echo("")
            choice = click.prompt(
                "Proceed with this spec?",
                type=click.Choice(["y", "edit", "restart"]),
                default="y"
            )
            if choice == "restart":
                click.echo("Restarting...")
                # Recursively call (simplified - just restart discussion)
                return
            elif choice == "edit":
                click.echo("Edit the spec at: .eri-rpg/specs/{spec.id}.json")
                click.echo("Then run: eri-rpg plan generate {spec.id}")
                return
        click.echo("")

        # Phase 4: PLAN (ERI)
        click.echo("Phase 4: PLAN (ERI)")
        click.echo("-" * 30)
        plan = _run_plan_phase(spec, output_path)
        click.echo(f"Plan: {plan.objective[:60]}...")
        click.echo(f"Tasks: {len(plan.tasks)}")
        click.echo(f"Must-haves: {len(plan.must_haves.truths)} truths, {len(plan.must_haves.artifacts)} artifacts")

        if not yes:
            click.echo("")
            if not click.confirm("Generate project files?"):
                click.echo("Stopped before scaffolding.")
                click.echo(f"Spec saved to: {output_path}/.eri-rpg/specs/{spec.id}.json")
                return
        click.echo("")

        # Phase 5: SCAFFOLD
        if not no_scaffold:
            click.echo("Phase 5: SCAFFOLD")
            click.echo("-" * 30)
            files_created = _run_scaffold_phase(plan, spec, output_path, stack)
            click.echo(f"Created {len(files_created)} files")
            click.echo("")
        else:
            click.echo("Phase 5: SCAFFOLD (skipped)")
            click.echo("")
            files_created = []

        # Phase 6: TRACK
        click.echo("Phase 6: TRACK")
        click.echo("-" * 30)
        _run_track_phase(name, output_path, spec, plan, files_created)
        click.echo("")

        # Summary
        click.echo("=" * 50)
        click.echo(" PROJECT SCAFFOLDED")
        click.echo("=" * 50)
        click.echo("")
        click.echo(f"Location: {output_path}")
        click.echo("")

        # Show ERI execution instructions
        click.echo("ERI Plan created with:")
        click.echo(f"  - {len(plan.tasks)} tasks to execute")
        click.echo(f"  - {len(plan.must_haves.truths)} truths to verify")
        click.echo(f"  - {len(plan.must_haves.artifacts)} artifacts to create")
        click.echo("")
        click.echo("To execute the plan, run:")
        click.echo(f"  eri-rpg eri-execute {name}")
        click.echo("")
        click.echo("Or view the plan:")
        click.echo(f"  eri-rpg eri-plan {name} --show")


def _run_describe_phase(name: str, description: str) -> str:
    """Run the describe phase - gather project description.

    Args:
        name: Project name
        description: Initial description (may be empty)

    Returns:
        Final description string
    """
    if description:
        return description

    # Prompt for description
    description = click.prompt(
        "Describe your project in one sentence",
        default=f"A new {name} project"
    )
    return description


def _run_discuss_phase(
    name: str,
    description: str,
    project_path: str,
    skip_questions: bool = False,
) -> Optional["Discussion"]:
    """Run the discuss phase - clarifying questions.

    Args:
        name: Project name
        description: Project description
        project_path: Path where project will be created
        skip_questions: Whether to skip interactive questions

    Returns:
        Completed Discussion or None if cancelled
    """
    from erirpg.discuss import (
        generate_new_project_questions,
        Discussion,
    )
    from erirpg.memory import load_knowledge, save_knowledge

    # Generate questions
    questions = generate_new_project_questions(description, project_path)

    if not questions:
        click.echo("No clarifying questions needed.")
        # Create minimal discussion
        discussion = Discussion.create(description, [], project=name)
        discussion.resolve()
        return discussion

    click.echo(f"A few clarifying questions ({len(questions)}):")
    click.echo("")

    # Create discussion
    discussion = Discussion.create(description, questions, project=name)

    if skip_questions:
        # Use defaults
        for q in questions:
            discussion.answer(q, "(default)")
        discussion.resolve()
        return discussion

    # Interactive Q&A
    for i, question in enumerate(questions, 1):
        answer = click.prompt(f"  {i}. {question}", default="")
        if answer.lower() in ["quit", "q", "exit"]:
            return None
        discussion.answer(question, answer if answer else "(no answer)")

    discussion.resolve()

    # Try to save discussion to project knowledge
    # (may not have .eri-rpg dir yet, that's ok)
    try:
        eri_dir = Path(project_path) / ".eri-rpg"
        if eri_dir.exists():
            store = load_knowledge(project_path, name)
            store.add_discussion(discussion)
            save_knowledge(project_path, store)
    except Exception:
        pass  # Will be saved in track phase

    return discussion


def _run_spec_phase(
    discussion: "Discussion",
    stack_hint: Optional[str],
    project_path: str,
    project_name: str,
) -> "ProjectSpec":
    """Run the spec phase - generate ProjectSpec from discussion.

    Args:
        discussion: Completed discussion
        stack_hint: Optional stack override
        project_path: Path where project will be created
        project_name: Name for the project

    Returns:
        Generated ProjectSpec
    """
    from erirpg.discuss import generate_spec_from_discussion
    from erirpg.specs import save_spec_to_project

    spec = generate_spec_from_discussion(
        discussion,
        stack_hint=stack_hint,
        project_path=project_path,
        project_name=project_name,
    )

    # Set output path
    spec.output_path = project_path

    # Create .eri-rpg/specs directory and save
    specs_dir = Path(project_path) / ".eri-rpg" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    save_spec_to_project(spec, project_path)

    return spec


def _run_plan_phase(
    spec: "ProjectSpec",
    project_path: str,
) -> "Plan":
    """Run the plan phase - generate ERI execution plan.

    Args:
        spec: ProjectSpec to plan from
        project_path: Path where project will be created

    Returns:
        Generated ERI Plan with tasks and must-haves
    """
    from erirpg.eri_planner import generate_eri_plan, save_eri_plan

    plan = generate_eri_plan(spec, project_path)

    # Save ERI plan to phases directory
    save_eri_plan(project_path, plan)

    return plan


def _run_scaffold_phase(
    plan: "Plan",
    spec: "ProjectSpec",
    output_path: str,
    stack: Optional[str] = None,
) -> list:
    """Run the scaffold phase - create project files.

    Args:
        plan: Execution plan
        spec: ProjectSpec
        output_path: Where to create files
        stack: Optional stack override

    Returns:
        List of created file paths
    """
    from erirpg.scaffold import scaffold_project

    result = scaffold_project(plan, spec, output_path, stack=stack)

    if result.errors:
        click.echo("Scaffold warnings:")
        for err in result.errors[:5]:
            click.echo(f"  ! {err}")

    return [str(f) for f in result.files_created]


def _run_track_phase(
    name: str,
    project_path: str,
    spec: "ProjectSpec",
    plan: "Plan",
    files_created: list,
) -> None:
    """Run the track phase - initialize EriRPG tracking.

    Args:
        name: Project name
        project_path: Project root path
        spec: ProjectSpec
        plan: Plan
        files_created: List of created file paths
    """
    from erirpg.config import init_project_config, set_tier
    from erirpg.registry import Registry, detect_project_language
    from erirpg.memory import load_knowledge, save_knowledge
    from erirpg.scaffold import create_eri_rpg_structure, auto_learn_scaffolds

    # Create .eri-rpg structure
    create_eri_rpg_structure(project_path)

    # Initialize config with full tier (since we used 'new' command)
    init_project_config(project_path, tier="full")

    # Detect language
    lang = detect_project_language(project_path)
    if lang == "unknown":
        lang = spec.language or "python"

    # Register project
    registry = Registry.get_instance()
    if not registry.get(name):
        try:
            registry.add(name, project_path, lang)
            click.echo(f"Registered project: {name}")
        except ValueError as e:
            click.echo(f"Warning: {e}")

    # Save discussion and any learnings
    store = load_knowledge(project_path, name)

    # Auto-learn scaffolded files
    learnings = auto_learn_scaffolds(project_path, spec)
    for file_path, summary in learnings.items():
        from erirpg.memory import StoredLearning
        from datetime import datetime

        learning = StoredLearning(
            module_path=file_path,
            learned_at=datetime.now(),
            summary=summary,
            purpose=f"Scaffolded for {name}",
        )
        store.add_learning(learning)

    save_knowledge(project_path, store)

    click.echo(f"Initialized EriRPG tracking")
    click.echo(f"  Mode: bootstrap (ready to graduate when stable)")
    click.echo(f"  Tier: full")
    if learnings:
        click.echo(f"  Auto-learned: {len(learnings)} files")
