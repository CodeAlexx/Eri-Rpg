"""
EriRPG CLI - One tool. Three modes. No bloat.

Modes:
- new: Create new project from scratch
- take: Transplant feature from Project A to Project B
- work: Modify existing project

Commands:
- Setup: add, remove, list, index
- Modes: new, take, work
- Exploration: show, find, impact
- Knowledge: learn, recall, relearn, decide, pattern, log, knowledge
- Flow: status, next, validate, done, reset
"""

import click
import json
import os
import sys
import re

from datetime import datetime

from erirpg.registry import Registry, Project, detect_project_language
from erirpg.indexer import index_project, get_or_load_graph
from erirpg.graph import Graph
from erirpg.ops import find_modules, extract_feature, analyze_impact, plan_transplant, Feature, TransplantPlan
from erirpg.context import generate_context, estimate_tokens
from erirpg.state import State
from erirpg.knowledge import Learning, Decision, HistoryEntry
from erirpg.modes import run_take, run_work, run_new, run_next, QUESTIONS
from erirpg.memory import StoredLearning, load_knowledge, save_knowledge
from erirpg.refs import CodeRef


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """EriRPG - Cross-project feature transplant tool.

    Register projects, index codebases, find capabilities,
    extract features, and generate context for Claude Code.
    """
    pass


# ============================================================================
# Setup Commands
# ============================================================================

@cli.command()
@click.argument("name")
@click.argument("path", type=click.Path())
@click.option("--lang", default=None, type=click.Choice(["python", "rust", "c"]),
              help="Programming language (auto-detected if not specified). Supported: python, rust, c.")
