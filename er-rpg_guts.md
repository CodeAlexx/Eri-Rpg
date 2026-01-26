# EriRPG Guts

Scope: Core EriRPG Python package (`erirpg/`).
Note: Bundled external source trees (`gsd-source/`, `rlm-source/`) are excluded.

## `erirpg/__init__.py`

What it is: EriRPG - Cross-project feature transplant tool.

```python
"""
EriRPG - Cross-project feature transplant tool.

A lean CLI tool for:
- Registering external projects with paths
- Indexing codebases to build dependency graphs
- Finding capabilities in code via local search
- Extracting features as self-contained units
- Planning transplants between projects
- Generating minimal context for Claude Code

No LLM calls. Pure Python. Claude Code is the LLM.
"""

__version__ = "0.1.0"
__author__ = "Alex"

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg.registry import Registry, Project

__all__ = [
    "Graph",
    "Module",
    "Interface",
    "Edge",
    "Registry",
    "Project",
]
```

## `erirpg/cli.py`

What it is: EriRPG CLI - One tool. Three modes. No bloat.

```python
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
@click.option("--lang", default=None, type=click.Choice(["python", "rust", "c", "typescript"]),
              help="Programming language (auto-detected if not specified)")
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
        use_learnings=not no_learnings
    )

    tokens = estimate_tokens(feature, transplant_plan)

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
def learn(project: str, module_path: str, summary: str, purpose: str):
    """Store a learning about a module.

    After understanding a module, record key insights so you don't
    have to re-read it later. Saves ~85% tokens on revisits.

    Example:
        eri-rpg learn onetrainer modules/util/loss.py \\
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

    # Prompt for optional details
    click.echo("\nOptional: Enter key functions (name: description), empty line to finish:")
    key_functions = {}
    while True:
        line = click.prompt("", default="", show_default=False)
        if not line:
            break
        if ":" in line:
            name, desc = line.split(":", 1)
            key_functions[name.strip()] = desc.strip()

    click.echo("\nOptional: Enter gotchas (one per line), empty line to finish:")
    gotchas = []
    while True:
        line = click.prompt("", default="", show_default=False)
        if not line:
            break
        gotchas.append(line)

    # Create and store learning
    learning = Learning(
        module_path=module_path,
        learned_at=datetime.now(),
        summary=summary,
        purpose=purpose,
        key_functions=key_functions,
        gotchas=gotchas,
    )

    graph.knowledge.add_learning(learning)
    graph.save(proj.graph_path)

    click.echo(f"\n✓ Stored learning for {module_path}")
    click.echo(f"  Summary: {summary}")
    click.echo(f"  Key functions: {len(key_functions)}")
    click.echo(f"  Gotchas: {len(gotchas)}")


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

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    learning = graph.knowledge.get_learning(module_path)

    if learning:
        click.echo(learning.format_for_context())

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

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if graph.knowledge.remove_learning(module_path):
        graph.save(proj.graph_path)
        click.echo(f"✓ Removed learning for {module_path}")
        click.echo(f"\nNow read the source and store new learning:")
        click.echo(f"  eri-rpg learn {project} {module_path}")
    else:
        click.echo(f"No learning stored for {module_path}")


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
# Entry Point
# ============================================================================

def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
```

## `erirpg/context.py`

What it is: Context generation for Claude Code.

```python
"""
Context generation for Claude Code.

Generates minimal, focused context files that include:
- Stored learnings (if available) OR source code (via refs)
- Target interfaces (signatures only)
- Transplant plan with mappings and wiring
- Staleness warnings for outdated learnings

The knowledge system allows ~85% token reduction on revisited modules
by storing learnings about code instead of re-reading source every time.

The v2 ref system enables:
- Fresh code loading via hydration (no stale snapshots)
- Staleness detection for learnings
- Lightweight feature files (refs instead of full code)
"""

from datetime import datetime
import os
from pathlib import Path
from typing import Optional

from erirpg.ops import Feature, TransplantPlan
from erirpg.graph import Graph
from erirpg.registry import Project
from erirpg.memory import load_knowledge, get_knowledge_path


def generate_context(
    feature: Feature,
    plan: TransplantPlan,
    source_graph: Optional[Graph],
    target_graph: Graph,
    target_project: Project,
    source_project: Optional[Project] = None,
    output_dir: Optional[str] = None,
    use_learnings: bool = True,
) -> str:
    """Generate context file for Claude Code.

    Args:
        feature: Extracted feature
        plan: Transplant plan
        source_graph: Source project's graph (for backward compat knowledge lookup)
        target_graph: Target project's graph
        target_project: Target project
        source_project: Source project (for v2 knowledge and hydration)
        output_dir: Where to save (default: target/.eri-rpg/context/)
        use_learnings: If True, use stored learnings instead of source when available

    Returns:
        Path to generated context file
    """
    if not output_dir:
        output_dir = os.path.join(target_project.path, ".eri-rpg", "context")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Try to load v2 knowledge store if source project is available
    knowledge_store = None
    source_path = None
    if source_project:
        source_path = source_project.path
        knowledge_path = get_knowledge_path(source_path)
        if os.path.exists(knowledge_path):
            knowledge_store = load_knowledge(source_path, source_project.name)

    # Generate context markdown
    lines = []

    # Header
    lines.append(f"# Transplant: {feature.name}")
    lines.append("")
    lines.append(f"From: **{feature.source_project}**")
    lines.append(f"To: **{plan.target_project}**")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Source Code Section
    lines.append("---")
    lines.append("")
    lines.append("## Source Code")
    lines.append("")
    lines.append(f"These files from `{feature.source_project}` implement the feature:")
    lines.append("")

    modules_with_learnings = []
    modules_without_learnings = []
    stale_learnings = []

    # Hydrate code from refs if source_path is available
    hydrated_code = {}
    if source_path and feature.code_refs:
        hydrated_code = feature.hydrate_code(source_path)

    for comp_path in feature.components:
        # Check for v2 knowledge first, fall back to graph knowledge
        learning = None
        is_stale = False

        if use_learnings:
            # Try v2 knowledge store first
            if knowledge_store is not None:
                stored = knowledge_store.get_learning(comp_path)
                if stored:
                    # Convert to Learning format for display
                    from erirpg.knowledge import Learning
                    learning = Learning(
                        module_path=stored.module_path,
                        learned_at=stored.learned_at,
                        summary=stored.summary,
                        purpose=stored.purpose,
                        key_functions=stored.key_functions,
                        key_params=stored.key_params,
                        gotchas=stored.gotchas,
                        dependencies=stored.dependencies,
                        transplanted_to=stored.transplanted_to,
                        source_ref=stored.source_ref,
                        confidence=stored.confidence,
                        version=stored.version,
                    )
                    if source_path and stored.is_stale(source_path):
                        is_stale = True
                        stale_learnings.append(comp_path)

            # Fall back to graph knowledge (v1 backward compat)
            if learning is None and source_graph is not None:
                learning = source_graph.knowledge.get_learning(comp_path)
                if learning and source_path:
                    is_stale = learning.is_stale(source_path)
                    if is_stale:
                        stale_learnings.append(comp_path)

        lines.append(f"### `{comp_path}`")
        lines.append("")

        if learning:
            # Use stored learning instead of source code
            modules_with_learnings.append(comp_path)

            # Show staleness warning if applicable
            if is_stale:
                lines.append("**WARNING: This learning may be stale (source file changed)**")
                lines.append(f"Refresh with: `eri-rpg memory refresh {feature.source_project} {comp_path}`")
                lines.append("")

            lines.append(learning.format_for_context())
            lines.append("")
            lines.append("**Source**: [SKIPPED - learning exists]")
            lines.append(f"To re-read source: `eri-rpg recall {feature.source_project} {comp_path} --source`")
            lines.append("")
        else:
            # No learning - include source code (hydrated fresh or from snapshot)
            modules_without_learnings.append(comp_path)

            # Prefer hydrated code, fall back to snapshot
            code = hydrated_code.get(comp_path) or feature.code_snapshots.get(comp_path, "")

            lines.append("**No stored understanding yet.**")
            lines.append("")
            if code:
                lines.append("```python")
                lines.append(code.strip())
                lines.append("```")
            else:
                lines.append("*Code not available - use `--snapshot` when extracting for offline use*")
            lines.append("")
            lines.append(f"After understanding this, store it: `eri-rpg learn {feature.source_project} {comp_path}`")
            lines.append("")

    # Target Interfaces Section
    lines.append("---")
    lines.append("")
    lines.append("## Target Interfaces")
    lines.append("")
    lines.append(f"Existing interfaces in `{plan.target_project}` to integrate with:")
    lines.append("")

    # Find relevant target modules
    relevant_modules = set()
    for mapping in plan.mappings:
        if mapping.target_module:
            relevant_modules.add(mapping.target_module)

    if relevant_modules:
        for mod_path in sorted(relevant_modules):
            mod = target_graph.get_module(mod_path)
            if mod:
                lines.append(f"### `{mod_path}`")
                lines.append("")
                lines.append(f"**Summary:** {mod.summary or '(no summary)'}")
                lines.append("")
                lines.append("**Interfaces:**")
                for iface in mod.interfaces:
                    if iface.signature:
                        lines.append(f"- `{iface.signature}`")
                    else:
                        lines.append(f"- `{iface.type} {iface.name}`")
                lines.append("")
    else:
        lines.append("*No existing interfaces to integrate with - creating new files.*")
        lines.append("")

    # Transplant Plan Section
    lines.append("---")
    lines.append("")
    lines.append("## Transplant Plan")
    lines.append("")

    # Mappings
    lines.append("### Mappings")
    lines.append("")
    lines.append("| Source | Target | Action | Notes |")
    lines.append("|--------|--------|--------|-------|")
    for m in plan.mappings:
        source = f"`{m.source_interface}`"
        target = f"`{m.target_interface or 'NEW'}`" if m.target_interface else "CREATE"
        lines.append(f"| {source} | {target} | {m.action} | {m.notes} |")
    lines.append("")

    # Wiring
    if plan.wiring:
        lines.append("### Wiring Tasks")
        lines.append("")
        for w in plan.wiring:
            lines.append(f"- **{w.file}**: {w.action} - {w.details}")
        lines.append("")

    # Generation Order
    lines.append("### Implementation Order")
    lines.append("")
    lines.append("Create/modify files in this order (dependencies first):")
    lines.append("")
    for i, path in enumerate(plan.generation_order, 1):
        lines.append(f"{i}. `{path}`")
    lines.append("")

    # Instructions Section
    lines.append("---")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append("1. **Read** the source code above carefully")
    lines.append("2. **Adapt** each component for the target project:")
    lines.append("   - Adjust imports to match target structure")
    lines.append("   - Implement interface adapters where needed")
    lines.append("   - Follow target project conventions")
    lines.append("3. **Wire** components together:")
    for w in plan.wiring:
        lines.append(f"   - {w.file}: {w.details}")
    lines.append("4. **Verify** the transplant works")
    lines.append("")
    lines.append("After implementation, run: `eri-rpg validate`")
    lines.append("")

    # Write file
    filename = f"{feature.name.replace(' ', '_').lower()}.md"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


def estimate_tokens(feature: Feature, plan: TransplantPlan) -> int:
    """Estimate token count for context.

    Rough estimate: ~4 chars per token for code, ~3 for prose.
    """
    code_chars = sum(len(code) for code in feature.code.values())
    plan_chars = len(str(plan.mappings)) + len(str(plan.wiring))
    prose_chars = 1000  # Header, instructions

    code_tokens = code_chars / 4
    other_tokens = (plan_chars + prose_chars) / 3

    return int(code_tokens + other_tokens)
```

## `erirpg/graph.py`

What it is: Graph data structures for representing codebases.

```python
"""
Graph data structures for representing codebases.

Provides Module, Interface, Edge, and Graph classes for storing
and querying indexed project structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from erirpg.knowledge import Knowledge


@dataclass
class Interface:
    """A public interface (class, function, method, const) in a module."""
    name: str
    type: str  # "class" | "function" | "method" | "const"
    signature: str = ""  # Full signature string
    docstring: str = ""  # First line of docstring
    methods: List[str] = field(default_factory=list)  # For classes
    line: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "signature": self.signature,
            "docstring": self.docstring,
            "methods": self.methods,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Interface":
        return cls(
            name=d["name"],
            type=d["type"],
            signature=d.get("signature", ""),
            docstring=d.get("docstring", ""),
            methods=d.get("methods", []),
            line=d.get("line", 0),
        )


@dataclass
class Module:
    """A source file/module in the project."""
    path: str  # Relative path from project root
    lang: str  # "python" | "rust" | "typescript"
    lines: int = 0
    summary: str = ""  # From module docstring
    interfaces: List[Interface] = field(default_factory=list)
    deps_internal: List[str] = field(default_factory=list)  # Modules in same project
    deps_external: List[str] = field(default_factory=list)  # External packages

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "lang": self.lang,
            "lines": self.lines,
            "summary": self.summary,
            "interfaces": [i.to_dict() for i in self.interfaces],
            "deps_internal": self.deps_internal,
            "deps_external": self.deps_external,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Module":
        return cls(
            path=d["path"],
            lang=d["lang"],
            lines=d.get("lines", 0),
            summary=d.get("summary", ""),
            interfaces=[Interface.from_dict(i) for i in d.get("interfaces", [])],
            deps_internal=d.get("deps_internal", []),
            deps_external=d.get("deps_external", []),
        )


@dataclass
class Edge:
    """A dependency edge between modules."""
    source: str  # Module path
    target: str  # Module path or external package
    edge_type: str  # "imports" | "uses" | "inherits"
    specifics: List[str] = field(default_factory=list)  # What exactly is imported

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "specifics": self.specifics,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(
            source=d["source"],
            target=d["target"],
            edge_type=d["edge_type"],
            specifics=d.get("specifics", []),
        )


@dataclass
class Graph:
    """Complete dependency graph for a project."""
    project: str
    version: str = "1.0.0"
    indexed_at: datetime = field(default_factory=datetime.now)
    modules: Dict[str, Module] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    _knowledge: Optional["Knowledge"] = field(default=None, repr=False)

    @property
    def knowledge(self) -> "Knowledge":
        """Get or create knowledge store."""
        if self._knowledge is None:
            from erirpg.knowledge import Knowledge
            self._knowledge = Knowledge()
        return self._knowledge

    @knowledge.setter
    def knowledge(self, value: "Knowledge") -> None:
        self._knowledge = value

    def save(self, path: str) -> None:
        """Save graph to JSON file.

        Note: As of v2, knowledge is stored separately in knowledge.json
        and is NOT included in the graph. The graph is structural-only
        and can be safely rebuilt without losing knowledge.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project": self.project,
            "version": self.version,
            "indexed_at": self.indexed_at.isoformat(),
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

        # Knowledge is NO LONGER embedded in graph.json (v2 change)
        # It is stored separately in knowledge.json to survive reindexing
        # See erirpg.memory for the new storage system

        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Graph":
        """Load graph from JSON file.

        Note: For v1 backward compatibility, knowledge embedded in graph.json
        is still loaded. However, new code should use the separate knowledge.json
        storage via erirpg.memory. Use migration.migrate_knowledge() to move
        embedded knowledge to the new storage format.
        """
        with open(path, "r") as f:
            data = json.load(f)

        graph = cls(
            project=data["project"],
            version=data.get("version", "1.0.0"),
            indexed_at=datetime.fromisoformat(data["indexed_at"]),
            modules={k: Module.from_dict(v) for k, v in data["modules"].items()},
            edges=[Edge.from_dict(e) for e in data.get("edges", [])],
        )

        # Load knowledge if present (v1 backward compatibility)
        # New code should use erirpg.memory.load_knowledge() instead
        if "knowledge" in data:
            from erirpg.knowledge import Knowledge
            graph._knowledge = Knowledge.from_dict(data["knowledge"])

        return graph

    def get_module(self, path: str) -> Optional[Module]:
        """Get a module by path."""
        return self.modules.get(path)

    def add_module(self, module: Module) -> None:
        """Add a module to the graph."""
        self.modules[module.path] = module

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_deps(self, path: str) -> List[str]:
        """Get modules that this module depends on (internal only)."""
        module = self.modules.get(path)
        if not module:
            return []
        return module.deps_internal

    def get_dependents(self, path: str) -> List[str]:
        """Get modules that depend on this module."""
        dependents = []
        for edge in self.edges:
            if edge.target == path and edge.source in self.modules:
                dependents.append(edge.source)
        return dependents

    def get_transitive_deps(self, path: str) -> Set[str]:
        """Get all transitive dependencies of a module."""
        visited = set()
        to_visit = [path]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            deps = self.get_deps(current)
            for dep in deps:
                if dep not in visited:
                    to_visit.append(dep)

        visited.discard(path)  # Don't include self
        return visited

    def get_transitive_dependents(self, path: str) -> Set[str]:
        """Get all modules that transitively depend on this module."""
        visited = set()
        to_visit = [path]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            dependents = self.get_dependents(current)
            for dep in dependents:
                if dep not in visited:
                    to_visit.append(dep)

        visited.discard(path)  # Don't include self
        return visited

    def topo_sort(self, modules: List[str]) -> List[str]:
        """Topologically sort modules by dependencies.

        Returns modules in order where dependencies come before dependents.
        """
        # Build dependency subgraph for requested modules
        module_set = set(modules)
        in_degree = {m: 0 for m in modules}

        for m in modules:
            deps = self.get_deps(m)
            for dep in deps:
                if dep in module_set:
                    in_degree[m] += 1

        # Kahn's algorithm
        result = []
        queue = [m for m, d in in_degree.items() if d == 0]

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Find modules that depend on current
            for m in modules:
                if current in self.get_deps(m):
                    in_degree[m] -= 1
                    if in_degree[m] == 0:
                        queue.append(m)

        # Handle cycles by appending remaining
        remaining = [m for m in modules if m not in result]
        result.extend(remaining)

        return result

    def stats(self) -> dict:
        """Get graph statistics."""
        return {
            "modules": len(self.modules),
            "edges": len(self.edges),
            "total_lines": sum(m.lines for m in self.modules.values()),
            "total_interfaces": sum(len(m.interfaces) for m in self.modules.values()),
        }
