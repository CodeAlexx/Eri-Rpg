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
from erirpg.memory import load_knowledge


def get_module_info(project_path: str, module_path: str, graph: "Graph") -> Optional[dict]:
    """
    Get module info, checking v2 knowledge first then v1 graph.
    
    Returns:
        Dict with module info or None if unknown.
    """
    # Check v2 knowledge first (memory.py)
    try:
        knowledge = load_knowledge(project_path)
        if module_path in knowledge.learnings:
            learning = knowledge.learnings[module_path]
            return {
                'summary': learning.summary,
                'purpose': learning.purpose,
                'key_functions': learning.key_functions,
                'gotchas': learning.gotchas,
                'source': 'v2_knowledge'
            }
    except Exception:
        pass
    
    # Fall back to v1 graph knowledge
    learning = graph.knowledge.get_learning(module_path)
    if learning:
        return {
            'summary': learning.summary,
            'purpose': getattr(learning, 'purpose', ''),
            'key_functions': getattr(learning, 'key_functions', {}),
            'gotchas': getattr(learning, 'gotchas', []),
            'source': 'v1_graph'
        }
    
    return None


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