def add(name: str, path: str, lang: str):
    """Register a project.

    NAME: Unique project identifier
    PATH: Path to project root
    """
    registry = Registry.get_instance()

    # Auto-detect language if not specified
    if lang is None:
        lang = detect_project_language(path)
        if lang == "unknown":
            click.echo("Warning: Could not detect language, defaulting to 'python'", err=True)
            lang = "python"
        else:
            click.echo(f"Auto-detected language: {lang}")

    try:
        project = registry.add(name, path, lang)
        click.echo(f"Added project: {name}")
        click.echo(f"  Path: {project.path}")
        click.echo(f"  Language: {lang}")
        click.echo(f"\nNext: eri-rpg index {name}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("name")
def remove(name: str):
    """Remove a project from registry."""
    registry = Registry.get_instance()

    if registry.remove(name):
        click.echo(f"Removed project: {name}")
    else:
        click.echo(f"Error: Project '{name}' not found", err=True)
        sys.exit(1)


@cli.command("list")
def list_projects():
    """List registered projects."""
    registry = Registry.get_instance()
    projects = registry.list()

    if not projects:
        click.echo("No projects registered.")
        click.echo("Add one with: eri-rpg add <name> <path>")
        return

    for p in projects:
        status = "indexed" if p.is_indexed() else "not indexed"
        age = ""
        if p.index_age_days() is not None:
            days = p.index_age_days()
            if days < 1:
                age = " (today)"
            else:
                age = f" ({int(days)} days ago)"

        click.echo(f"{p.name}: {p.path} ({p.lang}, {status}{age})")


@cli.command()
@click.argument("name")
@click.option("-v", "--verbose", is_flag=True, help="Show progress")
def index(name: str, verbose: bool):
    """Index a project's codebase.

    Parses all files, extracts interfaces, builds dependency graph.
    """
    registry = Registry.get_instance()
    project = registry.get(name)

    if not project:
        click.echo(f"Error: Project '{name}' not found", err=True)
        click.echo("Add it with: eri-rpg add <name> <path>")
        sys.exit(1)

    click.echo(f"Indexing {name}...")
    try:
        graph = index_project(project, verbose=verbose)
        registry.update_indexed(name)

        stats = graph.stats()
        click.echo(f"\nIndexed:")
        click.echo(f"  Modules: {stats['modules']}")
        click.echo(f"  Dependencies: {stats['edges']}")
        click.echo(f"  Lines: {stats['total_lines']:,}")
        click.echo(f"  Interfaces: {stats['total_interfaces']}")
        click.echo(f"\nSaved to: {project.graph_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Mode Commands (new, take, work)
# ============================================================================

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
def done():
    """Mark current work as complete.

    Updates state and logs completion.
    """
    state = State.load()

    if state.phase == "idle":
        click.echo("Nothing in progress.")
        return

    task = state.current_task or "Unknown task"
    state.log("done", f"Completed: {task}")
    state.reset()

    click.echo(f"✓ Marked complete: {task}")
    click.echo("")
    click.echo("If you learned something new, store it:")
    click.echo("  eri-rpg learn <project> <module>")


@cli.command("new")
@click.argument("description")
@click.option("-o", "--output", default=None, help="Where to create project")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed progress")
def new_project(description: str, output: str, verbose: bool):
    """Create a new project from scratch.

    Asks questions, generates spec, creates structure, guides you.

    \b
    Example:
        eri-rpg new "video editor with timeline and effects"
    """
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


# ============================================================================
# Exploration Commands
# ============================================================================

@cli.command()
@click.argument("project")
def show(project: str):
    """Show project structure from graph."""
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    stats = graph.stats()
    click.echo(f"Project: {project}")
    click.echo(f"Path: {proj.path}")
    click.echo(f"Modules: {stats['modules']}")
    click.echo(f"Lines: {stats['total_lines']:,}")
    click.echo("")

    # Group by top-level directory
    dirs = {}
    for mod_path in sorted(graph.modules.keys()):
        parts = mod_path.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        if top not in dirs:
            dirs[top] = []
        dirs[top].append(mod_path)

    for dir_name, modules in sorted(dirs.items()):
        click.echo(f"{dir_name}/")
        for mod in modules[:5]:  # Show first 5
            m = graph.get_module(mod)
            ifaces = ", ".join(i.name for i in m.interfaces[:3])
            if len(m.interfaces) > 3:
                ifaces += "..."
            click.echo(f"  {mod}: {ifaces}")
        if len(modules) > 5:
            click.echo(f"  ... and {len(modules) - 5} more")


@cli.command()
@click.argument("project")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def find(project: str, query: str, limit: int):
    """Find modules matching a query.

    Searches summaries, interface names, and docstrings.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    results = find_modules(graph, query, limit=limit)

    if not results:
        click.echo(f"No modules match: {query}")
        click.echo("Try broader terms or: eri-rpg show {project}")
        return

    click.echo(f"Matching modules in {project}:")
    click.echo("")
    for mod, score in results:
        summary = mod.summary[:60] + "..." if len(mod.summary) > 60 else mod.summary
        click.echo(f"  {mod.path} ({score:.2f})")
        if summary:
            click.echo(f"    {summary}")


@cli.command()
@click.argument("project")
@click.argument("module_path")
def impact(project: str, module_path: str):
    """Analyze impact of changing a module.

    Shows direct and transitive dependents.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        analysis = analyze_impact(graph, module_path)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Impact analysis for {module_path}:")
    click.echo("")

    if analysis["summary"]:
        click.echo(f"Summary: {analysis['summary']}")

    click.echo(f"Interfaces: {', '.join(analysis['interfaces'])}")
    click.echo("")

    click.echo(f"Direct dependents ({len(analysis['direct_dependents'])}):")
    for d in analysis["direct_dependents"]:
        click.echo(f"  - {d}")

    if analysis["transitive_dependents"]:
        click.echo(f"\nTransitive dependents ({len(analysis['transitive_dependents'])}):")
        for d in analysis["transitive_dependents"][:5]:
            click.echo(f"  - {d}")
        if len(analysis["transitive_dependents"]) > 5:
            click.echo(f"  ... and {len(analysis['transitive_dependents']) - 5} more")

    click.echo(f"\nTotal affected: {analysis['total_affected']}")
    click.echo(f"Risk: {analysis['risk']}")


# ============================================================================
# Transplant Commands
# ============================================================================

@cli.command()
@click.argument("project")
@click.argument("query")
@click.option("-o", "--output", required=True, help="Output file path")
@click.option("-n", "--name", default=None, help="Feature name")
def extract(project: str, query: str, output: str, name: str):
    """Extract a feature from a project.

    Finds matching modules, includes dependencies, saves as JSON.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    feature_name = name or query.replace(" ", "_")

    try:
        feature = extract_feature(graph, proj, query, feature_name)
        feature.save(output)

        click.echo(f"Extracted feature: {feature_name}")
        click.echo(f"Components: {len(feature.components)}")
        for c in feature.components:
            click.echo(f"  - {c}")
        click.echo(f"Provides: {len(feature.provides)} interfaces")
        click.echo(f"Requires: {len(feature.requires)} packages")
        click.echo(f"\nSaved to: {output}")

        # Update state
        state = State.load()
        state.update(
            current_task=f"Transplant {feature_name} from {project}",
            phase="extracting",
            feature_file=output,
        )
        state.log("extract", f"Extracted {feature_name} to {output}")

        click.echo(f"\nNext: eri-rpg plan {output} <target_project>")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feature_file", type=click.Path(exists=True))
@click.argument("target_project")
def plan(feature_file: str, target_project: str):
    """Plan transplant to target project.

    Creates mappings and wiring tasks.
    """
    registry = Registry.get_instance()
    target = registry.get(target_project)

    if not target:
        click.echo(f"Error: Target project '{target_project}' not found", err=True)
        sys.exit(1)

    try:
        target_graph = get_or_load_graph(target)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    feature = Feature.load(feature_file)
    transplant_plan = plan_transplant(feature, target_graph, target)

    # Save plan
    plan_file = feature_file.replace(".json", ".plan.json")
    transplant_plan.save(plan_file)

    click.echo(f"Transplant plan: {feature.name} -> {target_project}")
    click.echo("")

    click.echo("Mappings:")
    for m in transplant_plan.mappings:
        click.echo(f"  {m.source_interface}: {m.action}")
        if m.notes:
            click.echo(f"    {m.notes}")

    if transplant_plan.wiring:
        click.echo("\nWiring tasks:")
        for w in transplant_plan.wiring:
            click.echo(f"  {w.file}: {w.details}")

    click.echo(f"\nSaved to: {plan_file}")

    # Update state
    state = State.load()
    state.update(phase="planning", plan_file=plan_file)
    state.log("plan", f"Created plan at {plan_file}")

    click.echo(f"\nNext: eri-rpg context {feature_file} {target_project}")


@cli.command()
@click.argument("feature_file", type=click.Path(exists=True))
@click.argument("target_project")
@click.option("--no-learnings", is_flag=True, help="Include full source instead of learnings")
def context(feature_file: str, target_project: str, no_learnings: bool):
    """Generate context for Claude Code.

    Creates a markdown file with source code, target interfaces,
    and transplant plan. Uses stored learnings when available
    for ~85% token reduction on revisited modules.
    """
    registry = Registry.get_instance()
    target = registry.get(target_project)

    if not target:
        click.echo(f"Error: Target project '{target_project}' not found", err=True)
        sys.exit(1)

    try:
        target_graph = get_or_load_graph(target)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    feature = Feature.load(feature_file)

    # Load source project's graph for knowledge lookup
    source_proj = registry.get(feature.source_project)
    source_graph = None
    if source_proj:
        try:
            source_graph = get_or_load_graph(source_proj)
        except ValueError:
            pass  # No graph, no learnings - that's fine

    # Load or generate plan
    plan_file = feature_file.replace(".json", ".plan.json")
    if os.path.exists(plan_file):
        transplant_plan = TransplantPlan.load(plan_file)
    else:
        transplant_plan = plan_transplant(feature, target_graph, target)
        transplant_plan.save(plan_file)

    context_path = generate_context(
        feature, transplant_plan, source_graph, target_graph, target,
        source_project=source_proj,
        use_learnings=not no_learnings
    )

    tokens = estimate_tokens(feature, transplant_plan, source_project=source_proj)

    click.echo(f"Generated context: {context_path}")
    click.echo(f"Estimated tokens: ~{tokens:,}")
    click.echo("")
    click.echo("Give this file to Claude Code:")
    click.echo(f"  cat {context_path}")
    click.echo("")
    click.echo("Or reference it directly in conversation.")

    # Update state
    state = State.load()
    state.update(phase="context_ready", context_file=context_path, waiting_on="claude")
    state.log("context", f"Generated context at {context_path}")

    click.echo("\nAfter Claude implements, run: eri-rpg validate")


# ============================================================================
# Orchestration Commands
# ============================================================================

@cli.command("do")
@click.argument("task")
def do_task(task: str):
    """Smart mode - figure out steps for a task.

    Parses task description and suggests/executes steps.
    """
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
        runner = CliRunner()
        result = runner.invoke(find, [project, capability])
        click.echo(result.output)
        return

    # Pattern: "what uses X in Y"
    match = re.search(r"what\s+uses\s+(.+?)\s+in\s+(\w+)", task_lower)
    if match:
        module, project = match.groups()
        click.echo(f"Analyzing impact of {module} in {project}...")
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(impact, [project, module])
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
    state = State.load()
    click.echo(state.format_status())


@cli.command()
def validate():
    """Validate Claude's implementation.

    Checks if transplant was completed correctly.
    """
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

    passed = 0
    failed = 0

    # Check mappings
    for m in transplant_plan.mappings:
        if m.action == "CREATE":
            # Check if file exists (rough check)
            # Would need smarter path resolution
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
    state = State.load()
    state.reset()
    click.echo("State reset to idle.")


# ============================================================================
# Knowledge Commands
# ============================================================================

@cli.command()
@click.argument("project")
@click.argument("module_path")
@click.option("--summary", "-s", prompt=True, help="One-line summary of the module")
@click.option("--purpose", "-p", prompt=True, help="Detailed purpose explanation")
@click.option("--non-interactive", "-y", is_flag=True, help="Skip interactive prompts for key functions and gotchas")
def learn(project: str, module_path: str, summary: str, purpose: str, non_interactive: bool):
    """Store a learning about a module.

    After understanding a module, record key insights so you don't
    have to re-read it later. Saves ~85% tokens on revisits.

    Example:
        eri-rpg learn onetrainer modules/util/loss.py \\
            -s "Loss calculation utilities" \\
            -p "Handles MSE, masked, and prior-based losses"

        # Non-interactive mode (for scripts/automation):
        eri-rpg learn onetrainer modules/util/loss.py -y \\
            -s "Loss calculation utilities" \\
            -p "Handles MSE, masked, and prior-based losses"
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    key_functions = {}
    gotchas = []

    if not non_interactive:
        # Prompt for optional details
        click.echo("\nOptional: Enter key functions (name: description), empty line to finish:")
        while True:
            line = click.prompt("", default="", show_default=False)
            if not line:
                break
            if ":" in line:
                name, desc = line.split(":", 1)
                key_functions[name.strip()] = desc.strip()

        click.echo("\nOptional: Enter gotchas (one per line), empty line to finish:")
        while True:
            line = click.prompt("", default="", show_default=False)
            if not line:
                break
            gotchas.append(line)

    # Create CodeRef for source file tracking
    source_path = os.path.join(proj.path, module_path)
    source_ref = None
    if os.path.exists(source_path):
        source_ref = CodeRef.from_file(proj.path, module_path)

    # Create and store learning in v2 knowledge store
    learning = StoredLearning(
        module_path=module_path,
        learned_at=datetime.now(),
        summary=summary,
        purpose=purpose,
        key_functions=key_functions,
        gotchas=gotchas,
        source_ref=source_ref,
    )

    # Load existing knowledge store and add learning
    store = load_knowledge(proj.path, project)
    store.add_learning(learning)
    save_knowledge(proj.path, store)

    click.echo(f"\n✓ Stored learning for {module_path}")
    click.echo(f"  Summary: {summary}")
    click.echo(f"  Key functions: {len(key_functions)}")
    click.echo(f"  Gotchas: {len(gotchas)}")
    if source_ref:
        click.echo(f"  Source tracking: enabled (staleness detection)")


@cli.command()
@click.argument("project")
@click.argument("module_path")
@click.option("--source", is_flag=True, help="Also show original source code")
def recall(project: str, module_path: str, source: bool):
    """Retrieve what was learned about a module.

    Use this instead of re-reading source code. If no learning
    exists, you'll be prompted to read and learn.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    # Load from v2 knowledge store
    store = load_knowledge(proj.path, project)
    learning = store.get_learning(module_path)

    if learning:
        # Format with staleness check
        click.echo(learning.format_for_context(proj.path))

        if source:
            click.echo("\n--- Original Source ---\n")
            source_path = os.path.join(proj.path, module_path)
            if os.path.exists(source_path):
                with open(source_path) as f:
                    click.echo(f.read())
            else:
                click.echo(f"Source file not found: {source_path}")
    else:
        click.echo(f"No learning stored for {module_path}")
        click.echo(f"\nTo learn this module:")
        click.echo(f"  1. Read the source: cat {os.path.join(proj.path, module_path)}")
        click.echo(f"  2. Store learning: eri-rpg learn {project} {module_path}")


@cli.command()
@click.argument("project")
@click.argument("module_path")
def relearn(project: str, module_path: str):
    """Force re-read a module (removes stored learning).

    Use when the source code has changed significantly.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    # Load from v2 knowledge store
    store = load_knowledge(proj.path, project)

    if store.remove_learning(module_path):
        save_knowledge(proj.path, store)
        click.echo(f"✓ Removed learning for {module_path}")
        click.echo(f"\nNow read the source and store new learning:")
        click.echo(f"  eri-rpg learn {project} {module_path}")
    else:
        click.echo(f"No learning stored for {module_path}")


@cli.command()
@click.argument("project")
@click.argument("module_path")
def history(project: str, module_path: str):
    """Show version history for a module's learning.

    Displays all recorded versions with timestamps, operations,
    and associated git commits.

    Example:
        eri-rpg history eritrainer training/optimizer.py
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    store = load_knowledge(proj.path, project)
    learning = store.get_learning(module_path)

    if not learning:
        click.echo(f"No learning found for {module_path}")
        return

    click.echo(f"{'═' * 50}")
    click.echo(f" History: {module_path}")
    click.echo(f"{'═' * 50}")
    click.echo(f"Current version: v{learning.current_version}")
    click.echo("")

    if not learning.versions:
        click.echo("No version history available")
        click.echo("(Versions are created when learnings are modified)")
        return

    for v in reversed(learning.versions):
        marker = " (current)" if v.version == learning.current_version else ""
        click.echo(f"v{v.version}{marker} - {v.timestamp.strftime('%Y-%m-%d %H:%M')} - {v.operation}")
        if v.change_description:
            click.echo(f"    {v.change_description}")
        if v.commit_before:
            click.echo(f"    git before: {v.commit_before}")
        if v.commit_after:
            click.echo(f"    git after: {v.commit_after}")
        click.echo("")

    if learning.transplanted_from:
        click.echo(f"Transplanted from: {learning.transplanted_from}")

    if learning.transplanted_to_list:
        click.echo(f"Transplanted to: {', '.join(learning.transplanted_to_list)}")


@cli.command()
@click.argument("project")
@click.argument("module_path")
@click.option("-v", "--version", "target_version", type=int, default=None,
              help="Version to rollback to (default: previous)")
@click.option("--code", is_flag=True, help="Also restore files to disk from snapshot")
@click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
@click.option("--use-git", is_flag=True, help="Use git checkout instead of stored snapshots")
def rollback(project: str, module_path: str, target_version: int, code: bool, dry_run: bool, use_git: bool):
    """Rollback a module's learning to a previous version.

    Restores the learning's summary, purpose, key_functions, and gotchas
    to the state they were in at the specified version.

    With --code: Also restores the actual file contents from stored snapshots.

    Example:
        eri-rpg rollback eritrainer training/optimizer.py
        eri-rpg rollback eritrainer training/optimizer.py -v 2
        eri-rpg rollback eritrainer training/optimizer.py --code
        eri-rpg rollback eritrainer training/optimizer.py --code --dry-run
        eri-rpg rollback eritrainer training/optimizer.py --code --use-git
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    store = load_knowledge(proj.path, project)
    learning = store.get_learning(module_path)

    if not learning:
        click.echo(f"No learning found for {module_path}")
        return

    if not learning.versions:
        click.echo("No version history available")
        return

    # Find target version
    target = target_version if target_version is not None else learning.current_version - 1

    if target < 1:
        click.echo("Already at earliest version (versions start at 1)")
        return

    # Find the version by number
    version_obj = None
    for v in learning.versions:
        if v.version == target:
            version_obj = v
            break

    if not version_obj:
        available = [v.version for v in learning.versions]
        click.echo(f"Version {target} not found. Available: {available}")
        return

    old_version = learning.current_version

    if code:
        # Restore files to disk
        if use_git and version_obj.commit_before:
            # Use git checkout
            import subprocess
            if dry_run:
                click.echo(f"Would run: git checkout {version_obj.commit_before} -- {module_path}")
            else:
                try:
                    subprocess.run(
                        ['git', 'checkout', version_obj.commit_before, '--', module_path],
                        cwd=proj.path,
                        check=True,
                        capture_output=True,
                    )
                    click.echo(f"✓ Restored {module_path} from git commit {version_obj.commit_before}")
                except subprocess.CalledProcessError as e:
                    click.echo(f"Git checkout failed: {e.stderr.decode() if e.stderr else str(e)}", err=True)
                    sys.exit(1)

                # Also rollback metadata
                learning.rollback(target)
                store.add_learning(learning)
                save_knowledge(proj.path, store)
                click.echo(f"✓ Rolled back learning: v{old_version} -> v{target}")

        elif version_obj.files_content:
            # Use stored snapshot
            result = learning.rollback_files(
                project_path=proj.path,
                to_version=target,
                dry_run=dry_run,
            )

            click.echo(result.format())

            if not dry_run and result.success:
                store.add_learning(learning)
                save_knowledge(proj.path, store)

        else:
            click.echo(f"No code snapshot available for version {target}.")
            if version_obj.commit_before:
                click.echo(f"\nGit commit available. Re-run with --use-git:")
                click.echo(f"  eri-rpg rollback {project} {module_path} -v {target} --code --use-git")
            else:
                click.echo("You may need to restore manually from git history.")
            sys.exit(1)

    else:
        # Metadata-only rollback
        try:
            learning.rollback(target)
            store.add_learning(learning)
            save_knowledge(proj.path, store)

            click.echo(f"Rolled back {module_path}: v{old_version} -> v{target}")
            click.echo("\nNote: Only learning metadata was rolled back.")
            click.echo("To also restore file contents, use --code flag.")

            # Show what's available
            if version_obj.files_content:
                click.echo(f"\n  eri-rpg rollback {project} {module_path} -v {target} --code")
            elif version_obj.commit_before:
                click.echo(f"\n  eri-rpg rollback {project} {module_path} -v {target} --code --use-git")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("title")
@click.option("--reason", "-r", required=True, help="Why this decision was made")
@click.option("--affects", "-a", multiple=True, help="Module paths affected")
@click.option("--alt", multiple=True, help="Alternatives considered")
def decide(title: str, reason: str, affects: tuple, alt: tuple):
    """Record an architectural decision.

    Stores important decisions with rationale for future reference.

    Example:
        eri-rpg decide "Use PEFT for LoRA" \\
            -r "Better maintained than custom implementation" \\
            -a eritrainer/training/lora.py \\
            --alt "Custom LoRA" --alt "LoRAX"
    """
    state = State.load()

    # Get current project from state or ask
    project = state.current_task.split()[-1] if state.current_task else None

    if not project:
        click.echo("No active project context.")
        click.echo("Decisions are stored globally in state.")

    # Create decision ID from title
    decision_id = title.lower().replace(" ", "_")[:30]

    decision = Decision(
        id=decision_id,
        date=datetime.now(),
        title=title,
        reason=reason,
        affects=list(affects),
        alternatives=list(alt),
    )

    # Store in state history for now (could also store in graph)
    state.log("decision", f"{title}: {reason}")

    click.echo(f"✓ Recorded decision: {title}")
    click.echo(f"  Reason: {reason}")
    if affects:
        click.echo(f"  Affects: {', '.join(affects)}")
    if alt:
        click.echo(f"  Alternatives: {', '.join(alt)}")


@cli.command()
@click.argument("project")
@click.argument("name")
@click.argument("description")
def pattern(project: str, name: str, description: str):
    """Store a reusable pattern or gotcha.

    Record patterns you discover for future reference.

    Example:
        eri-rpg pattern onetrainer local_files_only \\
            "Always use local_files_only=True with from_pretrained()"
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    graph.knowledge.add_pattern(name, description)
    graph.save(proj.graph_path)

    click.echo(f"✓ Stored pattern: {name}")
    click.echo(f"  {description}")


@cli.command()
@click.argument("action")
@click.option("--feature", "-f", help="Feature name")
@click.option("--from-proj", help="Source project")
@click.option("--to-path", help="Target path")
def log(action: str, feature: str, from_proj: str, to_path: str):
    """Log an action to project history.

    Records transplants, modifications, and other actions.

    Example:
        eri-rpg log "Transplanted masked loss" \\
            -f masked_loss --from-proj onetrainer \\
            --to-path eritrainer/training/masked_loss.py
    """
    entry = HistoryEntry(
        date=datetime.now(),
        action="transplant" if "transplant" in action.lower() else "modify",
        description=action,
        feature=feature,
        from_project=from_proj,
        to_path=to_path,
    )

    state = State.load()
    state.log(entry.action, action)

    click.echo(f"✓ Logged: {action}")
    if feature:
        click.echo(f"  Feature: {feature}")
    if from_proj:
        click.echo(f"  From: {from_proj}")
    if to_path:
        click.echo(f"  To: {to_path}")


@cli.command("knowledge")
@click.argument("project")
def show_knowledge(project: str):
    """Show all stored knowledge for a project.

    Displays learnings, patterns, and statistics.
    """
    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    knowledge = graph.knowledge
    stats = knowledge.stats()

    click.echo(f"Knowledge for {project}")
    click.echo("=" * 40)
    click.echo("")

    click.echo(f"Learnings: {stats['learnings']}")
    if knowledge.learnings:
        for path, learning in sorted(knowledge.learnings.items()):
            age_days = (datetime.now() - learning.learned_at).days
            age_str = "today" if age_days == 0 else f"{age_days}d ago"
            click.echo(f"  • {path} ({age_str})")
            click.echo(f"    {learning.summary}")

    click.echo("")
    click.echo(f"Patterns: {stats['patterns']}")
    if knowledge.patterns:
        for name, desc in sorted(knowledge.patterns.items()):
            click.echo(f"  • {name}: {desc[:60]}...")

    click.echo("")
    click.echo(f"History entries: {stats['history_entries']}")
    recent = knowledge.get_recent_history(5)
    if recent:
        click.echo("  Recent:")
        for h in recent:
            click.echo(f"  • [{h.date.strftime('%m/%d')}] {h.action}: {h.description[:40]}...")

    # Token savings estimate
    if stats['learnings'] > 0:
        click.echo("")
        click.echo("Token savings estimate:")
        # Rough estimate: 500 tokens per learning vs 2000 tokens for source
        saved = stats['learnings'] * 1500
        click.echo(f"  ~{saved:,} tokens saved per context generation")


# ============================================================================
# Spec Commands
# ============================================================================

@cli.group()
def spec():
    """Spec management commands.

    Specs are first-class inputs that describe tasks, projects, and transplants.
    They provide a structured way to define work with validation and versioning.

    \b
        spec new <type>       - Create spec from template
        spec validate <path>  - Validate a spec file
        spec show <path>      - Display spec contents
        spec list             - List specs in project
    """
    pass


@spec.command("new")
@click.argument("spec_type", type=click.Choice(["task", "project", "transplant"]))
@click.option("-o", "--output", default=None, help="Output path (default: .eri-rpg/specs/)")
@click.option("--name", "-n", default=None, help="Spec name")
def spec_new(spec_type: str, output: str, name: str):
    """Create a new spec from template.

    Creates a spec file with example values that you can edit.

    \b
    Examples:
        eri-rpg spec new task
        eri-rpg spec new project -n my-app
        eri-rpg spec new transplant -o ./specs/my-transplant.json
    """
    from erirpg.specs import get_spec_template, create_spec, SPEC_VERSION

    template = get_spec_template(spec_type)

    if name:
        template["name"] = name

    # Create the spec to normalize and generate ID
    spec = create_spec(spec_type, **{k: v for k, v in template.items() if k != "spec_type"})

    # Determine output path
    if output:
        output_path = output
    else:
        # Default to .eri-rpg/specs/ in current directory
        specs_dir = os.path.join(os.getcwd(), ".eri-rpg", "specs")
        os.makedirs(specs_dir, exist_ok=True)
        output_path = os.path.join(specs_dir, f"{spec.id}.json")

    spec.save(output_path)

    click.echo(f"Created {spec_type} spec: {output_path}")
    click.echo("")
    click.echo("Edit the file to customize, then validate:")
    click.echo(f"  eri-rpg spec validate {output_path}")


@spec.command("validate")
@click.argument("path", type=click.Path(exists=True))
def spec_validate(path: str):
    """Validate a spec file.

    Checks for required fields and valid values.

    \b
    Example:
        eri-rpg spec validate ./specs/my-task.json
    """
    from erirpg.specs import load_spec, validate_spec

    try:
        spec = load_spec(path)
        is_valid, errors = validate_spec(spec)

        if is_valid:
            click.echo(f"✓ Valid {spec.spec_type} spec: {spec.id}")
            click.echo(f"  Name: {getattr(spec, 'name', 'N/A')}")
            click.echo(f"  Version: {spec.version}")
        else:
            click.echo(f"✗ Invalid spec: {path}", err=True)
            click.echo("")
            for error in errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)

    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {path}", err=True)
        click.echo(f"  {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error loading spec: {e}", err=True)
        sys.exit(1)


@spec.command("show")
@click.argument("path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def spec_show(path: str, as_json: bool):
    """Display spec contents.

    Shows the spec in a readable format.

    \b
    Example:
        eri-rpg spec show ./specs/my-task.json
        eri-rpg spec show ./specs/my-task.json --json
    """
    from erirpg.specs import load_spec

    try:
        spec = load_spec(path)

        if as_json:
            click.echo(json.dumps(spec.to_dict(), indent=2))
            return

        # Human-readable format
        click.echo(f"Spec: {spec.id}")
        click.echo("=" * 50)
        click.echo(f"Type: {spec.spec_type}")
        click.echo(f"Version: {spec.version}")
        click.echo(f"Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"Updated: {spec.updated_at.strftime('%Y-%m-%d %H:%M')}")
        click.echo("")

        # Type-specific fields
        if spec.spec_type == "task":
            click.echo(f"Name: {spec.name}")
            click.echo(f"Task Type: {spec.task_type or '(not set)'}")
            click.echo(f"Status: {spec.status}")
            click.echo(f"Priority: {spec.priority}")
            if spec.source_project:
                click.echo(f"Source: {spec.source_project}")
            if spec.target_project:
                click.echo(f"Target: {spec.target_project}")
            if spec.query:
                click.echo(f"Query: {spec.query}")
            if spec.description:
                click.echo(f"\nDescription:\n  {spec.description}")

        elif spec.spec_type == "project":
            click.echo(f"Name: {spec.name}")
            click.echo(f"Language: {spec.language}")
            if spec.framework:
                click.echo(f"Framework: {spec.framework}")
            click.echo(f"Core Feature: {spec.core_feature}")
            if spec.output_path:
                click.echo(f"Output: {spec.output_path}")
            if spec.directories:
                click.echo(f"\nDirectories: {', '.join(spec.directories)}")
            if spec.dependencies:
                click.echo(f"Dependencies: {', '.join(spec.dependencies)}")

        elif spec.spec_type == "transplant":
            click.echo(f"Name: {spec.name}")
            click.echo(f"Source: {spec.source_project}")
            click.echo(f"Target: {spec.target_project}")
            click.echo(f"Feature: {spec.feature_name or '(from file)'}")
            if spec.feature_file:
                click.echo(f"Feature File: {spec.feature_file}")
            if spec.components:
                click.echo(f"\nComponents ({len(spec.components)}):")
                for comp in spec.components[:5]:
                    click.echo(f"  - {comp}")
                if len(spec.components) > 5:
                    click.echo(f"  ... and {len(spec.components) - 5} more")

        # Common fields
        if spec.tags:
            click.echo(f"\nTags: {', '.join(spec.tags)}")
        if spec.notes:
            click.echo(f"\nNotes:\n  {spec.notes}")

    except Exception as e:
        click.echo(f"Error loading spec: {e}", err=True)
        sys.exit(1)


@spec.command("list")
@click.option("-t", "--type", "spec_type", type=click.Choice(["task", "project", "transplant"]),
              help="Filter by spec type")
@click.option("-p", "--path", default=None, help="Project path (default: current directory)")
def spec_list(spec_type: str, path: str):
    """List specs in a project.

    Shows all specs stored in the project's .eri-rpg/specs/ directory.

    \b
    Example:
        eri-rpg spec list
        eri-rpg spec list -t task
        eri-rpg spec list -p /path/to/project
    """
    from erirpg.specs import list_specs, load_spec

    project_path = path or os.getcwd()
    specs = list_specs(project_path, spec_type=spec_type)

    if not specs:
        click.echo("No specs found.")
        click.echo(f"\nCreate one with: eri-rpg spec new <type>")
        return

    click.echo(f"Specs in {project_path}:")
    click.echo("")

    for spec_path in specs:
        try:
            s = load_spec(spec_path)
            name = getattr(s, "name", s.id)
            click.echo(f"  [{s.spec_type}] {name}")
            click.echo(f"    ID: {s.id}")
            click.echo(f"    Path: {spec_path}")
        except Exception as e:
            click.echo(f"  [error] {spec_path}: {e}")
        click.echo("")


# ============================================================================
# Plan Commands
# ============================================================================

@cli.group("plan")
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
                pass

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


# ============================================================================
# Run Commands
# ============================================================================

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


# ============================================================================
# Memory Commands (v2 storage system)
# ============================================================================

@cli.group()
def memory():
    """Memory management commands (v2 storage).

    The v2 memory system stores knowledge in a separate knowledge.json
    file that survives reindexing. Commands:

    \b
        memory status    - Show memory stats and staleness
        memory search    - Search learnings by keyword
        memory stale     - List stale learnings
        memory refresh   - Update stale learning
        memory migrate   - Migrate v1 knowledge to v2
    """
    pass


@memory.command("status")
@click.argument("project")
def memory_status(project: str):
    """Show memory status for a project.

    Displays v2 knowledge store stats, staleness info, and health metrics.
    """
    from erirpg.memory import load_knowledge, get_knowledge_path
    from erirpg.migration import get_migration_status

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    # Get migration status
    migration = get_migration_status(proj.path)

    click.echo(f"Memory Status for {project}")
    click.echo("=" * 40)
    click.echo("")

    # Storage info
    click.echo("Storage:")
    click.echo(f"  graph.json: {'exists' if migration['graph_exists'] else 'missing'}")
    click.echo(f"  knowledge.json: {'exists' if migration['knowledge_exists'] else 'missing'}")

    if migration['has_embedded_knowledge']:
        click.echo("")
        click.echo("WARNING: v1 knowledge embedded in graph.json")
        click.echo(f"  Embedded learnings: {migration['embedded_learnings']}")
        click.echo(f"  Run: eri-rpg memory migrate {project}")

    # v2 knowledge stats
    if migration['knowledge_exists']:
        knowledge_path = get_knowledge_path(proj.path)
        store = load_knowledge(proj.path, project)
        stats = store.stats()

        click.echo("")
        click.echo("v2 Knowledge Store:")
        click.echo(f"  Learnings: {stats['learnings']}")
        click.echo(f"  Decisions: {stats['decisions']}")
        click.echo(f"  Patterns: {stats['patterns']}")
        click.echo(f"  Runs tracked: {stats['runs']}")

        # Staleness check
        stale = store.get_stale_learnings(proj.path)
        fresh = store.get_fresh_learnings(proj.path)

        click.echo("")
        click.echo("Staleness:")
        click.echo(f"  Fresh: {len(fresh)}")
        click.echo(f"  Stale: {len(stale)}")

        if stale:
            click.echo("")
            click.echo("Stale learnings need refresh:")
            for path in stale[:5]:
                click.echo(f"  - {path}")
            if len(stale) > 5:
                click.echo(f"  ... and {len(stale) - 5} more")
            click.echo(f"\nRun: eri-rpg memory stale {project}")

        # Health score
        total = stats['learnings']
        if total > 0:
            health = (len(fresh) / total) * 100
            click.echo("")
            click.echo(f"Health Score: {health:.0f}%")
    else:
        click.echo("")
        click.echo("No v2 knowledge store yet.")
        click.echo(f"Create learnings with: eri-rpg learn {project} <module>")


@memory.command("search")
@click.argument("project")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def memory_search(project: str, query: str, limit: int):
    """Search learnings by keyword.

    Searches summaries, purposes, functions, and gotchas.
    """
    from erirpg.memory import load_knowledge, get_knowledge_path

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    knowledge_path = get_knowledge_path(proj.path)
    if not os.path.exists(knowledge_path):
        click.echo(f"No knowledge.json found for {project}")
        click.echo(f"Create learnings first: eri-rpg learn {project} <module>")
        return

    store = load_knowledge(proj.path, project)
    results = store.search(query, limit=limit)

    if not results:
        click.echo(f"No learnings match: {query}")
        return

    click.echo(f"Search results for '{query}':")
    click.echo("")

    for path, learning, score in results:
        is_stale = learning.is_stale(proj.path)
        stale_marker = " [STALE]" if is_stale else ""
        click.echo(f"  {path} (score: {score:.2f}){stale_marker}")
        click.echo(f"    {learning.summary}")
        click.echo("")


@memory.command("stale")
@click.argument("project")
def memory_stale(project: str):
    """List all stale learnings.

    Shows learnings whose source files have changed since
    the learning was created.
    """
    from erirpg.memory import load_knowledge, get_knowledge_path

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    knowledge_path = get_knowledge_path(proj.path)
    if not os.path.exists(knowledge_path):
        click.echo(f"No knowledge.json found for {project}")
        return

    store = load_knowledge(proj.path, project)
    stale = store.get_stale_learnings(proj.path)

    if not stale:
        click.echo(f"All learnings are fresh!")
        return

    click.echo(f"Stale learnings in {project}:")
    click.echo("")

    for path in stale:
        learning = store.get_learning(path)
        if learning:
            age_days = (datetime.now() - learning.learned_at).days
            click.echo(f"  {path}")
            click.echo(f"    Learned: {age_days} days ago")
            click.echo(f"    Summary: {learning.summary}")
            click.echo("")

    click.echo("To refresh a learning:")
    click.echo(f"  eri-rpg memory refresh {project} <module_path>")
    click.echo("")
    click.echo("Or re-learn from scratch:")
    click.echo(f"  eri-rpg relearn {project} <module_path>")


@memory.command("refresh")
@click.argument("project")
@click.argument("module_path")
def memory_refresh(project: str, module_path: str):
    """Refresh a stale learning.

    Updates the CodeRef to current file state without changing
    the learning content. Use 'relearn' if content changed.
    """
    from erirpg.memory import load_knowledge, save_knowledge, get_knowledge_path
    from erirpg.refs import CodeRef

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    knowledge_path = get_knowledge_path(proj.path)
    if not os.path.exists(knowledge_path):
        click.echo(f"No knowledge.json found for {project}")
        sys.exit(1)

    store = load_knowledge(proj.path, project)
    learning = store.get_learning(module_path)

    if not learning:
        click.echo(f"No learning found for: {module_path}")
        sys.exit(1)

    # Check if source file exists
    file_path = os.path.join(proj.path, module_path)
    if not os.path.exists(file_path):
        click.echo(f"Source file no longer exists: {module_path}")
        click.echo("Consider removing this learning or updating the path.")
        sys.exit(1)

    # Check if actually stale
    if not learning.is_stale(proj.path):
        click.echo(f"Learning is not stale: {module_path}")
        return

    # Create new CodeRef with current file state
    try:
        new_ref = CodeRef.from_file(proj.path, module_path)
        learning.source_ref = new_ref
        learning.version += 1
        store.add_learning(learning)
        save_knowledge(proj.path, store)

        click.echo(f"Refreshed learning: {module_path}")
        click.echo(f"  New version: {learning.version}")
        click.echo("")
        click.echo("Note: Only the CodeRef was updated. If the code logic changed,")
        click.echo(f"consider re-learning: eri-rpg relearn {project} {module_path}")
    except Exception as e:
        click.echo(f"Error refreshing: {e}", err=True)
        sys.exit(1)


@memory.command("migrate")
@click.argument("project")
@click.option("--force", is_flag=True, help="Force migration even if knowledge.json exists")
def memory_migrate(project: str, force: bool):
    """Migrate v1 knowledge to v2 format.

    Extracts knowledge from graph.json into separate knowledge.json
    and creates CodeRefs for learnings.
    """
    from erirpg.migration import (
        check_migration_needed,
        migrate_knowledge,
        get_migration_status,
    )

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    # Check migration status
    status = get_migration_status(proj.path)

    if not status['has_embedded_knowledge']:
        click.echo("No v1 knowledge to migrate.")
        return

    if status['knowledge_exists'] and not force:
        click.echo("knowledge.json already exists.")
        click.echo("Use --force to overwrite.")
        return

    # Perform migration
    click.echo(f"Migrating knowledge for {project}...")

    result = migrate_knowledge(proj.path, project)

    if result['migrated']:
        click.echo("")
        click.echo("Migration complete:")
        click.echo(f"  Learnings: {result['learnings']}")
        click.echo(f"  Decisions: {result['decisions']}")
        click.echo(f"  Patterns: {result['patterns']}")
        click.echo(f"  CodeRefs created: {result['refs_created']}")
        if result['refs_failed'] > 0:
            click.echo(f"  CodeRefs failed (files missing): {result['refs_failed']}")
        click.echo("")
        click.echo("Knowledge now stored in knowledge.json (survives reindex)")
    else:
        click.echo(f"Migration failed: {result['error']}", err=True)
        sys.exit(1)


# ============================================================================
# Verification Commands
# ============================================================================

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


# ============================================================================
# Spec-Driven Execution Commands (NEW)
# ============================================================================

@cli.command("goal-plan")
@click.argument("project")
@click.argument("goal")
@click.option("-o", "--output", default=None, help="Output spec file path")
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
    except Exception:
        pass

    try:
        knowledge = load_knowledge(proj.path, project)
    except Exception:
        pass

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


# ============================================================================
# Quick Fix Commands (Lightweight Mode)
# ============================================================================

@cli.command("quick")
@click.argument("project")
@click.argument("file_path")
@click.argument("description")
@click.option("--no-commit", is_flag=True, help="Don't auto-commit after edit")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it")
def quick_cmd(project: str, file_path: str, description: str, no_commit: bool, dry_run: bool):
    """Start a quick fix on a single file.

    Lightweight mode for simple, focused changes without full spec ceremony.
    No run state, no steps - just snapshot, edit, commit.

    \b
    Examples:
        eri-rpg quick myproject src/utils.py "Fix off-by-one error"
        eri-rpg quick eritrainer train.py "Add debug logging"

    After editing, complete with: eri-rpg quick-done <project>
    Or cancel with: eri-rpg quick-cancel <project>
    """
    from erirpg.quick import quick_fix

    try:
        result = quick_fix(
            project=project,
            file_path=file_path,
            description=description,
            auto_commit=not no_commit,
            dry_run=dry_run,
        )
        if result == "ready":
            click.echo("")
            click.echo("Now edit the file. When done:")
            click.echo(f"  eri-rpg quick-done {project}")
            click.echo("")
            click.echo("To cancel and restore:")
            click.echo(f"  eri-rpg quick-cancel {project}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("quick-done")
@click.argument("project")
@click.option("--no-commit", is_flag=True, help="Don't commit changes")
@click.option("-m", "--message", default=None, help="Custom commit message")
def quick_done_cmd(project: str, no_commit: bool, message: str):
    """Complete a quick fix and commit changes.

    \b
    Example:
        eri-rpg quick-done myproject
        eri-rpg quick-done myproject -m "Better commit message"
    """
    from erirpg.quick import quick_done

    try:
        result = quick_done(
            project=project,
            auto_commit=not no_commit,
            commit_message=message,
        )
        if result:
            click.echo("")
            click.echo("Quick fix completed successfully.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("quick-cancel")
@click.argument("project")
def quick_cancel_cmd(project: str):
    """Cancel a quick fix and restore the original file.

    \b
    Example:
        eri-rpg quick-cancel myproject
    """
    from erirpg.quick import quick_cancel

    try:
        quick_cancel(project)
        click.echo("")
        click.echo("Quick fix cancelled.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("quick-status")
@click.argument("project")
def quick_status_cmd(project: str):
    """Check if a quick fix is active.

    \b
    Example:
        eri-rpg quick-status myproject
    """
    from erirpg.quick import load_quick_fix_state

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    state = load_quick_fix_state(proj.path)

    if not state or not state.get("quick_fix_active"):
        click.echo(f"No active quick fix for {project}")
        return

    click.echo(f"Quick fix active:")
    click.echo(f"  File: {state.get('target_file')}")
    click.echo(f"  Description: {state.get('description')}")
    click.echo(f"  Started: {state.get('timestamp')}")
    click.echo("")
    click.echo(f"Complete: eri-rpg quick-done {project}")
    click.echo(f"Cancel: eri-rpg quick-cancel {project}")


# ============================================================================
# Cleanup Commands (Run Management)
# ============================================================================

@cli.command("cleanup")
@click.argument("project")
@click.option("--prune", is_flag=True, help="Delete stale/abandoned runs")
@click.option("--days", default=7, help="Consider runs older than N days as stale (default: 7)")
@click.option("--force", is_flag=True, help="Delete without confirmation")
def cleanup_cmd(project: str, prune: bool, days: int, force: bool):
    """List and optionally prune abandoned runs.

    Stale runs are IN_PROGRESS runs that haven't been touched in N days.

    \b
    Examples:
        eri-rpg cleanup myproject          # List runs
        eri-rpg cleanup myproject --prune  # Delete stale runs
        eri-rpg cleanup myproject --prune --days 1  # Delete runs older than 1 day
    """
    from pathlib import Path
    from datetime import datetime, timedelta

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    run_dir = Path(proj.path) / ".eri-rpg" / "runs"
    if not run_dir.exists():
        click.echo(f"No runs found for {project}")
        return

    runs = list(run_dir.glob("*.json"))
    if not runs:
        click.echo(f"No runs found for {project}")
        return

    # Analyze runs
    now = datetime.now()
    stale_threshold = now - timedelta(days=days)

    completed = []
    in_progress = []
    stale = []

    for run_file in runs:
        try:
            with open(run_file) as f:
                run_data = json.load(f)

            run_id = run_data.get("id", run_file.stem)
            goal = run_data.get("spec", {}).get("goal", "Unknown")[:40]
            started = run_data.get("started_at", "")
            completed_at = run_data.get("completed_at")

            # Parse timestamp
            try:
                if started:
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00").split("+")[0])
                else:
                    started_dt = datetime.fromtimestamp(run_file.stat().st_mtime)
            except Exception:
                started_dt = datetime.fromtimestamp(run_file.stat().st_mtime)

            run_info = {
                "id": run_id,
                "goal": goal,
                "started": started_dt,
                "file": run_file,
            }

            if completed_at:
                completed.append(run_info)
            elif started_dt < stale_threshold:
                stale.append(run_info)
            else:
                in_progress.append(run_info)

        except Exception as e:
            click.echo(f"Warning: Could not parse {run_file.name}: {e}", err=True)

    # Show summary
    click.echo(f"Runs for {project}:")
    click.echo(f"  Completed: {len(completed)}")
    click.echo(f"  In Progress: {len(in_progress)}")
    click.echo(f"  Stale (>{days} days): {len(stale)}")
    click.echo("")

    if stale:
        click.echo("Stale runs:")
        for run in stale:
            age = (now - run["started"]).days
            click.echo(f"  {run['id']}: {run['goal']}... ({age} days old)")
        click.echo("")

    if in_progress:
        click.echo("Active runs:")
        for run in in_progress:
            age = (now - run["started"]).days
            click.echo(f"  {run['id']}: {run['goal']}... ({age} days old)")
        click.echo("")

    if prune and stale:
        if not force:
            click.confirm(f"Delete {len(stale)} stale run(s)?", abort=True)

        for run in stale:
            run["file"].unlink()
            click.echo(f"Deleted: {run['id']}")

        click.echo(f"\nPruned {len(stale)} stale run(s).")

        # Also clean up preflight state if no active runs
        if not in_progress:
            preflight_file = Path(proj.path) / ".eri-rpg" / "preflight_state.json"
            if preflight_file.exists():
                preflight_file.unlink()
                click.echo("Cleared stale preflight state.")
    elif prune:
        click.echo("No stale runs to prune.")


@cli.command("runs")
@click.argument("project")
@click.option("--all", "show_all", is_flag=True, help="Show all runs including completed")
def runs_cmd(project: str, show_all: bool):
    """List runs for a project.

    \b
    Example:
        eri-rpg runs myproject
        eri-rpg runs myproject --all
    """
    from pathlib import Path
    from datetime import datetime

    registry = Registry.get_instance()
    proj = registry.get(project)

    if not proj:
        click.echo(f"Error: Project '{project}' not found", err=True)
        sys.exit(1)

    run_dir = Path(proj.path) / ".eri-rpg" / "runs"
    if not run_dir.exists():
        click.echo(f"No runs found for {project}")
        return

    runs = sorted(run_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        click.echo(f"No runs found for {project}")
        return

    click.echo(f"Runs for {project}:")
    click.echo("")

    for run_file in runs:
        try:
            with open(run_file) as f:
                run_data = json.load(f)

            run_id = run_data.get("id", run_file.stem)
            goal = run_data.get("spec", {}).get("goal", "Unknown")[:50]
            completed_at = run_data.get("completed_at")

            if completed_at and not show_all:
                continue

            status = "COMPLETED" if completed_at else "IN_PROGRESS"
            status_icon = "✓" if completed_at else "○"

            # Get progress
            plan = run_data.get("plan", {})
            steps = plan.get("steps", [])
            completed_steps = sum(1 for s in steps if s.get("status") == "completed")
            total_steps = len(steps)

            click.echo(f"  {status_icon} {run_id}")
            click.echo(f"    Goal: {goal}...")
            click.echo(f"    Status: {status} ({completed_steps}/{total_steps} steps)")
            click.echo("")

        except Exception as e:
            click.echo(f"  ? {run_file.name} (error: {e})")

    click.echo("")
    click.echo("Resume a run: eri-rpg goal-status <project>")
    click.echo("Cleanup stale: eri-rpg cleanup <project> --prune")


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