```

## `erirpg/indexer.py`

What it is: Code indexer for building dependency graphs.

```python
"""
Code indexer for building dependency graphs.

Walks project directories, parses files, builds module graph
with interfaces and dependencies.
"""

import os
from pathlib import Path
from typing import List, Set, Tuple
from datetime import datetime

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg.parsers.python import (
    parse_python_file,
    resolve_import_to_module,
    classify_external_package,
)
from erirpg.parsers.c import parse_c_file, resolve_include_to_module
from erirpg.parsers.rust import parse_rust_file, resolve_use_to_module, classify_external_crate
from erirpg.parsers import get_parser_for_file, detect_language
from erirpg.registry import Project


# Standard library modules to ignore as external deps
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
    "base64", "binascii", "bisect", "builtins", "bz2",
    "calendar", "cgi", "cgitb", "chunk", "cmath", "code", "codecs",
    "codeop", "collections", "colorsys", "compileall", "concurrent",
    "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "cProfile", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "doctest", "email", "encodings", "enum", "errno",
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "grp", "gzip",
    "hashlib", "heapq", "hmac", "html", "http",
    "imaplib", "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
    "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder",
    "multiprocessing", "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
    "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
    "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors", "shelve", "shlex",
    "shutil", "signal", "site", "smtplib", "sndhdr", "socket", "socketserver",
    "spwd", "sqlite3", "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize", "trace",
    "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
    "unicodedata", "unittest", "urllib", "uu", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    # Typing extensions
    "typing_extensions",
}


def index_project(project: Project, verbose: bool = False) -> Graph:
    """Index a project and build its dependency graph.

    This function rebuilds the structural index (graph.json) from source files.
    Knowledge (stored in knowledge.json) is PRESERVED and NOT modified by
    reindexing - it exists independently of the structural graph.

    Args:
        project: Project to index
        verbose: Print progress

    Returns:
        The built Graph

    Note:
        If you have v1 knowledge embedded in graph.json, run migration first:
        >>> from erirpg.migration import auto_migrate_if_needed
        >>> auto_migrate_if_needed(project.path, project.name)
    """
    # Check for v1 knowledge that needs migration
    from erirpg.migration import check_migration_needed, auto_migrate_if_needed

    needs_migration, reason = check_migration_needed(project.path)
    if needs_migration:
        if verbose:
            print(f"Migrating v1 knowledge to separate storage...")
        result = auto_migrate_if_needed(project.path, project.name)
        if result and result.get("migrated"):
            if verbose:
                print(f"  Migrated {result['learnings']} learnings, "
                      f"{result['decisions']} decisions, "
                      f"{result['patterns']} patterns")

    # Create new graph (structural only - knowledge is separate)
    graph = Graph(project=project.name)

    # Find all source files based on language
    if project.lang == "python":
        source_files = _find_python_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} Python files")
    elif project.lang == "c":
        source_files = _find_c_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} C/C++ files")
    elif project.lang == "rust":
        source_files = _find_rust_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} Rust files")
    else:
        raise NotImplementedError(f"Language '{project.lang}' not yet supported")

    # Collect all module paths first
    module_paths = set()
    for file_path in source_files:
        rel_path = os.path.relpath(file_path, project.path)
        module_paths.add(rel_path)

    # Parse each file
    for file_path in source_files:
        rel_path = os.path.relpath(file_path, project.path)

        if verbose:
            print(f"  Parsing {rel_path}")

        try:
            # Get appropriate parser
            parser = get_parser_for_file(file_path)
            if not parser:
                if verbose:
                    print(f"    Skipped (no parser)")
                continue
            parsed = parser(file_path)
        except Exception as e:
            if verbose:
                print(f"    Error: {e}")
            continue

        # Create interfaces
        interfaces = []
        for iface in parsed.get("interfaces", []):
            interfaces.append(Interface(
                name=iface["name"],
                type=iface["type"],
                signature=iface.get("signature", ""),
                docstring=iface.get("docstring", ""),
                methods=iface.get("methods", []),
                line=iface.get("line", 0),
            ))

        # Resolve imports based on language
        deps_internal = []
        deps_external = set()

        for imp in parsed.get("imports", []):
            if project.lang == "python":
                resolved = resolve_import_to_module(
                    imp, list(module_paths), project.name
                )
                if resolved:
                    deps_internal.append(resolved)
                else:
                    pkg = classify_external_package(imp)
                    if pkg and pkg not in STDLIB_MODULES:
                        deps_external.add(pkg)
            elif project.lang == "c":
                resolved = resolve_include_to_module(imp, list(module_paths))
                if resolved:
                    deps_internal.append(resolved)
                elif not imp.get("is_system"):
                    deps_external.add(imp["name"])
            elif project.lang == "rust":
                resolved = resolve_use_to_module(imp, list(module_paths))
                if resolved:
                    deps_internal.append(resolved)
                else:
                    crate = classify_external_crate(imp)
                    if crate:
                        deps_external.add(crate)

        module = Module(
            path=rel_path,
            lang=project.lang,
            lines=parsed.get("lines", 0),
            summary=parsed.get("docstring", ""),
            interfaces=interfaces,
            deps_internal=list(set(deps_internal)),
            deps_external=list(deps_external),
        )

        graph.add_module(module)

    # Build edges from internal deps
    for mod_path, module in graph.modules.items():
        for dep in module.deps_internal:
            edge = Edge(
                source=mod_path,
                target=dep,
                edge_type="imports",
                specifics=[],  # Could populate from parsed imports
            )
            graph.add_edge(edge)

    # Save graph
    graph.indexed_at = datetime.now()
    graph.save(project.graph_path)

    if verbose:
        stats = graph.stats()
        print(f"Indexed: {stats['modules']} modules, {stats['edges']} edges, "
              f"{stats['total_lines']} lines, {stats['total_interfaces']} interfaces")

    return graph


def _find_python_files(root: str) -> List[str]:
    """Find all Python files in a directory tree.

    Excludes:
    - __pycache__ directories
    - .git directories
    - .eri-rpg directories
    - Virtual environments (venv, .venv, env)
    - Build directories (build, dist, *.egg-info)
    """
    exclude_dirs = {
        "__pycache__", ".git", ".eri-rpg", "venv", ".venv", "env",
        "build", "dist", "node_modules", ".tox", ".pytest_cache",
    }

    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs and not d.endswith(".egg-info")
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                py_files.append(os.path.join(dirpath, filename))

    return py_files


def _find_c_files(root: str) -> List[str]:
    """Find all C/C++ files in a directory tree.

    Includes: .c, .h, .cpp, .hpp, .cc, .hh
    Excludes: build directories, .git, etc.
    """
    exclude_dirs = {
        ".git", ".eri-rpg", "build", "cmake-build-debug", "cmake-build-release",
        "node_modules", ".vscode", ".idea", "third_party", "vendor", "deps",
    }

    c_extensions = {".c", ".h", ".cpp", ".hpp", ".cc", ".hh"}
    c_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext in c_extensions:
                c_files.append(os.path.join(dirpath, filename))

    return c_files


def _find_rust_files(root: str) -> List[str]:
    """Find all Rust files in a directory tree.

    Includes: .rs files
    Excludes: target directory, .git, etc.
    """
    exclude_dirs = {
        ".git", ".eri-rpg", "target", "node_modules", ".vscode", ".idea",
    }

    rs_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs
        ]

        for filename in filenames:
            if filename.endswith(".rs"):
                rs_files.append(os.path.join(dirpath, filename))

    return rs_files


def get_or_load_graph(project: Project) -> Graph:
    """Get project graph, loading from disk if exists."""
    if project.is_indexed() and os.path.exists(project.graph_path):
        return Graph.load(project.graph_path)
    raise ValueError(f"Project '{project.name}' is not indexed. Run: eri-rpg index {project.name}")
```

## `erirpg/knowledge.py`

What it is: Knowledge storage for EriRPG.

```python
"""
Knowledge storage for EriRPG.

Stores learnings about code so Claude Code doesn't have to re-read
and re-learn modules every session.

Components:
- Learning: What was understood about a module (summary, key functions, gotchas)
- Decision: Architectural/design decisions with rationale
- Pattern: Reusable patterns and gotchas
- HistoryEntry: Log of actions taken (transplants, modifications)

Note: This module maintains backward compatibility with v1 storage.
For v2 persistent storage that survives reindexing, see memory.py.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from erirpg.refs import CodeRef


@dataclass
class Learning:
    """What Claude Code learned about a module.

    Attributes:
        module_path: Path to the module relative to project root
        learned_at: When the learning was created
        summary: One-line purpose/summary
        purpose: Detailed explanation
        key_functions: Map of function name -> description
        key_params: Map of parameter name -> explanation
        gotchas: List of things to watch out for
        dependencies: External dependencies used
        transplanted_to: If this was transplanted somewhere
        source_ref: Reference to the source code (for staleness detection)
        confidence: How confident we are in this learning (0.0-1.0)
        version: Version number for tracking updates
    """
    module_path: str
    learned_at: datetime
    summary: str  # One-line purpose
    purpose: str  # Detailed explanation
    key_functions: Dict[str, str] = field(default_factory=dict)  # name -> description
    key_params: Dict[str, str] = field(default_factory=dict)  # param -> explanation
    gotchas: List[str] = field(default_factory=list)  # Things to watch out for
    dependencies: List[str] = field(default_factory=list)  # External deps used
    transplanted_to: Optional[str] = None  # If transplanted somewhere
    source_ref: Optional["CodeRef"] = None  # Reference to source code
    confidence: float = 1.0  # Confidence score (0.0-1.0)
    version: int = 1  # Version number

    def is_stale(self, project_path: str) -> bool:
        """Check if this learning is stale (source code changed).

        Args:
            project_path: Root path of the project

        Returns:
            True if source_ref exists and file has changed, False otherwise
        """
        if self.source_ref is None:
            return False  # No ref to check against
        return self.source_ref.is_stale(project_path)

    def to_dict(self) -> dict:
        d = {
            "module_path": self.module_path,
            "learned_at": self.learned_at.isoformat(),
            "summary": self.summary,
            "purpose": self.purpose,
            "key_functions": self.key_functions,
            "key_params": self.key_params,
            "gotchas": self.gotchas,
            "dependencies": self.dependencies,
            "transplanted_to": self.transplanted_to,
            "confidence": self.confidence,
            "version": self.version,
        }
        if self.source_ref:
            d["source_ref"] = self.source_ref.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Learning":
        source_ref = None
        if "source_ref" in d:
            from erirpg.refs import CodeRef
            source_ref = CodeRef.from_dict(d["source_ref"])

        return cls(
            module_path=d["module_path"],
            learned_at=datetime.fromisoformat(d["learned_at"]),
            summary=d.get("summary", ""),
            purpose=d.get("purpose", ""),
            key_functions=d.get("key_functions", {}),
            key_params=d.get("key_params", {}),
            gotchas=d.get("gotchas", []),
            dependencies=d.get("dependencies", []),
            transplanted_to=d.get("transplanted_to"),
            source_ref=source_ref,
            confidence=d.get("confidence", 1.0),
            version=d.get("version", 1),
        )

    def format_for_context(self) -> str:
        """Format learning for inclusion in context file."""
        lines = [
            f"### Stored Understanding (from {self.learned_at.strftime('%Y-%m-%d')})",
            f"",
            f"**Summary**: {self.summary}",
            f"",
            f"**Purpose**: {self.purpose}",
        ]

        if self.key_functions:
            lines.append("")
            lines.append("**Key Functions**:")
            for name, desc in self.key_functions.items():
                lines.append(f"- `{name}`: {desc}")

        if self.key_params:
            lines.append("")
            lines.append("**Key Parameters**:")
            for name, desc in self.key_params.items():
                lines.append(f"- `{name}`: {desc}")

        if self.gotchas:
            lines.append("")
            lines.append("**Gotchas**:")
            for g in self.gotchas:
                lines.append(f"- {g}")

        if self.dependencies:
            lines.append("")
            lines.append(f"**Dependencies**: {', '.join(self.dependencies)}")

        if self.transplanted_to:
            lines.append("")
            lines.append(f"**Transplanted to**: `{self.transplanted_to}`")

        return "\n".join(lines)


@dataclass
class Decision:
    """An architectural or design decision."""
    id: str
    date: datetime
    title: str
    reason: str
    affects: List[str] = field(default_factory=list)  # Module paths affected
    alternatives: List[str] = field(default_factory=list)  # What was considered

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "title": self.title,
            "reason": self.reason,
            "affects": self.affects,
            "alternatives": self.alternatives,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Decision":
        return cls(
            id=d["id"],
            date=datetime.fromisoformat(d["date"]),
            title=d["title"],
            reason=d.get("reason", ""),
            affects=d.get("affects", []),
            alternatives=d.get("alternatives", []),
        )


@dataclass
class HistoryEntry:
    """A logged action in the project history."""
    date: datetime
    action: str  # "transplant", "create", "modify", "delete"
    description: str
    feature: Optional[str] = None
    from_project: Optional[str] = None
    to_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "action": self.action,
            "description": self.description,
            "feature": self.feature,
            "from_project": self.from_project,
            "to_path": self.to_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            date=datetime.fromisoformat(d["date"]),
            action=d["action"],
            description=d.get("description", ""),
            feature=d.get("feature"),
            from_project=d.get("from_project"),
            to_path=d.get("to_path"),
        )


@dataclass
class Knowledge:
    """All knowledge stored for a project."""
    learnings: Dict[str, Learning] = field(default_factory=dict)  # module_path -> Learning
    decisions: List[Decision] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)  # name -> description
    history: List[HistoryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "learnings": {k: v.to_dict() for k, v in self.learnings.items()},
            "decisions": [d.to_dict() for d in self.decisions],
            "patterns": self.patterns,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Knowledge":
        return cls(
            learnings={k: Learning.from_dict(v) for k, v in d.get("learnings", {}).items()},
            decisions=[Decision.from_dict(x) for x in d.get("decisions", [])],
            patterns=d.get("patterns", {}),
            history=[HistoryEntry.from_dict(x) for x in d.get("history", [])],
        )

    # CRUD operations

    def add_learning(self, learning: Learning) -> None:
        """Add or update a learning for a module."""
        self.learnings[learning.module_path] = learning

    def get_learning(self, module_path: str) -> Optional[Learning]:
        """Get learning for a module, if exists."""
        return self.learnings.get(module_path)

    def has_learning(self, module_path: str) -> bool:
        """Check if learning exists for a module."""
        return module_path in self.learnings

    def remove_learning(self, module_path: str) -> bool:
        """Remove learning for a module. Returns True if removed."""
        if module_path in self.learnings:
            del self.learnings[module_path]
            return True
        return False

    def add_decision(self, decision: Decision) -> None:
        """Add a decision."""
        self.decisions.append(decision)

    def get_decisions_for_module(self, module_path: str) -> List[Decision]:
        """Get all decisions affecting a module."""
        return [d for d in self.decisions if module_path in d.affects]

    def add_pattern(self, name: str, description: str) -> None:
        """Add or update a pattern."""
        self.patterns[name] = description

    def get_pattern(self, name: str) -> Optional[str]:
        """Get a pattern by name."""
        return self.patterns.get(name)

    def log_action(self, entry: HistoryEntry) -> None:
        """Log an action to history."""
        self.history.append(entry)

    def get_recent_history(self, limit: int = 10) -> List[HistoryEntry]:
        """Get most recent history entries."""
        return sorted(self.history, key=lambda h: h.date, reverse=True)[:limit]

    def stats(self) -> dict:
        """Get knowledge statistics."""
        return {
            "learnings": len(self.learnings),
            "decisions": len(self.decisions),
            "patterns": len(self.patterns),
            "history_entries": len(self.history),
        }


def load_knowledge(graph_path: str) -> Knowledge:
    """Load knowledge from a graph.json file."""
    path = Path(graph_path)
    if not path.exists():
        return Knowledge()

    with open(path) as f:
        data = json.load(f)

    if "knowledge" not in data:
        return Knowledge()

    return Knowledge.from_dict(data["knowledge"])


def save_knowledge(graph_path: str, knowledge: Knowledge) -> None:
    """Save knowledge to a graph.json file (merges with existing)."""
    path = Path(graph_path)

    if path.exists():
        with open(path) as f:
            data = json.load(f)
    else:
        data = {}

    data["knowledge"] = knowledge.to_dict()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

## `erirpg/memory.py`

What it is: Persistent semantic memory for EriRPG.

```python
"""
Persistent semantic memory for EriRPG.

This module provides the KnowledgeStore - a separate storage layer for
semantic knowledge that persists independently of the structural graph.

Key design principles:
- Knowledge survives reindexing (stored in separate knowledge.json)
- Staleness is tracked via CodeRefs
- Search enables finding relevant learnings by query

Storage structure:
    .eri-rpg/
    ├── graph.json       # Structural index (rebuildable)
    ├── knowledge.json   # Semantic memory (PRESERVED)
    └── runs/            # Execution history (in knowledge.json)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import json
import os
from pathlib import Path

from erirpg.refs import CodeRef


@dataclass
class RunRecord:
    """Record of a command execution for context tracking.

    Attributes:
        timestamp: When the command was run
        command: The command that was executed
        modules_read: List of modules that were read during execution
        modules_written: List of modules that were written/modified
        success: Whether the command completed successfully
        duration_ms: How long the command took in milliseconds
        notes: Optional notes about the run
    """
    timestamp: datetime
    command: str
    modules_read: List[str] = field(default_factory=list)
    modules_written: List[str] = field(default_factory=list)
    success: bool = True
    duration_ms: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "command": self.command,
            "modules_read": self.modules_read,
            "modules_written": self.modules_written,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunRecord":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            command=d["command"],
            modules_read=d.get("modules_read", []),
            modules_written=d.get("modules_written", []),
            success=d.get("success", True),
            duration_ms=d.get("duration_ms", 0),
            notes=d.get("notes", ""),
        )


