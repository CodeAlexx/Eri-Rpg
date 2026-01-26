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


# Map file extensions to code fence languages
EXTENSION_TO_FENCE = {
    # Python
    ".py": "python",
    ".pyi": "python",
    # Rust
    ".rs": "rust",
    # C/C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".hh": "cpp",
    # JavaScript/TypeScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    # Other common languages
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".sql": "sql",
}


def get_fence_language(file_path: str) -> str:
    """Get the appropriate code fence language for a file path.

    Args:
        file_path: Path to the file (can be relative or absolute)

    Returns:
        Language string for code fences (e.g., 'python', 'rust', 'c')
        Falls back to 'text' for unknown extensions.
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_TO_FENCE.get(ext, "text")


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
                fence_lang = get_fence_language(comp_path)
                lines.append(f"```{fence_lang}")
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


def estimate_tokens(
    feature: Feature,
    plan: TransplantPlan,
    source_project: Optional[Project] = None,
) -> int:
    """Estimate token count for context.

    Rough estimate: ~4 chars per token for code, ~3 for prose.

    Args:
        feature: The extracted feature
        plan: The transplant plan
        source_project: Source project (needed to hydrate code refs for accurate estimate)

    Returns:
        Estimated token count
    """
    # Get code chars - try to hydrate refs if source_project is available
    code_chars = 0

    if source_project and feature.code_refs:
        # Hydrate from refs for accurate count
        try:
            hydrated = feature.hydrate_code(source_project.path)
            code_chars = sum(len(code) for code in hydrated.values())
        except Exception:
            # Fall back to snapshots if hydration fails
            code_chars = sum(len(code) for code in feature.code.values())
    else:
        # Use snapshots
        code_chars = sum(len(code) for code in feature.code.values())

    # If still zero and we have refs, warn about inaccurate estimate
    if code_chars == 0 and feature.code_refs:
        # Estimate based on typical file sizes (~2000 chars per file)
        code_chars = len(feature.code_refs) * 2000

    plan_chars = len(str(plan.mappings)) + len(str(plan.wiring))
    prose_chars = 1000  # Header, instructions

    code_tokens = code_chars / 4
    other_tokens = (plan_chars + prose_chars) / 3

    return int(code_tokens + other_tokens)
