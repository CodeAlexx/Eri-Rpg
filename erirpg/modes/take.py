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
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)
    
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
        source_project=source_proj,
        use_learnings=True
    )

    tokens = estimate_tokens(feature, plan, source_project=source_proj)

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