@dataclass
class StoredLearning:
    """A learning stored in the knowledge store.

    This is the storage representation that includes the CodeRef.
    The Learning class in knowledge.py can be converted to/from this.
    """
    module_path: str
    learned_at: datetime
    summary: str
    purpose: str
    key_functions: Dict[str, str] = field(default_factory=dict)
    key_params: Dict[str, str] = field(default_factory=dict)
    gotchas: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    transplanted_to: Optional[str] = None
    source_ref: Optional[CodeRef] = None
    confidence: float = 1.0
    version: int = 1

    def is_stale(self, project_path: str) -> bool:
        """Check if this learning is stale (source changed)."""
        if self.source_ref is None:
            return False  # No ref to check
        return self.source_ref.is_stale(project_path)

    def to_dict(self) -> dict:
        d = {
            "module_path": self.module_path,
            "learned_at": self.learned_at.isoformat(),
            "summary": self.summary,
            "purpose": self.purpose,
            "key_functions": self.key_functions,
            "key_params": self.key_params,
            "gotchas": self.gotchas,
            "dependencies": self.dependencies,
            "transplanted_to": self.transplanted_to,
            "confidence": self.confidence,
            "version": self.version,
        }
        if self.source_ref:
            d["source_ref"] = self.source_ref.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StoredLearning":
        source_ref = None
        if "source_ref" in d:
            source_ref = CodeRef.from_dict(d["source_ref"])

        return cls(
            module_path=d["module_path"],
            learned_at=datetime.fromisoformat(d["learned_at"]),
            summary=d.get("summary", ""),
            purpose=d.get("purpose", ""),
            key_functions=d.get("key_functions", {}),
            key_params=d.get("key_params", {}),
            gotchas=d.get("gotchas", []),
            dependencies=d.get("dependencies", []),
            transplanted_to=d.get("transplanted_to"),
            source_ref=source_ref,
            confidence=d.get("confidence", 1.0),
            version=d.get("version", 1),
        )


@dataclass
class StoredDecision:
    """An architectural or design decision stored in knowledge."""
    id: str
    date: datetime
    title: str
    reason: str
    affects: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "title": self.title,
            "reason": self.reason,
            "affects": self.affects,
            "alternatives": self.alternatives,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StoredDecision":
        return cls(
            id=d["id"],
            date=datetime.fromisoformat(d["date"]),
            title=d["title"],
            reason=d.get("reason", ""),
            affects=d.get("affects", []),
            alternatives=d.get("alternatives", []),
        )


@dataclass
class KnowledgeStore:
    """Persistent semantic knowledge store.

    Stores learnings, decisions, patterns, and run history
    independently of the structural graph. Survives reindexing.
    """
    project: str
    version: str = "2.0.0"
    learnings: Dict[str, StoredLearning] = field(default_factory=dict)
    decisions: List[StoredDecision] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)
    runs: List[RunRecord] = field(default_factory=list)

    # CRUD for learnings

    def add_learning(self, learning: StoredLearning) -> None:
        """Add or update a learning."""
        self.learnings[learning.module_path] = learning

    def get_learning(self, module_path: str) -> Optional[StoredLearning]:
        """Get learning for a module path."""
        return self.learnings.get(module_path)

    def has_learning(self, module_path: str) -> bool:
        """Check if learning exists for a module."""
        return module_path in self.learnings

    def remove_learning(self, module_path: str) -> bool:
        """Remove a learning. Returns True if it existed."""
        if module_path in self.learnings:
            del self.learnings[module_path]
            return True
        return False

    # CRUD for decisions

    def add_decision(self, decision: StoredDecision) -> None:
        """Add a decision."""
        self.decisions.append(decision)

    def get_decisions_for_module(self, module_path: str) -> List[StoredDecision]:
        """Get all decisions affecting a module."""
        return [d for d in self.decisions if module_path in d.affects]

    # CRUD for patterns

    def add_pattern(self, name: str, description: str) -> None:
        """Add or update a pattern."""
        self.patterns[name] = description

    def get_pattern(self, name: str) -> Optional[str]:
        """Get a pattern by name."""
        return self.patterns.get(name)

    # Run tracking

    def add_run(self, run: RunRecord) -> None:
        """Add a run record."""
        self.runs.append(run)

    def get_recent_runs(self, limit: int = 10) -> List[RunRecord]:
        """Get most recent run records."""
        return sorted(self.runs, key=lambda r: r.timestamp, reverse=True)[:limit]

    # Staleness detection

    def get_stale_learnings(self, project_path: str) -> List[str]:
        """Find all learnings whose source files have changed.

        Args:
            project_path: Root path of the project

        Returns:
            List of module paths with stale learnings
        """
        stale = []
        for module_path, learning in self.learnings.items():
            if learning.is_stale(project_path):
                stale.append(module_path)
        return stale

    def get_fresh_learnings(self, project_path: str) -> List[str]:
        """Find all learnings that are still fresh.

        Args:
            project_path: Root path of the project

        Returns:
            List of module paths with fresh learnings
        """
        fresh = []
        for module_path, learning in self.learnings.items():
            if not learning.is_stale(project_path):
                fresh.append(module_path)
        return fresh

    # Search

    def search(self, query: str, limit: int = 10) -> List[tuple[str, StoredLearning, float]]:
        """Search learnings by query.

        Simple keyword-based search matching against:
        - Module path
        - Summary
        - Purpose
        - Key function names and descriptions
        - Gotchas

        Args:
            query: Search query (space-separated keywords)
            limit: Maximum results to return

        Returns:
            List of (module_path, learning, score) tuples
        """
        from erirpg.search import search_learnings
        return search_learnings(self.learnings, query, limit)

    # Statistics

    def stats(self) -> dict:
        """Get knowledge store statistics."""
        return {
            "learnings": len(self.learnings),
            "decisions": len(self.decisions),
            "patterns": len(self.patterns),
            "runs": len(self.runs),
        }

    # Persistence

    def save(self, path: str) -> None:
        """Save knowledge store to JSON file.

        Args:
            path: Path to knowledge.json file
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project": self.project,
            "version": self.version,
            "saved_at": datetime.now().isoformat(),
            "learnings": {k: v.to_dict() for k, v in self.learnings.items()},
            "decisions": [d.to_dict() for d in self.decisions],
            "patterns": self.patterns,
            "runs": [r.to_dict() for r in self.runs[-100:]],  # Keep last 100 runs
        }

        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "KnowledgeStore":
        """Load knowledge store from JSON file.

        Args:
            path: Path to knowledge.json file

        Returns:
            Loaded KnowledgeStore, or empty one if file doesn't exist
        """
        if not os.path.exists(path):
            # Return empty store - caller should set project name
            return cls(project="unknown")

        with open(path, "r") as f:
            data = json.load(f)

        return cls(
            project=data.get("project", "unknown"),
            version=data.get("version", "2.0.0"),
            learnings={
                k: StoredLearning.from_dict(v)
                for k, v in data.get("learnings", {}).items()
            },
            decisions=[
                StoredDecision.from_dict(d)
                for d in data.get("decisions", [])
            ],
            patterns=data.get("patterns", {}),
            runs=[
                RunRecord.from_dict(r)
                for r in data.get("runs", [])
            ],
        )


def get_knowledge_path(project_path: str) -> str:
    """Get the path to knowledge.json for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Path to .eri-rpg/knowledge.json
    """
    return os.path.join(project_path, ".eri-rpg", "knowledge.json")


def load_knowledge(project_path: str, project_name: str) -> KnowledgeStore:
    """Load knowledge store for a project.

    Args:
        project_path: Root path of the project
        project_name: Name of the project

    Returns:
        KnowledgeStore for the project
    """
    path = get_knowledge_path(project_path)
    store = KnowledgeStore.load(path)
    if store.project == "unknown":
        store.project = project_name
    return store


def save_knowledge(project_path: str, store: KnowledgeStore) -> None:
    """Save knowledge store for a project.

    Args:
        project_path: Root path of the project
        store: KnowledgeStore to save
    """
    path = get_knowledge_path(project_path)
    store.save(path)
```

## `erirpg/migration.py`

What it is: Migration utilities for EriRPG storage format.

```python
"""
Migration utilities for EriRPG storage format.

Handles migration from v1 (knowledge embedded in graph.json) to
v2 (knowledge in separate knowledge.json with CodeRefs).
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from erirpg.refs import CodeRef
from erirpg.memory import (
    KnowledgeStore,
    StoredLearning,
    StoredDecision,
    get_knowledge_path,
)


def check_migration_needed(project_path: str) -> Tuple[bool, str]:
    """Check if migration is needed for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Tuple of (needs_migration: bool, reason: str)
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    if not os.path.exists(graph_path):
        return False, "No graph.json found"

    # Check if knowledge.json already exists
    if os.path.exists(knowledge_path):
        return False, "Already migrated (knowledge.json exists)"

    # Check if graph.json has embedded knowledge
    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        return False, "No knowledge in graph.json to migrate"

    knowledge = data["knowledge"]
    has_content = any([
        knowledge.get("learnings"),
        knowledge.get("decisions"),
        knowledge.get("patterns"),
        knowledge.get("history"),
    ])

    if not has_content:
        return False, "Knowledge section is empty"

    return True, "Knowledge found in graph.json, ready to migrate"


def migrate_knowledge(
    project_path: str,
    project_name: str,
    create_refs: bool = True,
    backup: bool = True,
) -> dict:
    """Migrate knowledge from graph.json to knowledge.json.

    This is the main migration function. It:
    1. Reads knowledge from graph.json
    2. Creates CodeRefs for learnings (if files exist)
    3. Writes to knowledge.json
    4. Optionally backs up old graph.json

    Args:
        project_path: Root path of the project
        project_name: Name of the project
        create_refs: If True, create CodeRefs for learnings
        backup: If True, backup graph.json before migration

    Returns:
        Dict with migration results:
        - migrated: bool
        - learnings: int (count migrated)
        - decisions: int (count migrated)
        - patterns: int (count migrated)
        - refs_created: int (CodeRefs created)
        - refs_failed: int (files not found for refs)
        - error: str (if migration failed)
    """
    result = {
        "migrated": False,
        "learnings": 0,
        "decisions": 0,
        "patterns": 0,
        "refs_created": 0,
        "refs_failed": 0,
        "error": None,
    }

    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    # Check preconditions
    if not os.path.exists(graph_path):
        result["error"] = "No graph.json found"
        return result

    if os.path.exists(knowledge_path):
        result["error"] = "knowledge.json already exists, skipping migration"
        return result

    # Load graph.json
    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        result["error"] = "No knowledge in graph.json to migrate"
        return result

    old_knowledge = data["knowledge"]

    # Backup graph.json
    if backup:
        backup_path = graph_path + ".v1.backup"
        shutil.copy(graph_path, backup_path)

    # Create new knowledge store
    store = KnowledgeStore(project=project_name)

    # Migrate learnings
    for module_path, learning_data in old_knowledge.get("learnings", {}).items():
        # Create CodeRef if file exists
        source_ref = None
        if create_refs:
            try:
                source_ref = CodeRef.from_file(project_path, module_path)
                result["refs_created"] += 1
            except FileNotFoundError:
                result["refs_failed"] += 1
                # Still migrate the learning, just without a ref

        # Create stored learning
        stored = StoredLearning(
            module_path=module_path,
            learned_at=datetime.fromisoformat(learning_data["learned_at"]),
            summary=learning_data.get("summary", ""),
            purpose=learning_data.get("purpose", ""),
            key_functions=learning_data.get("key_functions", {}),
            key_params=learning_data.get("key_params", {}),
            gotchas=learning_data.get("gotchas", []),
            dependencies=learning_data.get("dependencies", []),
            transplanted_to=learning_data.get("transplanted_to"),
            source_ref=source_ref,
            confidence=learning_data.get("confidence", 1.0),
            version=learning_data.get("version", 1),
        )
        store.add_learning(stored)
        result["learnings"] += 1

    # Migrate decisions
    for decision_data in old_knowledge.get("decisions", []):
        stored = StoredDecision(
            id=decision_data["id"],
            date=datetime.fromisoformat(decision_data["date"]),
            title=decision_data["title"],
            reason=decision_data.get("reason", ""),
            affects=decision_data.get("affects", []),
            alternatives=decision_data.get("alternatives", []),
        )
        store.add_decision(stored)
        result["decisions"] += 1

    # Migrate patterns
    for name, description in old_knowledge.get("patterns", {}).items():
        store.add_pattern(name, description)
        result["patterns"] += 1

    # Note: history entries are NOT migrated as they have a different format
    # in v2 (RunRecord vs HistoryEntry). Old history stays in graph.json.

    # Save new knowledge store
    store.save(knowledge_path)

    result["migrated"] = True
    return result


def remove_embedded_knowledge(project_path: str, backup: bool = True) -> bool:
    """Remove embedded knowledge from graph.json after migration.

    Call this after verifying migration was successful to clean up
    the old embedded knowledge from graph.json.

    Args:
        project_path: Root path of the project
        backup: If True, backup graph.json before modification

    Returns:
        True if successful, False otherwise
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")

    if not os.path.exists(graph_path):
        return False

    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        return True  # Already clean

    if backup:
        backup_path = graph_path + ".pre-cleanup.backup"
        shutil.copy(graph_path, backup_path)

    del data["knowledge"]

    with open(graph_path, "w") as f:
        json.dump(data, f, indent=2)

    return True


def auto_migrate_if_needed(project_path: str, project_name: str) -> Optional[dict]:
    """Automatically migrate if needed, otherwise return None.

    This is a convenience function that checks if migration is needed
    and performs it if so. Safe to call multiple times.

    Args:
        project_path: Root path of the project
        project_name: Name of the project

    Returns:
        Migration result dict if migration was performed, None otherwise
    """
    needs_migration, reason = check_migration_needed(project_path)

    if not needs_migration:
        return None

    return migrate_knowledge(project_path, project_name)


def get_migration_status(project_path: str) -> dict:
    """Get detailed migration status for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Dict with status information
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    status = {
        "graph_exists": os.path.exists(graph_path),
        "knowledge_exists": os.path.exists(knowledge_path),
        "has_embedded_knowledge": False,
        "embedded_learnings": 0,
        "embedded_decisions": 0,
        "embedded_patterns": 0,
        "standalone_learnings": 0,
        "standalone_decisions": 0,
        "standalone_patterns": 0,
        "migration_needed": False,
        "migration_reason": "",
    }

    # Check graph.json
    if status["graph_exists"]:
        with open(graph_path, "r") as f:
            data = json.load(f)
        if "knowledge" in data:
            status["has_embedded_knowledge"] = True
            knowledge = data["knowledge"]
            status["embedded_learnings"] = len(knowledge.get("learnings", {}))
            status["embedded_decisions"] = len(knowledge.get("decisions", []))
            status["embedded_patterns"] = len(knowledge.get("patterns", {}))

    # Check knowledge.json
    if status["knowledge_exists"]:
        with open(knowledge_path, "r") as f:
            data = json.load(f)
        status["standalone_learnings"] = len(data.get("learnings", {}))
        status["standalone_decisions"] = len(data.get("decisions", []))
        status["standalone_patterns"] = len(data.get("patterns", {}))

    # Determine migration status
    needs_migration, reason = check_migration_needed(project_path)
    status["migration_needed"] = needs_migration
    status["migration_reason"] = reason

    return status
```

## `erirpg/modes/__init__.py`

What it is: EriRPG Modes - Three ways to work.

```python
"""
EriRPG Modes - Three ways to work.

- new: Create new project from scratch
- take: Transplant feature from Project A to Project B
- work: Modify existing project
"""

from erirpg.modes.take import run_take
from erirpg.modes.work import run_work
from erirpg.modes.new import run_new, run_next, QUESTIONS

__all__ = ["run_take", "run_work", "run_new", "run_next", "QUESTIONS"]
```

## `erirpg/modes/new.py`

What it is: New Mode - Create new project from scratch.

```python
"""
New Mode - Create new project from scratch.

Usage:
    eri-rpg new "video editor with timeline and effects"

Flow:
    1. Ask - questions until it understands what you want
    2. Spec - generate PROJECT.md + STRUCTURE.md
    3. Structure - generate project skeleton
    4. Plan - break into buildable chunks
    5. Context - generate context for first chunk
    6. Guide - tell user what to do next
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from erirpg.registry import Registry
from erirpg.state import State


@dataclass
class ProjectSpec:
    """Specification for a new project."""
    name: str
    description: str
    language: str = "python"
    framework: Optional[str] = None

    # Core features
    core_features: List[str] = field(default_factory=list)

    # Constraints
    constraints: List[str] = field(default_factory=list)

    # Structure
    directories: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)

    # Chunks (buildable pieces)
    chunks: List[Dict] = field(default_factory=list)


@dataclass
class Question:
    """A question to ask the user."""
    id: str
    question: str
    why: str  # Why we're asking
    options: Optional[List[str]] = None  # If multiple choice
    default: Optional[str] = None
    required: bool = True


# Question flow for new projects
QUESTIONS = [
    Question(
        id="name",
        question="What should we call this project?",
        why="Need a name for the directory and references",
        default=None,
        required=True,
    ),
    Question(
        id="core_feature",
        question="What's the ONE core feature? (be specific)",
        why="Starting with one thing keeps scope manageable",
        required=True,
    ),
    Question(
        id="language",
        question="What language?",
        why="Determines project structure and tooling",
        options=["python", "typescript", "rust", "go"],
        default="python",
        required=True,
    ),
    Question(
        id="framework",
        question="Any framework? (or 'none')",
        why="Frameworks dictate structure",
        default="none",
        required=False,
    ),
    Question(
        id="constraints",
        question="Any constraints? (e.g., 'must work offline', 'no external deps')",
        why="Constraints guide architecture decisions",
        default="none",
        required=False,
    ),
]


def slugify(name: str) -> str:
    """Convert name to valid directory name."""
    return name.lower().replace(" ", "_").replace("-", "_")


def generate_project_spec(answers: Dict[str, str], description: str) -> ProjectSpec:
    """Generate project specification from answers."""
    name = slugify(answers.get("name", "project"))

    # Parse constraints
    constraints_raw = answers.get("constraints", "none")
    constraints = []
    if constraints_raw and constraints_raw.lower() != "none":
        constraints = [c.strip() for c in constraints_raw.split(",")]

    # Determine structure based on language/framework
    language = answers.get("language", "python")
    framework = answers.get("framework", "none")
    if framework.lower() == "none":
        framework = None

    directories, key_files = get_structure_for(language, framework)

    # Create chunks from core feature
    core_feature = answers.get("core_feature", "main functionality")
    chunks = create_chunks(core_feature, language, framework)

    return ProjectSpec(
        name=name,
        description=description,
        language=language,
        framework=framework,
        core_features=[core_feature],
        constraints=constraints,
        directories=directories,
        key_files=key_files,
        chunks=chunks,
    )


def get_structure_for(language: str, framework: Optional[str]) -> tuple:
    """Get directory structure and key files for language/framework."""

    if language == "python":
        if framework == "fastapi":
            return (
                ["app", "app/api", "app/models", "app/core", "tests"],
                ["app/__init__.py", "app/main.py", "app/api/__init__.py",
                 "app/models/__init__.py", "app/core/__init__.py", "app/core/config.py",
                 "tests/__init__.py", "requirements.txt", "README.md"],
            )
        elif framework == "flask":
            return (
                ["app", "app/routes", "app/models", "tests"],
                ["app/__init__.py", "app/routes/__init__.py", "app/models/__init__.py",
                 "tests/__init__.py", "requirements.txt", "README.md"],
            )
        else:
            # Plain Python
            return (
                ["src", "tests"],
                ["src/__init__.py", "src/main.py", "tests/__init__.py",
                 "requirements.txt", "README.md"],
            )

    elif language == "typescript":
        if framework == "react":
            return (
                ["src", "src/components", "src/hooks", "src/utils", "public"],
                ["src/index.tsx", "src/App.tsx", "src/components/.gitkeep",
                 "package.json", "tsconfig.json", "README.md"],
            )
        elif framework == "node" or framework == "express":
            return (
                ["src", "src/routes", "src/models", "src/utils", "tests"],
                ["src/index.ts", "src/app.ts", "src/routes/index.ts",
                 "package.json", "tsconfig.json", "README.md"],
            )
        else:
            return (
                ["src", "tests"],
                ["src/index.ts", "package.json", "tsconfig.json", "README.md"],
            )

    elif language == "rust":
        return (
            ["src"],
            ["src/main.rs", "src/lib.rs", "Cargo.toml", "README.md"],
        )

    elif language == "go":
        return (
            ["cmd", "internal", "pkg"],
            ["cmd/main.go", "go.mod", "README.md"],
        )

    # Default
    return (["src"], ["src/main.py", "README.md"])


def create_chunks(core_feature: str, language: str, framework: Optional[str]) -> List[Dict]:
    """Break core feature into buildable chunks."""

    # Generic chunking - could be smarter
    chunks = [
        {
            "id": "001",
            "name": "Project Setup",
            "description": f"Initialize {language} project structure and dependencies",
            "creates": ["config", "dependencies", "base structure"],
            "depends_on": [],
        },
        {
            "id": "002",
            "name": "Core Data Structures",
            "description": f"Define data models for: {core_feature}",
            "creates": ["models", "types", "interfaces"],
            "depends_on": ["001"],
        },
        {
            "id": "003",
            "name": "Core Logic",
            "description": f"Implement main logic for: {core_feature}",
            "creates": ["business logic", "algorithms"],
            "depends_on": ["002"],
        },
        {
            "id": "004",
            "name": "Integration",
            "description": "Wire components together and create entry point",
            "creates": ["main entry", "CLI or API"],
            "depends_on": ["003"],
        },
    ]

    return chunks


def generate_project_md(spec: ProjectSpec, output_dir: str) -> str:
    """Generate PROJECT.md specification."""
    lines = [
        f"# {spec.name}",
        "",
        f"**Description:** {spec.description}",
        f"**Language:** {spec.language}",
    ]

    if spec.framework:
        lines.append(f"**Framework:** {spec.framework}")

    lines.extend([
        "",
        "## Core Features",
        "",
    ])

    for feature in spec.core_features:
        lines.append(f"- {feature}")

    if spec.constraints:
        lines.extend([
            "",
            "## Constraints",
            "",
        ])
        for constraint in spec.constraints:
            lines.append(f"- {constraint}")

    lines.extend([
        "",
        "## Build Order",
        "",
    ])

    for chunk in spec.chunks:
        lines.append(f"### Chunk {chunk['id']}: {chunk['name']}")
        lines.append(f"{chunk['description']}")
        lines.append(f"- Creates: {', '.join(chunk['creates'])}")
        if chunk['depends_on']:
            lines.append(f"- Depends on: {', '.join(chunk['depends_on'])}")
        lines.append("")

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(output_dir, "PROJECT.md")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def generate_structure_md(spec: ProjectSpec, output_dir: str) -> str:
    """Generate STRUCTURE.md with directory layout."""
    lines = [
        f"# Structure: {spec.name}",
        "",
        "## Directories",
        "",
        "```",
        f"{spec.name}/",
    ]

    for d in spec.directories:
        lines.append(f"├── {d}/")

    lines.extend([
        "└── .eri-rpg/",
        "```",
        "",
        "## Key Files",
        "",
    ])

    for f in spec.key_files:
        lines.append(f"- `{f}`")

    # Write file
    path = os.path.join(output_dir, "STRUCTURE.md")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def generate_chunk_context(spec: ProjectSpec, chunk_id: str, output_dir: str) -> tuple:
    """Generate context file for a specific chunk.

    Returns: (context_path, token_estimate)
    """
    chunk = None
    for c in spec.chunks:
        if c["id"] == chunk_id:
            chunk = c
            break

    if not chunk:
        raise ValueError(f"Chunk {chunk_id} not found")

    lines = [
        f"# Build: {spec.name}",
        f"## Chunk {chunk['id']}: {chunk['name']}",
        "",
        f"**Project:** {spec.name}",
        f"**Language:** {spec.language}",
    ]

    if spec.framework:
        lines.append(f"**Framework:** {spec.framework}")

    lines.extend([
        "",
        "---",
        "",
        "## What to Build",
        "",
        chunk['description'],
        "",
        "**Creates:**",
    ])

    for item in chunk['creates']:
        lines.append(f"- {item}")

    if chunk['depends_on']:
        lines.extend([
            "",
            "**Depends on chunks:**",
        ])
        for dep in chunk['depends_on']:
            lines.append(f"- Chunk {dep}")

    lines.extend([
        "",
        "---",
        "",
        "## Project Context",
        "",
        f"**Description:** {spec.description}",
        "",
        "**Core features:**",
    ])

    for feature in spec.core_features:
        lines.append(f"- {feature}")

    if spec.constraints:
        lines.extend([
            "",
            "**Constraints:**",
        ])
        for constraint in spec.constraints:
            lines.append(f"- {constraint}")

    lines.extend([
        "",
        "---",
        "",
        "## Structure",
        "",
        "Create these directories:",
        "",
    ])

    for d in spec.directories:
        lines.append(f"- `{d}/`")

    lines.extend([
        "",
        "Key files for this chunk:",
        "",
    ])

    # Filter key files relevant to this chunk
    for f in spec.key_files:
        lines.append(f"- `{f}`")

    lines.extend([
        "",
        "---",
        "",
        "## Instructions",
        "",
        f"1. Create the directory structure for `{spec.name}/`",
        f"2. Implement: {chunk['name']}",
        "3. Follow project constraints",
        "4. Keep it minimal - only what this chunk needs",
        "",
        f"When done: `eri-rpg next`",
        "",
    ])

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"chunk_{chunk_id}_{chunk['name'].lower().replace(' ', '_')}.md"
    path = os.path.join(output_dir, filename)

    with open(path, "w") as f:
        f.write("\n".join(lines))

    tokens = len("\n".join(lines)) // 4  # Rough estimate

    return path, tokens


def create_project_skeleton(spec: ProjectSpec, base_path: str) -> str:
    """Create the actual project directory structure.

    Returns: path to project root
    """
    project_path = os.path.join(base_path, spec.name)

    # Create directories
    for d in spec.directories:
        Path(os.path.join(project_path, d)).mkdir(parents=True, exist_ok=True)

    # Create .eri-rpg directories
    Path(os.path.join(project_path, ".eri-rpg", "specs")).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(project_path, ".eri-rpg", "context")).mkdir(parents=True, exist_ok=True)

    # Create empty key files (stubs)
    for f in spec.key_files:
        file_path = os.path.join(project_path, f)
        Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)

        if not os.path.exists(file_path):
            # Create with minimal content
            if f.endswith(".py"):
                content = f'"""{os.path.basename(f)} - TODO: implement"""\n'
            elif f.endswith(".ts") or f.endswith(".tsx"):
                content = f"// {os.path.basename(f)} - TODO: implement\n"
            elif f.endswith(".rs"):
                content = f"// {os.path.basename(f)} - TODO: implement\n"
            elif f.endswith(".go"):
                content = f"// {os.path.basename(f)} - TODO: implement\npackage main\n"
            elif f.endswith(".md"):
                content = f"# {os.path.basename(f).replace('.md', '')}\n\nTODO\n"
            elif f.endswith(".json"):
                content = "{}\n"
            elif f.endswith(".toml"):
                content = "# TODO\n"
            else:
                content = ""

            with open(file_path, "w") as fp:
                fp.write(content)

    return project_path


def format_guide(
    spec: ProjectSpec,
    project_path: str,
    context_path: str,
    tokens: int,
    current_chunk: Dict,
) -> str:
    """Format the guide output for the user."""
    border = "═" * 56

    lines = [
        "",
        border,
        f"PROJECT: {spec.name}",
        "",
        f"Created: {project_path}",
        "",
        f"CHUNK {current_chunk['id']}: {current_chunk['name']}",
        f"Context file: {context_path}",
        f"Tokens: ~{tokens:,}",
        "",
        "NEXT STEPS:",
        "  1. /clear",
        f"  2. Read the context: cat {context_path}",
        "  3. Tell CC: \"Build this\"",
        "",
        "When done: eri-rpg next",
        border,
        "",
    ]

    return "\n".join(lines)


def save_new_state(spec: ProjectSpec, project_path: str, current_chunk: str):
    """Save state for resuming."""
    state_data = {
        "mode": "new",
        "project_name": spec.name,
        "project_path": project_path,
        "current_chunk": current_chunk,
        "total_chunks": len(spec.chunks),
        "spec": {
            "name": spec.name,
            "description": spec.description,
            "language": spec.language,
            "framework": spec.framework,
            "core_features": spec.core_features,
            "constraints": spec.constraints,
            "directories": spec.directories,
            "key_files": spec.key_files,
            "chunks": spec.chunks,
        }
    }

    # Save to .eri-rpg in project
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    import json
    with open(state_path, "w") as f:
        json.dump(state_data, f, indent=2)


def load_new_state(project_path: str) -> Optional[dict]:
    """Load saved new project state."""
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    if os.path.exists(state_path):
        import json
        with open(state_path) as f:
            return json.load(f)
    return None


def run_new(
    description: str,
    output_dir: Optional[str] = None,
    answers: Optional[Dict[str, str]] = None,
    verbose: bool = False,
) -> dict:
    """Run the new mode.

    Args:
        description: What to build
        output_dir: Where to create project (default: current directory)
        answers: Pre-provided answers (for non-interactive use)
        verbose: Show detailed progress

    Returns:
        dict with results including 'questions' if more input needed
    """
    registry = Registry.get_instance()
    state = State.load()

    if output_dir is None:
        output_dir = os.getcwd()

    # If no answers provided, return questions
    if answers is None:
        return {
            'success': False,
            'need_input': True,
            'questions': QUESTIONS,
            'description': description,
        }

    # Generate spec from answers
    if verbose:
        print("Generating project specification...")

    spec = generate_project_spec(answers, description)

    if verbose:
        print(f"  Name: {spec.name}")
        print(f"  Language: {spec.language}")
        print(f"  Framework: {spec.framework or 'none'}")
        print(f"  Chunks: {len(spec.chunks)}")

    # Create project skeleton
    if verbose:
        print("Creating project structure...")

    project_path = create_project_skeleton(spec, output_dir)

    if verbose:
        print(f"  Created: {project_path}")

    # Generate specs
    if verbose:
        print("Generating specifications...")

    specs_dir = os.path.join(project_path, ".eri-rpg", "specs")
    project_md = generate_project_md(spec, specs_dir)
    structure_md = generate_structure_md(spec, specs_dir)

    if verbose:
        print(f"  PROJECT.md: {project_md}")
        print(f"  STRUCTURE.md: {structure_md}")

    # Generate context for first chunk
    if verbose:
        print("Generating context for Chunk 001...")

    context_dir = os.path.join(project_path, ".eri-rpg", "context")
    context_path, tokens = generate_chunk_context(spec, "001", context_dir)

    if verbose:
        print(f"  Context: {context_path}")
        print(f"  Tokens: ~{tokens:,}")

    # Save state for resuming
    save_new_state(spec, project_path, "001")

    # Register project
    try:
        registry.add(spec.name, project_path, spec.language)
        if verbose:
            print(f"  Registered project: {spec.name}")
    except ValueError:
        # Already registered, update path
        pass

    # Update global state
    state.update(
        current_task=f"New project: {spec.name}",
        phase="building",
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("new", f"Created new project: {spec.name}")

    # Generate guide
    guide = format_guide(spec, project_path, context_path, tokens, spec.chunks[0])

    return {
        'success': True,
        'project_name': spec.name,
        'project_path': project_path,
        'spec': spec,
        'project_md': project_md,
        'structure_md': structure_md,
        'context_path': context_path,
        'tokens': tokens,
        'current_chunk': "001",
        'total_chunks': len(spec.chunks),
        'guide': guide,
    }


def run_next(project_path: Optional[str] = None, verbose: bool = False) -> dict:
    """Advance to next chunk in new project.

    Args:
        project_path: Path to project (default: current directory)
        verbose: Show detailed progress

    Returns:
        dict with results
    """
    if project_path is None:
        project_path = os.getcwd()

    # Load state
    state_data = load_new_state(project_path)

    if not state_data:
        return {
            'success': False,
            'error': "No new project state found. Are you in a project created with 'eri-rpg new'?"
        }

    current_chunk = state_data['current_chunk']
    chunks = state_data['spec']['chunks']

    # Find current chunk index
    current_idx = None
    for i, c in enumerate(chunks):
        if c['id'] == current_chunk:
            current_idx = i
            break

    if current_idx is None:
        return {'success': False, 'error': f"Chunk {current_chunk} not found"}

    # Check if done
    if current_idx >= len(chunks) - 1:
        return {
            'success': True,
            'done': True,
            'message': f"Project {state_data['project_name']} complete! All {len(chunks)} chunks built.",
        }

    # Advance to next chunk
    next_chunk = chunks[current_idx + 1]

    if verbose:
        print(f"Advancing to Chunk {next_chunk['id']}: {next_chunk['name']}")

    # Reconstruct spec
    spec = ProjectSpec(**state_data['spec'])

    # Generate context for next chunk
    context_dir = os.path.join(project_path, ".eri-rpg", "context")
    context_path, tokens = generate_chunk_context(spec, next_chunk['id'], context_dir)

    # Update saved state
    state_data['current_chunk'] = next_chunk['id']
    import json
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    with open(state_path, "w") as f:
        json.dump(state_data, f, indent=2)

    # Update global state
    state = State.load()
    state.update(
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("next", f"Advanced to chunk {next_chunk['id']}")

    # Generate guide
    guide = format_guide(spec, project_path, context_path, tokens, next_chunk)

    return {
        'success': True,
        'done': False,
        'project_name': spec.name,
        'context_path': context_path,
        'tokens': tokens,
        'current_chunk': next_chunk['id'],
        'chunk_name': next_chunk['name'],
        'remaining': len(chunks) - current_idx - 1,
        'guide': guide,
    }
```

## `erirpg/modes/take.py`

What it is: Take Mode - Transplant feature from Project A to Project B.

```python
"""
Take Mode - Transplant feature from Project A to Project B.

Usage:
    eri-rpg take "masked_loss from onetrainer into eritrainer"
    eri-rpg take "gradient checkpointing from onetrainer"  # into current project

Flow:
    1. Parse - understand source, feature, target
    2. Check - are projects registered/indexed?
    3. Find - locate feature in source
    4. Learn - read source or use knowledge
    5. Spec - generate TRANSPLANT.md
    6. Context - generate context for CC
    7. Guide - tell user what to do next
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from erirpg.registry import Registry
from erirpg.indexer import get_or_load_graph
from erirpg.graph import Graph
from erirpg.ops import find_modules, extract_feature, plan_transplant, Feature, TransplantPlan
from erirpg.context import generate_context, estimate_tokens
from erirpg.state import State


@dataclass
class TakeRequest:
    """Parsed take command."""
    feature: str
    source_project: str
    target_project: Optional[str]


def parse_take_request(description: str) -> TakeRequest:
    """Parse natural language take request.

    Patterns:
        "X from A into B"
        "X from A to B"
        "X from A"  (target is current project)
    """
    description = description.strip()

    # Pattern: "X from A into/to B"
    match = re.match(
        r"(.+?)\s+from\s+(\w+)\s+(?:into|to)\s+(\w+)",
        description,
        re.IGNORECASE
    )
    if match:
        return TakeRequest(
            feature=match.group(1).strip(),
            source_project=match.group(2).strip(),
            target_project=match.group(3).strip(),
        )

    # Pattern: "X from A"
    match = re.match(
        r"(.+?)\s+from\s+(\w+)$",
        description,
        re.IGNORECASE
    )
    if match:
        return TakeRequest(
            feature=match.group(1).strip(),
            source_project=match.group(2).strip(),
            target_project=None,
        )

    raise ValueError(
        f"Cannot parse: {description}\n"
        f"Expected: '<feature> from <source> into <target>' or '<feature> from <source>'"
    )


def check_projects(
    request: TakeRequest,
    registry: Registry,
) -> Tuple[str, str, str, str]:
    """Check projects exist and are indexed.

    Returns: (source_name, source_path, target_name, target_path)
    Raises: ValueError with helpful message if something's wrong
    """
    # Check source
    source = registry.get(request.source_project)
    if not source:
        available = [p.name for p in registry.list()]
        raise ValueError(
            f"Source project '{request.source_project}' not found.\n"
            f"Available: {', '.join(available) if available else 'none'}\n"
            f"Add it: eri-rpg add {request.source_project} /path/to/{request.source_project}"
        )

    if not source.is_indexed():
        raise ValueError(
            f"Source project '{request.source_project}' not indexed.\n"
            f"Run: eri-rpg index {request.source_project}"
        )

    # Determine target
    if request.target_project:
        target = registry.get(request.target_project)
        if not target:
            available = [p.name for p in registry.list()]
            raise ValueError(
                f"Target project '{request.target_project}' not found.\n"
                f"Available: {', '.join(available) if available else 'none'}\n"
                f"Add it: eri-rpg add {request.target_project} /path/to/{request.target_project}"
            )
        target_name = request.target_project
    else:
        # Use current directory as target
        cwd = os.getcwd()
        target = None
        for p in registry.list():
            if os.path.samefile(p.path, cwd):
                target = p
                break

        if not target:
            raise ValueError(
                f"No target specified and current directory is not a registered project.\n"
                f"Either specify target: eri-rpg take \"{request.feature} from {request.source_project} into <target>\"\n"
                f"Or register current directory: eri-rpg add <name> ."
            )
        target_name = target.name

    if not target.is_indexed():
        raise ValueError(
            f"Target project '{target_name}' not indexed.\n"
            f"Run: eri-rpg index {target_name}"
        )

    return source.name, source.path, target_name, target.path


def find_feature(
    graph: Graph,
    feature_query: str,
    project_name: str,
) -> list:
    """Find modules matching feature query.

    Returns list of (module, score) tuples.
    """
    results = find_modules(graph, feature_query, limit=10)

    if not results:
        raise ValueError(
            f"No modules matching '{feature_query}' in {project_name}.\n"
            f"Try: eri-rpg show {project_name}\n"
            f"Or: eri-rpg find {project_name} \"<broader query>\""
        )

    return results


def check_knowledge(graph: Graph, modules: list) -> dict:
    """Check what knowledge exists for these modules.

    Returns: {
        'have_knowledge': [(path, learning), ...],
        'need_to_learn': [path, ...],
    }
    """
    have = []
    need = []

    for mod, _score in modules:
        learning = graph.knowledge.get_learning(mod.path)
        if learning:
            have.append((mod.path, learning))
        else:
            need.append(mod.path)

    return {
        'have_knowledge': have,
        'need_to_learn': need,
    }


def generate_transplant_spec(
    feature: Feature,
    plan: TransplantPlan,
    source_graph: Graph,
    target_name: str,
    output_dir: str,
) -> str:
    """Generate TRANSPLANT.md spec file.

    Returns path to spec file.
    """
    lines = []

    # Header
    lines.append(f"# Transplant: {feature.name}")
    lines.append("")
    lines.append(f"**From:** {feature.source_project}")
    lines.append(f"**To:** {target_name}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Feature summary
    lines.append("## Feature Summary")
    lines.append("")
    for comp_path in feature.components:
        learning = source_graph.knowledge.get_learning(comp_path) if source_graph else None
        if learning:
            lines.append(f"### {comp_path}")
            lines.append(f"**Summary:** {learning.summary}")
            lines.append(f"**Purpose:** {learning.purpose}")
            if learning.gotchas:
                lines.append("**Gotchas:**")
                for g in learning.gotchas:
                    lines.append(f"- {g}")
            lines.append("")
        else:
            lines.append(f"### {comp_path}")
            lines.append("*(No stored knowledge - will include source)*")
            lines.append("")

    # Mappings
    lines.append("## Mappings")
    lines.append("")
    lines.append("| Source | Target | Action | Notes |")
    lines.append("|--------|--------|--------|-------|")
    for m in plan.mappings:
        source = m.source_interface
        target = m.target_interface or "NEW"
        lines.append(f"| `{source}` | `{target}` | {m.action} | {m.notes} |")
    lines.append("")

    # Wiring
    if plan.wiring:
        lines.append("## Wiring")
        lines.append("")
        for w in plan.wiring:
            lines.append(f"- **{w.file}**: {w.action} - {w.details}")
        lines.append("")

    # Implementation order
    lines.append("## Implementation Order")
    lines.append("")
    for i, path in enumerate(plan.generation_order, 1):
        lines.append(f"{i}. `{path}`")
    lines.append("")

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    spec_path = os.path.join(output_dir, f"{feature.name.lower().replace(' ', '_')}_transplant.md")

    with open(spec_path, "w") as f:
        f.write("\n".join(lines))

    return spec_path


def format_guide(
    feature_name: str,
    source_name: str,
    target_name: str,
    context_path: str,
    tokens: int,
    tokens_saved: int,
) -> str:
    """Format the guide output for the user."""
    border = "═" * 56

    lines = [
        "",
        border,
        f"TRANSPLANT: {feature_name}",
        f"FROM: {source_name} → TO: {target_name}",
        "",
        f"Context file: {context_path}",
        f"Tokens: ~{tokens:,}",
    ]

    if tokens_saved > 0:
        lines.append(f"Saved: ~{tokens_saved:,} tokens (using stored knowledge)")

    lines.extend([
        "",
        "NEXT STEPS:",
        "  1. /clear",
        f"  2. Read the context: cat {context_path}",
        "  3. Tell CC: \"Implement this\"",
        "",
        "When done: eri-rpg validate",
        border,
        "",
    ])

    return "\n".join(lines)


def run_take(description: str, verbose: bool = False) -> dict:
    """Run the take mode.

    Args:
        description: Natural language description like "X from A into B"
        verbose: Show detailed progress

    Returns:
        dict with results: {
            'success': bool,
            'feature_name': str,
            'context_path': str,
            'spec_path': str,
            'tokens': int,
            'guide': str,
            'error': str (if not success),
        }
    """
    registry = Registry.get_instance()
    state = State.load()

    # 1. Parse
    if verbose:
        print("Parsing request...")

    try:
        request = parse_take_request(description)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if verbose:
        print(f"  Feature: {request.feature}")
        print(f"  Source: {request.source_project}")
        print(f"  Target: {request.target_project or '(current project)'}")

    # 2. Check projects
    if verbose:
        print("Checking projects...")

    try:
        source_name, source_path, target_name, target_path = check_projects(request, registry)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    # 3. Load graphs
    if verbose:
        print("Loading project graphs...")

    source_proj = registry.get(source_name)
    target_proj = registry.get(target_name)

    try:
        source_graph = get_or_load_graph(source_proj)
        target_graph = get_or_load_graph(target_proj)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    # 4. Find feature
    if verbose:
        print(f"Finding '{request.feature}' in {source_name}...")

    try:
        results = find_feature(source_graph, request.feature, source_name)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if verbose:
        print(f"  Found {len(results)} matching modules:")
        for mod, score in results[:5]:
            print(f"    - {mod.path} ({score:.2f})")

    # 5. Check knowledge
    knowledge_status = check_knowledge(source_graph, results)

    if verbose:
        have = len(knowledge_status['have_knowledge'])
        need = len(knowledge_status['need_to_learn'])
        print(f"Knowledge: {have} modules known, {need} need learning")

    # 6. Extract feature
    if verbose:
        print("Extracting feature...")

    feature_name = request.feature.replace(" ", "_")
    feature = extract_feature(source_graph, source_proj, request.feature, feature_name)

    # 7. Plan transplant
    if verbose:
        print("Planning transplant...")

    plan = plan_transplant(feature, target_graph, target_proj)

    # 8. Generate spec
    spec_dir = os.path.join(target_path, ".eri-rpg", "specs")
    spec_path = generate_transplant_spec(feature, plan, source_graph, target_name, spec_dir)

    if verbose:
        print(f"  Spec: {spec_path}")

    # 9. Generate context
    if verbose:
        print("Generating context...")

    context_path = generate_context(
        feature, plan, source_graph, target_graph, target_proj,
        use_learnings=True
    )

    tokens = estimate_tokens(feature, plan)

    # Estimate tokens saved
    tokens_saved = 0
    for path, _learning in knowledge_status['have_knowledge']:
        # Rough estimate: ~1500 tokens saved per learning
        tokens_saved += 1500

    if verbose:
        print(f"  Context: {context_path}")
        print(f"  Tokens: ~{tokens:,}")

    # 10. Update state
    state.update(
        current_task=f"Transplant {feature_name} from {source_name} to {target_name}",
        phase="context_ready",
        feature_file=None,
        plan_file=None,
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("take", f"Prepared transplant: {feature_name} from {source_name} to {target_name}")

    # 11. Generate guide
    guide = format_guide(
        feature_name=feature_name,
        source_name=source_name,
        target_name=target_name,
        context_path=context_path,
        tokens=tokens,
        tokens_saved=tokens_saved,
    )

    return {
        'success': True,
        'feature_name': feature_name,
        'source': source_name,
        'target': target_name,
        'spec_path': spec_path,
        'context_path': context_path,
        'tokens': tokens,
        'tokens_saved': tokens_saved,
        'guide': guide,
        'knowledge_status': knowledge_status,
    }
```

## `erirpg/modes/work.py`

What it is: Work Mode - Modify existing project.

```python
"""
Work Mode - Modify existing project.

Usage:
    eri-rpg work eritrainer "add dark mode to settings"
    eri-rpg work "fix the memory leak in dataloader"  # current project

Flow:
    1. Parse - understand project + task
    2. Check - is project indexed?
    3. Find - what code is relevant?
    4. Recall - load existing knowledge
    5. Spec - generate TASK.md
    6. Context - generate context for CC
    7. Guide - tell user what to do next
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

from erirpg.registry import Registry
from erirpg.indexer import get_or_load_graph
from erirpg.graph import Graph, Module
from erirpg.ops import find_modules
from erirpg.state import State


@dataclass
class WorkRequest:
    """Parsed work command."""
    project: Optional[str]
    task: str


def parse_work_request(project: Optional[str], task: str) -> WorkRequest:
    """Parse work request."""
    return WorkRequest(project=project, task=task.strip())


def resolve_project(request: WorkRequest, registry: Registry) -> Tuple[str, str]:
    """Resolve which project to work on.

    Returns: (project_name, project_path)
    """
    if request.project:
        proj = registry.get(request.project)
        if not proj:
            available = [p.name for p in registry.list()]
            raise ValueError(
                f"Project '{request.project}' not found.\n"
                f"Available: {', '.join(available) if available else 'none'}\n"
                f"Add it: eri-rpg add {request.project} /path/to/project"
            )
        return proj.name, proj.path

    # Try current directory
    cwd = os.getcwd()
    for p in registry.list():
        try:
            if os.path.samefile(p.path, cwd):
                return p.name, p.path
        except OSError:
            continue

    # Try parent directories
    for p in registry.list():
        try:
            if cwd.startswith(os.path.realpath(p.path)):
                return p.name, p.path
        except OSError:
            continue

    raise ValueError(
        f"No project specified and current directory is not a registered project.\n"
        f"Either specify: eri-rpg work <project> \"{request.task}\"\n"
        f"Or register current directory: eri-rpg add <name> ."
    )


def find_relevant_modules(
    graph: Graph,
    task: str,
    limit: int = 10,
) -> List[Tuple[Module, float]]:
    """Find modules relevant to the task.

    Searches by task keywords in module summaries, interfaces, docstrings.
    """
    results = find_modules(graph, task, limit=limit)
    return results


def gather_knowledge(
    graph: Graph,
    modules: List[Tuple[Module, float]],
) -> dict:
    """Gather existing knowledge about relevant modules.

    Returns: {
        'known': [(path, learning), ...],
        'unknown': [path, ...],
        'patterns': [(name, desc), ...],
        'decisions': [decision, ...],
    }
    """
    known = []
    unknown = []

    for mod, _score in modules:
        learning = graph.knowledge.get_learning(mod.path)
        if learning:
            known.append((mod.path, learning))
        else:
            unknown.append(mod.path)

    # Get all patterns
    patterns = list(graph.knowledge.patterns.items())

    # Get decisions affecting these modules
    decisions = []
    module_paths = [m.path for m, _ in modules]
    for decision in graph.knowledge.decisions:
        if any(path in decision.affects for path in module_paths):
            decisions.append(decision)

    return {
        'known': known,
        'unknown': unknown,
        'patterns': patterns,
        'decisions': decisions,
    }


def generate_task_spec(
    project_name: str,
    task: str,
    modules: List[Tuple[Module, float]],
    knowledge: dict,
    output_dir: str,
) -> str:
    """Generate TASK.md spec file."""
    lines = []

    # Header
    lines.append(f"# Task: {task}")
    lines.append("")
    lines.append(f"**Project:** {project_name}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Relevant modules
    lines.append("## Relevant Modules")
    lines.append("")
    for mod, score in modules:
        status = "✓ knowledge" if any(p == mod.path for p, _ in knowledge['known']) else "○ needs reading"
        lines.append(f"- `{mod.path}` ({score:.2f}) [{status}]")
        if mod.summary:
            lines.append(f"  {mod.summary}")
    lines.append("")

    # Existing knowledge
    if knowledge['known']:
        lines.append("## Existing Knowledge")
        lines.append("")
        for path, learning in knowledge['known']:
            lines.append(f"### {path}")
            lines.append(f"**Summary:** {learning.summary}")
            if learning.gotchas:
                lines.append("**Gotchas:**")
                for g in learning.gotchas:
                    lines.append(f"- {g}")
            lines.append("")

    # Patterns to follow
    if knowledge['patterns']:
        lines.append("## Patterns")
        lines.append("")
        for name, desc in knowledge['patterns']:
            lines.append(f"- **{name}:** {desc}")
        lines.append("")

    # Relevant decisions
    if knowledge['decisions']:
        lines.append("## Relevant Decisions")
        lines.append("")
        for d in knowledge['decisions']:
            lines.append(f"- **{d.title}:** {d.reason}")
        lines.append("")

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    task_slug = task.lower().replace(" ", "_")[:40]
    spec_path = os.path.join(output_dir, f"task_{task_slug}.md")

    with open(spec_path, "w") as f:
        f.write("\n".join(lines))

    return spec_path


def generate_work_context(
    project_name: str,
    project_path: str,
    task: str,
    modules: List[Tuple[Module, float]],
    knowledge: dict,
    graph: Graph,
    output_dir: str,
) -> Tuple[str, int]:
    """Generate context file for CC.

    Returns: (context_path, token_estimate)
    """
    lines = []

    # Header
    lines.append(f"# Work: {task}")
    lines.append("")
    lines.append(f"**Project:** {project_name}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Task description
    lines.append("## Task")
    lines.append("")
    lines.append(task)
    lines.append("")

    # Relevant code
    lines.append("---")
    lines.append("")
    lines.append("## Relevant Code")
    lines.append("")

    tokens = 200  # Base tokens for structure

    for mod, score in modules:
        lines.append(f"### `{mod.path}`")
        lines.append("")

        # Check for stored learning
        learning = graph.knowledge.get_learning(mod.path)

        if learning:
            # Use learning instead of source
            lines.append(f"**Summary:** {learning.summary}")
            lines.append("")
            lines.append(f"**Purpose:** {learning.purpose}")
            lines.append("")

            if learning.key_functions:
                lines.append("**Key Functions:**")
                for name, desc in learning.key_functions.items():
                    lines.append(f"- `{name}`: {desc}")
                lines.append("")

            if learning.gotchas:
                lines.append("**Gotchas:**")
                for g in learning.gotchas:
                    lines.append(f"- {g}")
                lines.append("")

            lines.append("*[Using stored knowledge]*")
            lines.append("")
            tokens += 150  # Estimate for learning
        else:
            # Include source code
            source_path = os.path.join(project_path, mod.path)
            if os.path.exists(source_path):
                with open(source_path) as f:
                    code = f.read()
                lines.append("```python")
                lines.append(code.strip())
                lines.append("```")
                lines.append("")
                lines.append(f"After understanding, store: `eri-rpg learn {project_name} {mod.path}`")
                lines.append("")
                tokens += len(code) // 4  # Rough token estimate
            else:
                lines.append("*(Source file not found)*")
                lines.append("")

    # Patterns
    if knowledge['patterns']:
        lines.append("---")
        lines.append("")
        lines.append("## Patterns to Follow")
        lines.append("")
        for name, desc in knowledge['patterns']:
            lines.append(f"- **{name}:** {desc}")
        lines.append("")
        tokens += 50

    # Decisions
    if knowledge['decisions']:
        lines.append("---")
        lines.append("")
        lines.append("## Relevant Decisions")
        lines.append("")
        for d in knowledge['decisions']:
            lines.append(f"- **{d.title}:** {d.reason}")
        lines.append("")
        tokens += 50

    # Instructions
    lines.append("---")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append(f"1. **Understand** the relevant code above")
    lines.append(f"2. **Implement** the task: {task}")
    lines.append("3. **Follow** existing patterns and decisions")
    lines.append("4. **Test** the changes work correctly")
    lines.append("")
    lines.append("When done: `eri-rpg done`")
    lines.append("")

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    task_slug = task.lower().replace(" ", "_")[:40]
    context_path = os.path.join(output_dir, f"work_{task_slug}.md")

    with open(context_path, "w") as f:
        f.write("\n".join(lines))

    return context_path, tokens


def format_guide(
    project_name: str,
    task: str,
    modules: List[Tuple[Module, float]],
    knowledge: dict,
    context_path: str,
    tokens: int,
) -> str:
    """Format the guide output for the user."""
    border = "═" * 56

    lines = [
        "",
        border,
        f"WORK: {project_name}",
        f"TASK: {task}",
        "",
        "Relevant modules:",
    ]

    for mod, _ in modules[:5]:
        status = "knowledge" if any(p == mod.path for p, _ in knowledge['known']) else "source"
        lines.append(f"  - {mod.path} ({status})")

    if len(modules) > 5:
        lines.append(f"  ... and {len(modules) - 5} more")

    lines.extend([
        "",
        f"Context file: {context_path}",
        f"Tokens: ~{tokens:,}",
        "",
        "NEXT STEPS:",
        "  1. /clear",
        f"  2. Read the context: cat {context_path}",
        f"  3. Tell CC: \"{task}\"",
        "",
        "When done: eri-rpg done",
        border,
        "",
    ])

    return "\n".join(lines)


def run_work(
    project: Optional[str],
    task: str,
    verbose: bool = False,
) -> dict:
    """Run the work mode.

    Args:
        project: Project name (or None for current directory)
        task: What to do
        verbose: Show detailed progress

    Returns:
        dict with results
    """
    registry = Registry.get_instance()
    state = State.load()

    # 1. Parse
    if verbose:
        print("Parsing request...")

    request = parse_work_request(project, task)

    # 2. Resolve project
    if verbose:
        print("Resolving project...")

    try:
        project_name, project_path = resolve_project(request, registry)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if verbose:
        print(f"  Project: {project_name}")
        print(f"  Path: {project_path}")

    # 3. Load graph
    if verbose:
        print("Loading project graph...")

    proj = registry.get(project_name)

    if not proj.is_indexed():
        return {
            'success': False,
            'error': f"Project '{project_name}' not indexed.\nRun: eri-rpg index {project_name}"
        }

    try:
        graph = get_or_load_graph(proj)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    # 4. Find relevant modules
    if verbose:
        print(f"Finding relevant modules for: {task}")

    modules = find_relevant_modules(graph, task, limit=10)

    if not modules:
        return {
            'success': False,
            'error': f"No modules found matching '{task}'.\n"
                     f"Try: eri-rpg show {project_name}\n"
                     f"Or: eri-rpg find {project_name} \"<keyword>\""
        }

    if verbose:
        print(f"  Found {len(modules)} relevant modules")
        for mod, score in modules[:5]:
            print(f"    - {mod.path} ({score:.2f})")

    # 5. Gather knowledge
    if verbose:
        print("Gathering existing knowledge...")

    knowledge = gather_knowledge(graph, modules)

    if verbose:
        print(f"  Known: {len(knowledge['known'])} modules")
        print(f"  Unknown: {len(knowledge['unknown'])} modules")
        print(f"  Patterns: {len(knowledge['patterns'])}")

    # 6. Generate spec
    spec_dir = os.path.join(project_path, ".eri-rpg", "specs")
    spec_path = generate_task_spec(project_name, task, modules, knowledge, spec_dir)

    if verbose:
        print(f"  Spec: {spec_path}")

    # 7. Generate context
    if verbose:
        print("Generating context...")

    context_dir = os.path.join(project_path, ".eri-rpg", "context")
    context_path, tokens = generate_work_context(
        project_name, project_path, task, modules, knowledge, graph, context_dir
    )

    if verbose:
        print(f"  Context: {context_path}")
        print(f"  Tokens: ~{tokens:,}")

    # 8. Update state
    state.update(
        current_task=f"Work on {project_name}: {task}",
        phase="context_ready",
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("work", f"Started work: {task} in {project_name}")

    # 9. Generate guide
    guide = format_guide(project_name, task, modules, knowledge, context_path, tokens)

    return {
        'success': True,
        'project': project_name,
        'task': task,
        'spec_path': spec_path,
        'context_path': context_path,
        'tokens': tokens,
        'modules': [(m.path, s) for m, s in modules],
        'knowledge': knowledge,
        'guide': guide,
    }
```

## `erirpg/ops.py`

What it is: Core operations: find, extract, impact, plan.

```python
"""
Core operations: find, extract, impact, plan.

These operations work on indexed graphs to:
- Find modules matching capabilities
- Extract features as self-contained units
- Analyze impact of changes
- Plan transplants between projects
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Union
import json
import os
import re

from erirpg.graph import Graph, Module, Interface
from erirpg.registry import Project
from erirpg.refs import CodeRef


@dataclass
class Feature:
    """An extracted feature - self-contained unit of code.

    Features can store code in two ways:
    1. As CodeRefs (default): References to code locations, hydrated on demand
    2. As snapshots (--snapshot flag): Full code content for offline use

    Attributes:
        name: Feature name
        source_project: Source project name
        extracted_at: When the feature was extracted
        components: List of module paths in dependency order
        requires: External packages/interfaces needed
        provides: Interfaces exported by this feature
        code_refs: Dict of path -> CodeRef (reference-based storage)
        code_snapshots: Dict of path -> str (snapshot-based storage)
    """
    name: str
    source_project: str
    extracted_at: datetime = field(default_factory=datetime.now)
    components: List[str] = field(default_factory=list)  # Module paths
    requires: List[Dict] = field(default_factory=list)  # External interfaces needed
    provides: List[Dict] = field(default_factory=list)  # Interfaces exported
    code_refs: Dict[str, CodeRef] = field(default_factory=dict)  # path -> CodeRef
    code_snapshots: Dict[str, str] = field(default_factory=dict)  # path -> code (for backwards compat)

    # Backward compatibility property
    @property
    def code(self) -> Dict[str, str]:
        """Get code dict (for backward compatibility).

        Returns snapshots if available, otherwise empty dict.
        Use hydrate_code() to get fresh code from refs.
        """
        return self.code_snapshots

    @code.setter
    def code(self, value: Dict[str, str]) -> None:
        """Set code snapshots (for backward compatibility)."""
        self.code_snapshots = value

    def hydrate_code(self, project_path: str, component: Optional[str] = None) -> Dict[str, str]:
        """Load fresh code from refs.

        Args:
            project_path: Root path of the source project
            component: If specified, only hydrate this component

        Returns:
            Dict of path -> code content
        """
        result = {}

        if component:
            # Hydrate single component
            if component in self.code_refs:
                result[component] = self.code_refs[component].hydrate(project_path)
            elif component in self.code_snapshots:
                result[component] = self.code_snapshots[component]
        else:
            # Hydrate all components
            for path in self.components:
                if path in self.code_refs:
                    try:
                        result[path] = self.code_refs[path].hydrate(project_path)
                    except FileNotFoundError:
                        # Fall back to snapshot if available
                        if path in self.code_snapshots:
                            result[path] = self.code_snapshots[path]
                elif path in self.code_snapshots:
                    result[path] = self.code_snapshots[path]

        return result

    def get_stale_components(self, project_path: str) -> List[str]:
        """Get components whose source files have changed.

        Args:
            project_path: Root path of the source project

        Returns:
            List of component paths that are stale
        """
        stale = []
        for path, ref in self.code_refs.items():
            if ref.is_stale(project_path):
                stale.append(path)
        return stale

    def save(self, path: str) -> None:
        """Save feature to JSON file."""
        data = {
            "name": self.name,
            "source_project": self.source_project,
            "extracted_at": self.extracted_at.isoformat(),
            "components": self.components,
            "requires": self.requires,
            "provides": self.provides,
            "code_refs": {k: v.to_dict() for k, v in self.code_refs.items()},
        }
        # Include snapshots if present (for --snapshot mode or backward compat)
        if self.code_snapshots:
            data["code"] = self.code_snapshots
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Feature":
        """Load feature from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        # Load code_refs if present (v2 format)
        code_refs = {}
        if "code_refs" in data:
            code_refs = {k: CodeRef.from_dict(v) for k, v in data["code_refs"].items()}

        # Load code snapshots if present (v1 format or --snapshot)
        code_snapshots = data.get("code", {})

        return cls(
            name=data["name"],
            source_project=data["source_project"],
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            components=data["components"],
            requires=data["requires"],
            provides=data["provides"],
            code_refs=code_refs,
            code_snapshots=code_snapshots,
        )


@dataclass
class Mapping:
    """A mapping between source and target module/interface."""
    source_module: str
    source_interface: str
    target_module: Optional[str]  # None = CREATE
    target_interface: Optional[str]  # None = CREATE
    action: str  # "ADAPT" | "CREATE" | "SKIP"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_module": self.source_module,
            "source_interface": self.source_interface,
            "target_module": self.target_module,
            "target_interface": self.target_interface,
            "action": self.action,
            "notes": self.notes,
        }


@dataclass
class WiringTask:
    """A wiring task for transplant."""
    file: str
    action: str
    details: str

    def to_dict(self) -> dict:
        return {"file": self.file, "action": self.action, "details": self.details}


@dataclass
class TransplantPlan:
    """Plan for transplanting a feature to a target project."""
    feature_name: str
    source_project: str
    target_project: str
    mappings: List[Mapping] = field(default_factory=list)
    wiring: List[WiringTask] = field(default_factory=list)
    generation_order: List[str] = field(default_factory=list)

    def save(self, path: str) -> None:
        """Save plan to JSON file."""
        data = {
            "feature_name": self.feature_name,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "mappings": [m.to_dict() for m in self.mappings],
            "wiring": [w.to_dict() for w in self.wiring],
            "generation_order": self.generation_order,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TransplantPlan":
        """Load plan from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(
            feature_name=data["feature_name"],
            source_project=data["source_project"],
            target_project=data["target_project"],
            mappings=[Mapping(**m) for m in data["mappings"]],
            wiring=[WiringTask(**w) for w in data["wiring"]],
            generation_order=data["generation_order"],
        )


def find_modules(
    graph: Graph,
    query: str,
    limit: int = 10,
) -> List[Tuple[Module, float]]:
    """Find modules matching a query.

    Uses simple token-based scoring:
    - Summary match: 0.5 weight
    - Interface names: 0.3 weight
    - Docstrings: 0.2 weight

    Args:
        graph: Project graph
        query: Search query
        limit: Maximum results

    Returns:
        List of (Module, score) tuples, sorted by score descending
    """
    query_tokens = _tokenize(query.lower())

    results = []
    for mod in graph.modules.values():
        score = 0.0

        # Summary match (0.5 weight)
        summary_tokens = _tokenize(mod.summary.lower())
        summary_score = _jaccard(query_tokens, summary_tokens)
        score += summary_score * 0.5

        # Interface names (0.3 weight)
        iface_names = " ".join(i.name for i in mod.interfaces)
        iface_tokens = _tokenize(iface_names.lower())
        iface_score = _jaccard(query_tokens, iface_tokens)
        score += iface_score * 0.3

        # Docstrings (0.2 weight)
        docstrings = " ".join(i.docstring for i in mod.interfaces)
        doc_tokens = _tokenize(docstrings.lower())
        doc_score = _jaccard(query_tokens, doc_tokens)
        score += doc_score * 0.2

        # Boost for exact phrase in summary
        if query.lower() in mod.summary.lower():
            score += 0.3

        # Boost for path match
        path_tokens = _tokenize(mod.path.lower().replace("/", " ").replace("_", " "))
        if query_tokens & path_tokens:
            score += 0.1

        if score > 0:
            results.append((mod, score))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into words."""
    return set(re.findall(r'\w+', text))


def _jaccard(set1: Set[str], set2: Set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def extract_feature(
    graph: Graph,
    project: Project,
    query: str,
    feature_name: str,
    snapshot: bool = False,
) -> Feature:
    """Extract a feature from a project.

    Finds matching modules, includes transitive dependencies,
    and packages as a Feature with code references (or snapshots).

    Args:
        graph: Project graph
        project: Project (for reading files)
        query: Search query
        feature_name: Name for the feature
        snapshot: If True, store full code instead of refs (for offline use)

    Returns:
        Extracted Feature
    """
    # Find matching modules
    matches = find_modules(graph, query, limit=5)
    if not matches:
        raise ValueError(f"No modules match query: {query}")

    # Take top match and its dependencies
    primary = matches[0][0]
    deps = graph.get_transitive_deps(primary.path)

    # Include primary + deps
    components = [primary.path] + list(deps)

    # Topo sort for correct order
    ordered = graph.topo_sort(components)

    # Create code refs (and optionally snapshots)
    code_refs = {}
    code_snapshots = {}
    for comp in ordered:
        file_path = os.path.join(project.path, comp)
        if os.path.exists(file_path):
            # Always create CodeRef for freshness tracking
            try:
                code_refs[comp] = CodeRef.from_file(project.path, comp)
            except Exception:
                pass  # Skip if can't create ref

            # Optionally include full code snapshot
            if snapshot:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code_snapshots[comp] = f.read()

    # Extract requires (external deps)
    requires = []
    external_seen = set()
    for comp in ordered:
        mod = graph.get_module(comp)
        if mod:
            for ext in mod.deps_external:
                if ext not in external_seen:
                    external_seen.add(ext)
                    requires.append({"package": ext})

    # Extract provides (interfaces from primary)
    provides = []
    for iface in primary.interfaces:
        provides.append({
            "name": iface.name,
            "type": iface.type,
            "signature": iface.signature,
        })

    return Feature(
        name=feature_name,
        source_project=project.name,
        components=ordered,
        requires=requires,
        provides=provides,
        code_refs=code_refs,
        code_snapshots=code_snapshots,
    )


def analyze_impact(
    graph: Graph,
    module_path: str,
) -> Dict:
    """Analyze impact of changing a module.

    Args:
        graph: Project graph
        module_path: Module to analyze

    Returns:
        Dict with direct_dependents, transitive_dependents, risk level
    """
    module = graph.get_module(module_path)
    if not module:
        raise ValueError(f"Module not found: {module_path}")

    # Get dependents
    direct = graph.get_dependents(module_path)
    transitive = graph.get_transitive_dependents(module_path)
    transitive_only = [d for d in transitive if d not in direct]

    # Assess risk
    total = len(transitive)
    if total > 5:
        risk = "HIGH"
    elif total >= 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "module": module_path,
        "summary": module.summary,
        "interfaces": [i.name for i in module.interfaces],
        "direct_dependents": direct,
        "transitive_dependents": transitive_only,
        "total_affected": total,
        "risk": risk,
    }


def plan_transplant(
    feature: Feature,
    target_graph: Graph,
    target_project: Project,
) -> TransplantPlan:
    """Plan how to transplant a feature to a target project.

    Args:
        feature: Feature to transplant
        target_graph: Target project's graph
        target_project: Target project

    Returns:
        TransplantPlan with mappings and wiring
    """
    plan = TransplantPlan(
        feature_name=feature.name,
        source_project=feature.source_project,
        target_project=target_project.name,
    )

    # Build target interface index
    target_interfaces = {}
    for mod in target_graph.modules.values():
        for iface in mod.interfaces:
            target_interfaces[iface.name.lower()] = (mod.path, iface.name)

    # Create mappings for each provided interface
    for provided in feature.provides:
        name = provided["name"]
        name_lower = name.lower()

        if name_lower in target_interfaces:
            # Interface exists - ADAPT
            target_mod, target_iface = target_interfaces[name_lower]
            plan.mappings.append(Mapping(
                source_module=feature.components[0],  # Primary component
                source_interface=name,
                target_module=target_mod,
                target_interface=target_iface,
                action="ADAPT",
                notes=f"Existing {target_iface} in {target_mod}",
            ))
        else:
            # Interface doesn't exist - CREATE
            # Suggest a path based on source path
            suggested_path = _suggest_target_path(feature.components[0], target_project)
            plan.mappings.append(Mapping(
                source_module=feature.components[0],
                source_interface=name,
                target_module=None,
                target_interface=None,
                action="CREATE",
                notes=f"Suggested path: {suggested_path}",
            ))

    # Check required packages
    for req in feature.requires:
        pkg = req["package"]
        # Check if any target module uses this package
        pkg_used = any(
            pkg in mod.deps_external
            for mod in target_graph.modules.values()
        )
        if not pkg_used:
            plan.wiring.append(WiringTask(
                file="requirements.txt or pyproject.toml",
                action="add_dependency",
                details=f"Add {pkg} to dependencies",
            ))

    # Compute generation order
    plan.generation_order = feature.components

    return plan


def _suggest_target_path(source_path: str, target_project: Project) -> str:
    """Suggest a target path for a new module."""
    # Simple heuristic: use filename in a logical location
    filename = os.path.basename(source_path)
    # Could be smarter based on target project structure
    return f"<appropriate_dir>/{filename}"
```

## `erirpg/parsers/__init__.py`

What it is: Language-specific parsers for code analysis.

```python
"""
Language-specific parsers for code analysis.

Each parser extracts:
- Imports/dependencies
- Interfaces (classes, functions, exports)
- Module docstrings/summaries

Supported languages:
- Python (.py) - uses stdlib ast
- C/C++ (.c, .h, .cpp, .hpp) - regex-based
- Rust (.rs) - regex-based
"""

from erirpg.parsers.python import parse_python_file, resolve_import_to_module
from erirpg.parsers.c import parse_c_file, resolve_include_to_module
from erirpg.parsers.rust import parse_rust_file, resolve_use_to_module, classify_external_crate

__all__ = [
    "parse_python_file",
    "resolve_import_to_module",
    "parse_c_file",
    "resolve_include_to_module",
    "parse_rust_file",
    "resolve_use_to_module",
    "classify_external_crate",
]


def get_parser_for_file(path: str):
    """Get appropriate parser function for a file path.

    Returns:
        Parser function or None if unsupported
    """
    if path.endswith(".py"):
        return parse_python_file
    elif path.endswith((".c", ".h", ".cpp", ".hpp", ".cc", ".hh")):
        return parse_c_file
    elif path.endswith(".rs"):
        return parse_rust_file
    return None


def detect_language(path: str) -> str:
    """Detect language from file extension.

    Returns:
        Language string: 'python', 'c', 'rust', or 'unknown'
    """
    if path.endswith(".py"):
        return "python"
    elif path.endswith((".c", ".h", ".cpp", ".hpp", ".cc", ".hh")):
        return "c"
    elif path.endswith(".rs"):
        return "rust"
    return "unknown"
```

## `erirpg/parsers/c.py`

What it is: C/C++ parser using regex (no external deps).

```python
"""
C/C++ parser using regex (no external deps).

Extracts:
- #include statements (for dependencies)
- Function definitions (for interfaces)
- Struct/typedef definitions (for interfaces)
- Macro definitions (for interfaces)
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_c_file(path: str) -> Dict[str, Any]:
    """Parse C/C++ file, extract interfaces and includes.

    Args:
        path: Path to .c/.h/.cpp/.hpp file

    Returns:
        Dict with keys:
        - docstring: First block comment or empty
        - imports: List of include dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    result = {
        "docstring": _extract_file_comment(source),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    # Extract includes
    for match in re.finditer(r'#include\s*[<"]([^>"]+)[>"]', source):
        include = match.group(1)
        result["imports"].append({
            "type": "include",
            "name": include,
            "is_system": "<" in match.group(0),
        })

    # Extract function definitions (not declarations - must have body)
    # Pattern: return_type name(params) { ... }
    func_pattern = r'''
        (?:^|[\n;{}])                       # Start of line or after statement
        \s*
        (?:static\s+|inline\s+|extern\s+)*  # Optional modifiers
        ([\w\s\*]+?)                         # Return type
        \s+
        (\w+)                                # Function name
        \s*\(([^)]*)\)                       # Parameters
        \s*\{                                # Opening brace
    '''
    for match in re.finditer(func_pattern, source, re.VERBOSE | re.MULTILINE):
        ret_type = match.group(1).strip()
        name = match.group(2).strip()
        params = match.group(3).strip()

        # Skip if it looks like a control structure
        if name in ("if", "while", "for", "switch", "catch"):
            continue

        # Find line number
        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "function",
            "signature": f"{ret_type} {name}({params})",
            "docstring": _extract_preceding_comment(source, match.start()),
            "line": line_num,
        })

    # Extract struct definitions
    struct_pattern = r'''
        (?:typedef\s+)?                      # Optional typedef
        struct\s+
        (\w+)?                               # Struct name (optional for typedef)
        \s*\{([^}]*)\}                       # Body
        \s*(\w+)?                            # Typedef alias
        \s*;
    '''
    for match in re.finditer(struct_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1) or match.group(3)  # Use struct name or typedef name
        if not name:
            continue

        # Extract field names
        body = match.group(2)
        fields = []
        for field_match in re.finditer(r'(\w+)\s*[;\[]', body):
            fields.append(field_match.group(1))

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "struct",
            "signature": f"struct {name}",
            "docstring": _extract_preceding_comment(source, match.start()),
            "methods": fields,  # Use methods field for fields
            "line": line_num,
        })

    # Extract enum definitions
    enum_pattern = r'''
        (?:typedef\s+)?
        enum\s+
        (\w+)?
        \s*\{([^}]*)\}
        \s*(\w+)?
        \s*;
    '''
    for match in re.finditer(enum_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1) or match.group(3)
        if not name:
            continue

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "enum",
            "signature": f"enum {name}",
            "docstring": "",
            "line": line_num,
        })

    # Extract #define macros (function-like and constants)
    for match in re.finditer(r'^#define\s+(\w+)(?:\([^)]*\))?\s+(.*)$', source, re.MULTILINE):
        name = match.group(1)
        # Skip include guards
        if name.endswith("_H") or name.endswith("_H_"):
            continue

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "macro",
            "signature": f"#define {name}",
            "docstring": "",
            "line": line_num,
        })

    return result


def _extract_file_comment(source: str) -> str:
    """Extract first block comment as file docstring."""
    # Look for /* ... */ at start
    match = re.match(r'\s*/\*\s*(.*?)\s*\*/', source, re.DOTALL)
    if match:
        comment = match.group(1)
        # Get first meaningful line
        for line in comment.split("\n"):
            line = line.strip().lstrip("*").strip()
            if line and not line.startswith("Copyright"):
                return line[:100]
    return ""


def _extract_preceding_comment(source: str, pos: int) -> str:
    """Extract comment immediately before a position."""
    # Look backwards for /* */ or // comments
    before = source[:pos].rstrip()

    # Check for block comment
    if before.endswith("*/"):
        start = before.rfind("/*")
        if start != -1:
            comment = before[start+2:-2].strip()
            # Get first line
            lines = [l.strip().lstrip("*").strip() for l in comment.split("\n")]
            for line in lines:
                if line:
                    return line[:100]

    # Check for line comment
    lines = before.split("\n")
    if lines and lines[-1].strip().startswith("//"):
        return lines[-1].strip()[2:].strip()[:100]

    return ""


def resolve_include_to_module(
    include_info: dict,
    project_headers: List[str],
) -> Optional[str]:
    """Resolve an include to a project header.

    Args:
        include_info: Dict from parse_c_file imports
        project_headers: List of known header paths in the project

    Returns:
        Header path if internal, None if system/external
    """
    if include_info.get("is_system"):
        return None

    name = include_info["name"]

    # Try exact match
    for header in project_headers:
        if header.endswith(name) or header.endswith("/" + name):
            return header

    return None
```

## `erirpg/parsers/python.py`

What it is: Python parser using stdlib ast module.

```python
"""
Python parser using stdlib ast module.

Extracts:
- Module docstring (for summary)
- Import statements (for dependencies)
- Class definitions (for interfaces)
- Top-level function definitions (for interfaces)
"""

import ast
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_python_file(path: str) -> Dict[str, Any]:
    """Parse Python file, extract interfaces and imports.

    Args:
        path: Path to Python file

    Returns:
        Dict with keys:
        - docstring: Module docstring (first line)
        - imports: List of import dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            "docstring": "",
            "imports": [],
            "interfaces": [],
            "lines": lines,
            "error": f"SyntaxError: {e}",
        }

    result = {
        "docstring": _get_first_line(ast.get_docstring(tree)),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "type": "import",
                    "name": alias.name,
                    "asname": alias.asname,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:  # Skip relative imports without module
                result["imports"].append({
                    "type": "from",
                    "module": node.module,
                    "names": [a.name for a in node.names],
                    "level": node.level,  # 0=absolute, 1=relative, etc.
                })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

            result["interfaces"].append({
                "name": node.name,
                "type": "class",
                "methods": methods,
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
                "bases": [_get_name(base) for base in node.bases],
            })
        elif isinstance(node, ast.FunctionDef):
            # Top-level function only (col_offset check not needed at module level)
            result["interfaces"].append({
                "name": node.name,
                "type": "function",
                "signature": _get_function_signature(node),
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
            })
        elif isinstance(node, ast.AsyncFunctionDef):
            result["interfaces"].append({
                "name": node.name,
                "type": "async_function",
                "signature": _get_function_signature(node, is_async=True),
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
            })
        elif isinstance(node, ast.Assign):
            # Module-level constants (ALL_CAPS)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    result["interfaces"].append({
                        "name": target.id,
                        "type": "const",
                        "signature": "",
                        "docstring": "",
                        "line": node.lineno,
                    })

    return result


def _get_first_line(docstring: Optional[str]) -> str:
    """Extract first line of docstring."""
    if not docstring:
        return ""
    lines = docstring.strip().split("\n")
    return lines[0].strip() if lines else ""


def _get_name(node: ast.expr) -> str:
    """Get string name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[...]"
    else:
        return "?"


def _get_function_signature(node, is_async: bool = False) -> str:
    """Extract function signature as string.

    Args:
        node: ast.FunctionDef or ast.AsyncFunctionDef
        is_async: Whether function is async

    Returns:
        Signature string like "def foo(x: int, y: str) -> bool"
    """
    args = []

    # Regular args
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            try:
                arg_str += f": {ast.unparse(arg.annotation)}"
            except Exception:
                arg_str += ": ?"
        args.append(arg_str)

    # *args
    if node.args.vararg:
        vararg = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            try:
                vararg += f": {ast.unparse(node.args.vararg.annotation)}"
            except Exception:
                pass
        args.append(vararg)

    # **kwargs
    if node.args.kwarg:
        kwarg = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            try:
                kwarg += f": {ast.unparse(node.args.kwarg.annotation)}"
            except Exception:
                pass
        args.append(kwarg)

    prefix = "async def" if is_async else "def"
    sig = f"{prefix} {node.name}({', '.join(args)})"

    if node.returns:
        try:
            sig += f" -> {ast.unparse(node.returns)}"
        except Exception:
            sig += " -> ?"

    return sig


def resolve_import_to_module(
    import_info: dict,
    project_modules: List[str],
    project_name: str = "",
) -> Optional[str]:
    """Resolve an import to a project module path.

    Args:
        import_info: Dict from parse_python_file imports
        project_modules: List of known module paths in the project
        project_name: Name of project (for matching top-level imports)

    Returns:
        Module path if internal, None if external
    """
    if import_info["type"] == "import":
        # import foo.bar.baz
        name = import_info["name"]
        parts = name.split(".")

        # Check if any module path starts with this
        for mod in project_modules:
            mod_parts = mod.replace("/", ".").replace(".py", "").split(".")
            if parts[0] == mod_parts[0]:
                # Match - figure out which module
                candidate = "/".join(parts) + ".py"
                if candidate in project_modules:
                    return candidate
                # Try as package
                candidate = "/".join(parts) + "/__init__.py"
                if candidate in project_modules:
                    return candidate
        return None

    elif import_info["type"] == "from":
        # from foo.bar import baz
        module = import_info["module"]
        level = import_info.get("level", 0)

        if level > 0:
            # Relative import - treat as internal
            # Would need file context to fully resolve
            return None

        parts = module.split(".")

        # Check project name match
        if project_name and parts[0] == project_name:
            candidate = "/".join(parts) + ".py"
            if candidate in project_modules:
                return candidate
            candidate = "/".join(parts[1:]) + ".py"  # Without project name
            if candidate in project_modules:
                return candidate

        # Check direct module match
        for mod in project_modules:
            mod_no_ext = mod.replace(".py", "").replace("/__init__", "")
            mod_dotted = mod_no_ext.replace("/", ".")
            if mod_dotted == module or mod_dotted.endswith(f".{module}"):
                return mod

        return None

    return None


def classify_external_package(import_info: dict) -> Optional[str]:
    """Extract external package name from import.

    Returns the top-level package name (e.g., "torch" from "torch.nn").
    Returns None for relative imports.
    """
    if import_info["type"] == "import":
        name = import_info["name"]
        return name.split(".")[0]

    elif import_info["type"] == "from":
        if import_info.get("level", 0) > 0:
            return None  # Relative import
        module = import_info["module"]
        return module.split(".")[0]

    return None
```

## `erirpg/parsers/rust.py`

What it is: Rust parser using regex (no external deps).

```python
"""
Rust parser using regex (no external deps).

Extracts:
- use statements (for dependencies)
- fn definitions (for interfaces)
- struct/enum definitions (for interfaces)
- impl blocks (for interfaces)
- mod declarations (for dependencies)
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_rust_file(path: str) -> Dict[str, Any]:
    """Parse Rust file, extract interfaces and imports.

    Args:
        path: Path to .rs file

    Returns:
        Dict with keys:
        - docstring: Module doc comment (//! or /*!)
        - imports: List of use/mod dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    result = {
        "docstring": _extract_module_doc(source),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    # Extract use statements
    # use foo::bar::{baz, qux};
    for match in re.finditer(r'use\s+([\w:]+(?:::\{[^}]+\})?)\s*;', source):
        path = match.group(1)
        # Extract crate name
        parts = path.split("::")
        crate_name = parts[0] if parts else path

        result["imports"].append({
            "type": "use",
            "name": path,
            "crate": crate_name,
        })

    # Extract mod declarations (both inline and external)
    for match in re.finditer(r'(?:pub\s+)?mod\s+(\w+)\s*[{;]', source):
        name = match.group(1)
        result["imports"].append({
            "type": "mod",
            "name": name,
        })

    # Extract function definitions
    fn_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?           # Optional pub/pub(crate)
        (?:async\s+)?                        # Optional async
        (?:unsafe\s+)?                       # Optional unsafe
        (?:const\s+)?                        # Optional const
        fn\s+
        (\w+)                                # Function name
        (?:<[^>]+>)?                         # Optional generics
        \s*\(([^)]*)\)                       # Parameters
        (?:\s*->\s*([^\{]+?))?               # Optional return type
        \s*(?:where[^{]+)?\s*\{              # Optional where clause + opening brace
    '''
    for match in re.finditer(fn_pattern, source, re.VERBOSE):
        name = match.group(1)
        params = match.group(2).strip()
        ret_type = match.group(3).strip() if match.group(3) else "()"

        line_num = source[:match.start()].count("\n") + 1

        # Get doc comment
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "function",
            "signature": f"fn {name}({_summarize_params(params)}) -> {ret_type}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract struct definitions
    struct_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        struct\s+
        (\w+)                                # Struct name
        (?:<[^>]+>)?                         # Optional generics
        \s*(?:\{([^}]*)\}|\([^)]*\)\s*;|;)   # Body or tuple struct or unit struct
    '''
    for match in re.finditer(struct_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1)
        body = match.group(2) or ""

        # Extract field names
        fields = []
        for field_match in re.finditer(r'(\w+)\s*:', body):
            fields.append(field_match.group(1))

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "struct",
            "signature": f"struct {name}",
            "docstring": doc,
            "methods": fields,
            "line": line_num,
        })

    # Extract enum definitions
    enum_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        enum\s+
        (\w+)                                # Enum name
        (?:<[^>]+>)?                         # Optional generics
        \s*\{([^}]*)\}
    '''
    for match in re.finditer(enum_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1)
        body = match.group(2)

        # Extract variant names
        variants = []
        for var_match in re.finditer(r'(\w+)(?:\s*\{|\s*\(|,|\s*$)', body):
            variants.append(var_match.group(1))

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "enum",
            "signature": f"enum {name}",
            "docstring": doc,
            "methods": variants,
            "line": line_num,
        })

    # Extract impl blocks
    impl_pattern = r'''
        (?:^|\n)\s*
        impl\s*
        (?:<[^>]+>\s*)?                      # Optional generics
        (?:(\w+)\s+for\s+)?                  # Optional trait
        (\w+)                                # Type name
        (?:<[^>]+>)?                         # Optional type generics
        \s*\{
    '''
    for match in re.finditer(impl_pattern, source, re.VERBOSE):
        trait_name = match.group(1)
        type_name = match.group(2)

        line_num = source[:match.start()].count("\n") + 1

        name = f"{type_name}" if not trait_name else f"{trait_name} for {type_name}"

        result["interfaces"].append({
            "name": name,
            "type": "impl",
            "signature": f"impl {name}",
            "docstring": "",
            "line": line_num,
        })

    # Extract trait definitions
    trait_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        trait\s+
        (\w+)                                # Trait name
        (?:<[^>]+>)?                         # Optional generics
        \s*(?::\s*[^{]+)?\s*\{               # Optional bounds + opening brace
    '''
    for match in re.finditer(trait_pattern, source, re.VERBOSE):
        name = match.group(1)
        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "trait",
            "signature": f"trait {name}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract const definitions
    const_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        const\s+
        (\w+)                                # Const name
        \s*:\s*([^=]+?)                      # Type
        \s*=
    '''
    for match in re.finditer(const_pattern, source, re.VERBOSE):
        name = match.group(1)
        const_type = match.group(2).strip()
        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "const",
            "signature": f"const {name}: {const_type}",
            "docstring": "",
            "line": line_num,
        })

    return result


def _extract_module_doc(source: str) -> str:
    """Extract module-level doc comment (//! or /*!)."""
    # Check for //! comments at start
    lines = source.split("\n")
    doc_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("//!"):
            doc_lines.append(line[3:].strip())
        elif line.startswith("/*!"):
            # Block doc comment
            match = re.match(r'/\*!\s*(.*?)\s*\*/', source, re.DOTALL)
            if match:
                return match.group(1).split("\n")[0].strip()[:100]
            break
        elif line and not line.startswith("//"):
            break

    if doc_lines:
        return doc_lines[0][:100] if doc_lines else ""
    return ""


def _extract_doc_comment(source: str, pos: int) -> str:
    """Extract /// doc comment immediately before a position."""
    before = source[:pos]
    lines = before.split("\n")

    # Look for /// comments working backwards
    doc_lines = []
    for line in reversed(lines[-10:]):  # Check last 10 lines
        line = line.strip()
        if line.startswith("///"):
            doc_lines.insert(0, line[3:].strip())
        elif line.startswith("#["):
            continue  # Skip attributes
        elif line == "" and doc_lines:
            continue
        elif doc_lines:
            break
        else:
            break

    return doc_lines[0] if doc_lines else ""


def _summarize_params(params: str) -> str:
    """Summarize function parameters for display."""
    if not params.strip():
        return ""

    # Count parameters
    depth = 0
    count = 1
    for c in params:
        if c in "(<[{":
            depth += 1
        elif c in ")>]}":
            depth -= 1
        elif c == "," and depth == 0:
            count += 1

    if count > 3:
        return "..."
    if len(params) > 50:
        return "..."
    return params


def resolve_use_to_module(
    use_info: dict,
    project_modules: List[str],
) -> Optional[str]:
    """Resolve a use statement to a project module.

    Args:
        use_info: Dict from parse_rust_file imports
        project_modules: List of known module paths in the project

    Returns:
        Module path if internal, None if external crate
    """
    crate = use_info.get("crate", "")

    # Check if it's a known internal module
    if use_info["type"] == "mod":
        name = use_info["name"]
        for mod in project_modules:
            if mod.endswith(f"/{name}.rs") or mod.endswith(f"/{name}/mod.rs"):
                return mod

    # Check use statements
    if crate in ("crate", "self", "super"):
        # Internal path
        name = use_info["name"].replace("::", "/")
        for mod in project_modules:
            if name in mod:
                return mod

    return None


def classify_external_crate(use_info: dict) -> Optional[str]:
    """Extract external crate name from use statement.

    Returns the crate name, or None if it's internal.
    """
    if use_info["type"] == "mod":
        return None

    crate = use_info.get("crate", "")

    if crate in ("crate", "self", "super"):
        return None  # Internal

    if crate == "std":
        return None  # Standard library

    return crate
```

## `erirpg/refs.py`

What it is: Code references for EriRPG.

```python
"""
Code references for EriRPG.

References point to code locations without storing full content.
They track file identity via hash and mtime for staleness detection,
and can hydrate (load fresh content) on demand.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import hashlib
import os

if TYPE_CHECKING:
    pass


@dataclass
class CodeRef:
    """Reference to a code location without storing full content.

    Attributes:
        path: Relative path from project root
        content_hash: SHA256 hash of file content at creation time
        mtime: File modification time at creation time
        line_start: Starting line number (1-indexed, inclusive)
        line_end: Ending line number (1-indexed, inclusive), None for whole file
    """
    path: str
    content_hash: str
    mtime: float
    line_start: int = 1
    line_end: Optional[int] = None

    def is_stale(self, project_path: str) -> bool:
        """Check if the referenced file has changed.

        Uses a two-phase check:
        1. Fast path: check mtime (if unchanged, file unchanged)
        2. Slow path: if mtime changed, verify with hash

        Args:
            project_path: Root path of the project

        Returns:
            True if file has been deleted or modified, False otherwise
        """
        full_path = os.path.join(project_path, self.path)

        if not os.path.exists(full_path):
            return True  # File deleted

        current_mtime = os.path.getmtime(full_path)
        if current_mtime == self.mtime:
            return False  # Quick path: unchanged

        # mtime changed - verify with hash
        current_hash = self._compute_hash(full_path)
        return current_hash != self.content_hash

    def hydrate(self, project_path: str) -> str:
        """Load fresh content from the referenced location.

        Args:
            project_path: Root path of the project

        Returns:
            File content (or line range if line_start/line_end specified)

        Raises:
            FileNotFoundError: If the file no longer exists
        """
        full_path = os.path.join(project_path, self.path)

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            if self.line_end is None and self.line_start == 1:
                # Whole file
                return f.read()
            else:
                # Specific line range
                lines = f.readlines()
                start_idx = self.line_start - 1  # 0-indexed
                end_idx = self.line_end if self.line_end else len(lines)
                return "".join(lines[start_idx:end_idx])

    @classmethod
    def from_file(
        cls,
        project_path: str,
        relative_path: str,
        line_start: int = 1,
        line_end: Optional[int] = None
    ) -> "CodeRef":
        """Create a CodeRef from current file state.

        Args:
            project_path: Root path of the project
            relative_path: Path relative to project root
            line_start: Starting line (1-indexed)
            line_end: Ending line (1-indexed), None for whole file

        Returns:
            CodeRef capturing current file state

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = os.path.join(project_path, relative_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")

        mtime = os.path.getmtime(full_path)
        content_hash = cls._compute_hash_static(full_path)

        return cls(
            path=relative_path,
            content_hash=content_hash,
            mtime=mtime,
            line_start=line_start,
            line_end=line_end,
        )

    def _compute_hash(self, full_path: str) -> str:
        """Compute SHA256 hash of file content."""
        return self._compute_hash_static(full_path)

    @staticmethod
    def _compute_hash_static(full_path: str) -> str:
        """Compute SHA256 hash of file content (static version)."""
        hasher = hashlib.sha256()
        with open(full_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "mtime": self.mtime,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CodeRef":
        """Deserialize from dictionary."""
        return cls(
            path=d["path"],
            content_hash=d["content_hash"],
            mtime=d["mtime"],
            line_start=d.get("line_start", 1),
            line_end=d.get("line_end"),
        )

    def __repr__(self) -> str:
        lines = f":{self.line_start}-{self.line_end}" if self.line_end else ""
        return f"CodeRef({self.path}{lines})"
```

## `erirpg/registry.py`

What it is: Project registry for managing registered projects.

```python
"""
Project registry for managing registered projects.

Stores project metadata in ~/.eri-rpg/registry.json
Each project has a name, path, language, and index status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path
import os


def detect_project_language(path: str) -> str:
    """Auto-detect project language from files in the project root.

    Checks for common language indicators:
    - Cargo.toml -> rust
    - pyproject.toml / setup.py / *.py -> python
    - *.c, *.h, Makefile, CMakeLists.txt -> c

    Returns:
        Language string: 'python', 'c', 'rust', or 'unknown'
    """
    path = os.path.abspath(os.path.expanduser(path))

    # Check for language-specific files
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        return "rust"

    if os.path.exists(os.path.join(path, "pyproject.toml")) or \
       os.path.exists(os.path.join(path, "setup.py")):
        return "python"

    # Count files to determine majority language
    py_count = 0
    c_count = 0
    rs_count = 0

    for root, dirs, files in os.walk(path):
        # Skip hidden and build dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("target", "build", "node_modules", "__pycache__")]

        for f in files:
            if f.endswith(".py"):
                py_count += 1
            elif f.endswith((".c", ".h", ".cpp", ".hpp")):
                c_count += 1
            elif f.endswith(".rs"):
                rs_count += 1

        # Early exit if we've sampled enough
        if py_count + c_count + rs_count > 10:
            break

    # Determine by majority
    if c_count >= max(py_count, rs_count):
        return "c"
    elif rs_count >= max(py_count, c_count):
        return "rust"
    elif py_count > 0:
        return "python"

    return "unknown"


@dataclass
class Project:
    """A registered project."""
    name: str
    path: str  # Absolute path to project root
    lang: str  # "python" | "rust" | "c"
    indexed_at: Optional[datetime] = None
    graph_path: str = ""  # Path to graph.json

    def __post_init__(self):
        if not self.graph_path:
            self.graph_path = os.path.join(self.path, ".eri-rpg", "graph.json")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "lang": self.lang,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "graph_path": self.graph_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        indexed_at = None
        if d.get("indexed_at"):
            indexed_at = datetime.fromisoformat(d["indexed_at"])
        return cls(
            name=d["name"],
            path=d["path"],
            lang=d["lang"],
            indexed_at=indexed_at,
            graph_path=d.get("graph_path", ""),
        )

    def is_indexed(self) -> bool:
        """Check if project has been indexed."""
        return self.indexed_at is not None and os.path.exists(self.graph_path)

    def index_age_days(self) -> Optional[float]:
        """Days since last index, or None if never indexed."""
        if not self.indexed_at:
            return None
        delta = datetime.now() - self.indexed_at
        return delta.total_seconds() / 86400


@dataclass
class Registry:
    """Registry of all known projects."""
    projects: Dict[str, Project] = field(default_factory=dict)
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.eri-rpg"))

    def __post_init__(self):
        self._registry_path = os.path.join(self.config_dir, "registry.json")

    def add(self, name: str, path: str, lang: str) -> Project:
        """Add a new project to the registry.

        Args:
            name: Unique project name
            path: Path to project root
            lang: Programming language

        Returns:
            The created Project

        Raises:
            ValueError: If project with name already exists
            FileNotFoundError: If path doesn't exist
        """
        if name in self.projects:
            raise ValueError(f"Project '{name}' already exists")

        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(abs_path):
            raise FileNotFoundError(f"Path does not exist: {abs_path}")

        project = Project(name=name, path=abs_path, lang=lang)
        self.projects[name] = project
        self.save()
        return project

    def remove(self, name: str) -> bool:
        """Remove a project from the registry.

        Args:
            name: Project name to remove

        Returns:
            True if removed, False if not found
        """
        if name not in self.projects:
            return False

        del self.projects[name]
        self.save()
        return True

    def get(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.projects.get(name)

    def list(self) -> List[Project]:
        """List all registered projects."""
        return list(self.projects.values())

    def save(self) -> None:
        """Save registry to disk."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0.0",
            "projects": {k: v.to_dict() for k, v in self.projects.items()},
        }

        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        """Load registry from disk."""
        if not os.path.exists(self._registry_path):
            self.projects = {}
            return

        with open(self._registry_path, "r") as f:
            data = json.load(f)

        self.projects = {
            k: Project.from_dict(v)
            for k, v in data.get("projects", {}).items()
        }

    def update_indexed(self, name: str) -> None:
        """Mark a project as indexed now."""
        if name in self.projects:
            self.projects[name].indexed_at = datetime.now()
            self.save()

    @classmethod
    def get_instance(cls) -> "Registry":
        """Get or create the global registry instance."""
        registry = cls()
        registry.load()
        return registry
```

## `erirpg/search.py`

What it is: Search functionality for EriRPG knowledge.

```python
"""
Search functionality for EriRPG knowledge.

Provides keyword-based search over learnings with ranking
by relevance, freshness, and confidence.
"""

import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from erirpg.memory import StoredLearning


def tokenize(text: str) -> Set[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Text to tokenize

    Returns:
        Set of lowercase word tokens
    """
    if not text:
        return set()
    return set(re.findall(r'\w+', text.lower()))


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets.

    Args:
        set1: First set
        set2: Second set

    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def search_learnings(
    learnings: Dict[str, "StoredLearning"],
    query: str,
    limit: int = 10,
    project_path: str = None,
) -> List[Tuple[str, "StoredLearning", float]]:
    """Search learnings by query.

    Scoring components:
    - Path match: 0.2 weight (module path contains query terms)
    - Summary match: 0.3 weight (summary text matches)
    - Purpose match: 0.2 weight (purpose text matches)
    - Functions match: 0.2 weight (function names/descriptions)
    - Gotchas match: 0.1 weight (gotcha text matches)

    Boosted by:
    - Recency: +0.1 for learnings < 7 days old
    - Confidence: multiplied by confidence score
    - Freshness: -0.2 if stale (when project_path provided)

    Args:
        learnings: Dict of module_path -> StoredLearning
        query: Search query (space-separated keywords)
        limit: Maximum results to return
        project_path: Optional project path for staleness checking

    Returns:
        List of (module_path, learning, score) tuples sorted by score
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for module_path, learning in learnings.items():
        score = 0.0

        # Path match (0.2 weight)
        path_tokens = tokenize(module_path.replace("/", " ").replace("_", " "))
        path_score = jaccard_similarity(query_tokens, path_tokens)
        score += path_score * 0.2

        # Exact path substring match bonus
        if query.lower() in module_path.lower():
            score += 0.15

        # Summary match (0.3 weight)
        summary_tokens = tokenize(learning.summary)
        summary_score = jaccard_similarity(query_tokens, summary_tokens)
        score += summary_score * 0.3

        # Exact phrase in summary bonus
        if query.lower() in learning.summary.lower():
            score += 0.2

        # Purpose match (0.2 weight)
        purpose_tokens = tokenize(learning.purpose)
        purpose_score = jaccard_similarity(query_tokens, purpose_tokens)
        score += purpose_score * 0.2

        # Functions match (0.2 weight)
        func_text = " ".join(
            f"{name} {desc}"
            for name, desc in learning.key_functions.items()
        )
        func_tokens = tokenize(func_text)
        func_score = jaccard_similarity(query_tokens, func_tokens)
        score += func_score * 0.2

        # Gotchas match (0.1 weight)
        gotcha_text = " ".join(learning.gotchas)
        gotcha_tokens = tokenize(gotcha_text)
        gotcha_score = jaccard_similarity(query_tokens, gotcha_tokens)
        score += gotcha_score * 0.1

        # Recency boost
        days_old = (datetime.now() - learning.learned_at).days
        if days_old < 7:
            score += 0.1
        elif days_old < 30:
            score += 0.05

        # Confidence multiplier
        score *= learning.confidence

        # Staleness penalty
        if project_path and learning.is_stale(project_path):
            score -= 0.2

        if score > 0.01:  # Threshold to filter noise
            results.append((module_path, learning, score))

    # Sort by score descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]


def search_patterns(
    patterns: Dict[str, str],
    query: str,
    limit: int = 10,
) -> List[Tuple[str, str, float]]:
    """Search patterns by query.

    Args:
        patterns: Dict of name -> description
        query: Search query
        limit: Maximum results

    Returns:
        List of (name, description, score) tuples
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for name, description in patterns.items():
        score = 0.0

        # Name match
        name_tokens = tokenize(name.replace("_", " "))
        name_score = jaccard_similarity(query_tokens, name_tokens)
        score += name_score * 0.5

        # Exact name match
        if query.lower() in name.lower():
            score += 0.3

        # Description match
        desc_tokens = tokenize(description)
        desc_score = jaccard_similarity(query_tokens, desc_tokens)
        score += desc_score * 0.5

        if score > 0.01:
            results.append((name, description, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]


def search_decisions(
    decisions: List,
    query: str,
    limit: int = 10,
) -> List[Tuple[int, object, float]]:
    """Search decisions by query.

    Args:
        decisions: List of StoredDecision objects
        query: Search query
        limit: Maximum results

    Returns:
        List of (index, decision, score) tuples
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for i, decision in enumerate(decisions):
        score = 0.0

        # Title match
        title_tokens = tokenize(decision.title)
        title_score = jaccard_similarity(query_tokens, title_tokens)
        score += title_score * 0.4

        # Exact title match
        if query.lower() in decision.title.lower():
            score += 0.2

        # Reason match
        reason_tokens = tokenize(decision.reason)
        reason_score = jaccard_similarity(query_tokens, reason_tokens)
        score += reason_score * 0.4

        # Affects match
        affects_text = " ".join(decision.affects)
        affects_tokens = tokenize(affects_text)
        affects_score = jaccard_similarity(query_tokens, affects_tokens)
        score += affects_score * 0.2

        if score > 0.01:
            results.append((i, decision, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]
```

## `erirpg/state.py`

What it is: State tracking for orchestration mode.

```python
"""
State tracking for orchestration mode.

Tracks current task, phase, and history to guide users
through multi-step workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import os


@dataclass
class State:
    """Orchestration state for tracking progress."""
    current_task: Optional[str] = None
    phase: str = "idle"  # "idle" | "extracting" | "planning" | "implementing" | "validating"
    waiting_on: Optional[str] = None  # "user" | "claude" | None
    context_file: Optional[str] = None
    feature_file: Optional[str] = None
    plan_file: Optional[str] = None
    history: List[Dict] = field(default_factory=list)

    _state_dir: str = field(default="", repr=False)

    def __post_init__(self):
        if not self._state_dir:
            self._state_dir = os.path.expanduser("~/.eri-rpg")
        self._state_path = os.path.join(self._state_dir, "state.json")

    def update(self, **kwargs) -> None:
        """Update state fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def log(self, action: str, details: str = "") -> None:
        """Log an action to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "phase": self.phase,
        }
        self.history.append(entry)
        self.save()

    def reset(self) -> None:
        """Reset state to idle."""
        self.current_task = None
        self.phase = "idle"
        self.waiting_on = None
        self.context_file = None
        self.feature_file = None
        self.plan_file = None
        self.save()

    def get_next_step(self) -> str:
        """Get recommended next step based on current state."""
        if self.phase == "idle":
            return "Start a task with: eri-rpg do '<task description>'"

        elif self.phase == "extracting":
            if self.feature_file:
                return f"Feature extracted to {self.feature_file}. Plan with: eri-rpg plan {self.feature_file} <target>"
            return "Extracting feature..."

        elif self.phase == "planning":
            if self.plan_file:
                return f"Plan created at {self.plan_file}. Generate context with: eri-rpg context {self.feature_file} <target>"
            return "Planning transplant..."

        elif self.phase == "context_ready":
            return f"Give Claude Code the context at {self.context_file}\nAfter implementation, run: eri-rpg validate"

        elif self.phase == "implementing":
            return "Waiting for Claude Code to implement. When done: eri-rpg validate"

        elif self.phase == "validating":
            return "Validating implementation..."

        elif self.phase == "done":
            return "Task complete! Start a new task or run: eri-rpg status"

        return "Unknown state. Run: eri-rpg status"

    def save(self) -> None:
        """Save state to disk."""
        os.makedirs(self._state_dir, exist_ok=True)

        data = {
            "current_task": self.current_task,
            "phase": self.phase,
            "waiting_on": self.waiting_on,
            "context_file": self.context_file,
            "feature_file": self.feature_file,
            "plan_file": self.plan_file,
            "history": self.history[-50:],  # Keep last 50 entries
        }

        with open(self._state_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "State":
        """Load state from disk."""
        state_dir = os.path.expanduser("~/.eri-rpg")
        state_path = os.path.join(state_dir, "state.json")

        state = cls(_state_dir=state_dir)

        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                data = json.load(f)
            state.current_task = data.get("current_task")
            state.phase = data.get("phase", "idle")
            state.waiting_on = data.get("waiting_on")
            state.context_file = data.get("context_file")
            state.feature_file = data.get("feature_file")
            state.plan_file = data.get("plan_file")
            state.history = data.get("history", [])

        return state

    def format_status(self) -> str:
        """Format current status for display."""
        lines = []

        if self.current_task:
            lines.append(f"Current task: {self.current_task}")
        else:
            lines.append("No active task")

        lines.append(f"Phase: {self.phase}")

        if self.waiting_on:
            lines.append(f"Waiting on: {self.waiting_on}")

        if self.feature_file:
            lines.append(f"Feature: {self.feature_file}")
        if self.plan_file:
            lines.append(f"Plan: {self.plan_file}")
        if self.context_file:
            lines.append(f"Context: {self.context_file}")

        lines.append("")
        lines.append(f"Next step: {self.get_next_step()}")

        return "\n".join(lines)
```

