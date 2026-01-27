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

TOKEN BUDGET ENFORCEMENT:
- Default budget: 6500 tokens (fits comfortably in context)
- Uses tiktoken for ACCURATE token counting (not estimates)
- Code is truncated to fit budget, summaries/learnings preserved
- Never exceeds max_tokens limit
"""

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tiktoken

from erirpg.ops import Feature, TransplantPlan
from erirpg.graph import Graph
from erirpg.registry import Project
from erirpg.memory import load_knowledge, get_knowledge_path


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN COUNTING (ACCURATE via tiktoken)
# ═══════════════════════════════════════════════════════════════════════════════

# Lazy-loaded encoder (cl100k_base is used by Claude/GPT-4)
_ENCODER: Optional[tiktoken.Encoding] = None


def get_encoder() -> tiktoken.Encoding:
    """Get the tiktoken encoder, lazily initialized."""
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def count_tokens(text: str) -> int:
    """Count actual tokens in text using tiktoken.

    This is ACCURATE token counting, not estimation.
    Uses cl100k_base encoding (Claude/GPT-4 compatible).

    Args:
        text: Text to count tokens for

    Returns:
        Actual token count
    """
    if not text:
        return 0
    return len(get_encoder().encode(text))


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN BUDGET CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Default token budget for context generation (from DESIGN.md)
TOKEN_BUDGET = 6500

# Minimum code to show per file (don't truncate below this)
MIN_CODE_LINES = 20

# Reserved tokens for non-code sections (measured with tiktoken)
RESERVED_HEADER = 80          # Title, metadata
RESERVED_PLAN = 250           # Mappings, wiring, order
RESERVED_INSTRUCTIONS = 180   # Instructions section
RESERVED_INTERFACES = 120     # Per interface module
RESERVED_PER_LEARNING = 180   # Per learning block


@dataclass
class TokenBudget:
    """Tracks token allocation during context generation."""
    total: int
    used: int = 0
    code_budget: int = 0

    # Breakdown
    header_tokens: int = 0
    learning_tokens: int = 0
    code_tokens: int = 0
    interface_tokens: int = 0
    plan_tokens: int = 0
    instruction_tokens: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    @property
    def over_budget(self) -> bool:
        return self.used > self.total

    def allocate(self, tokens: int, category: str) -> int:
        """Allocate tokens, return actual amount allocated."""
        available = self.remaining
        allocated = min(tokens, available)
        self.used += allocated

        # Track by category
        if category == "header":
            self.header_tokens += allocated
        elif category == "learning":
            self.learning_tokens += allocated
        elif category == "code":
            self.code_tokens += allocated
        elif category == "interface":
            self.interface_tokens += allocated
        elif category == "plan":
            self.plan_tokens += allocated
        elif category == "instruction":
            self.instruction_tokens += allocated

        return allocated

    def summary(self) -> str:
        """Return budget summary string."""
        return (
            f"Tokens: {self.used}/{self.total} "
            f"(header:{self.header_tokens} learning:{self.learning_tokens} "
            f"code:{self.code_tokens} interface:{self.interface_tokens} "
            f"plan:{self.plan_tokens} instruction:{self.instruction_tokens})"
        )


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


# ═══════════════════════════════════════════════════════════════════════════════
# CODE TRUNCATION
# ═══════════════════════════════════════════════════════════════════════════════

def truncate_code(
    code: str,
    max_tokens: int,
    file_path: str = "",
) -> Tuple[str, int, bool]:
    """Truncate code to fit within token budget.

    Uses tiktoken for ACCURATE token counting during truncation.

    Strategy:
    1. If fits, return as-is
    2. Otherwise, binary search for optimal line count
    3. Keep at least MIN_CODE_LINES lines
    4. Add truncation marker

    Args:
        code: Source code to truncate
        max_tokens: Maximum tokens allowed
        file_path: File path for context in truncation message

    Returns:
        Tuple of (truncated_code, actual_tokens, was_truncated)
    """
    if not code:
        return "", 0, False

    current_tokens = count_tokens(code)

    # If fits, return as-is
    if current_tokens <= max_tokens:
        return code, current_tokens, False

    # Need to truncate - use binary search for optimal line count
    lines = code.split('\n')
    total_lines = len(lines)

    # Binary search for max lines that fit in budget
    # Account for truncation marker (~15 tokens)
    marker_budget = 15
    target_tokens = max_tokens - marker_budget

    low = MIN_CODE_LINES
    high = total_lines
    best_lines = MIN_CODE_LINES

    while low <= high:
        mid = (low + high) // 2
        test_code = '\n'.join(lines[:mid])
        test_tokens = count_tokens(test_code)

        if test_tokens <= target_tokens:
            best_lines = mid
            low = mid + 1
        else:
            high = mid - 1

    # Build truncated output
    truncated_lines = lines[:best_lines]
    truncated_count = total_lines - best_lines

    # Add truncation marker
    truncated_lines.append("")
    truncated_lines.append(f"# ... [{truncated_count} lines truncated to fit token budget]")
    if file_path:
        truncated_lines.append(f"# Full source: {file_path}")

    truncated = '\n'.join(truncated_lines)
    actual_tokens = count_tokens(truncated)

    return truncated, actual_tokens, True


def allocate_code_budgets(
    components: List[str],
    code_dict: Dict[str, str],
    total_budget: int,
    primary_module: str = "",
) -> Dict[str, int]:
    """Allocate token budgets to each code file.

    Uses tiktoken for ACCURATE token measurement.

    Strategy:
    1. Primary module gets 40% of budget
    2. Remaining modules share the rest proportionally by actual token count

    Args:
        components: List of component paths (in dependency order)
        code_dict: Dict of path -> code content
        total_budget: Total tokens available for code
        primary_module: The primary module (gets priority)

    Returns:
        Dict of path -> allocated tokens
    """
    if not components or total_budget <= 0:
        return {}

    allocations = {}

    # Calculate actual token counts for each component
    token_counts = {c: count_tokens(code_dict.get(c, "")) for c in components}
    total_tokens = sum(token_counts.values())

    if total_tokens == 0:
        # Equal distribution if no code
        per_file = total_budget // len(components)
        return {c: per_file for c in components}

    # Primary module gets 40% (if it exists and has code)
    remaining_budget = total_budget

    if primary_module and primary_module in components:
        primary_tokens = token_counts.get(primary_module, 0)
        if primary_tokens > 0:
            primary_budget = int(total_budget * 0.4)
            # But don't allocate more than needed
            primary_budget = min(primary_budget, primary_tokens)
            allocations[primary_module] = primary_budget
            remaining_budget -= primary_budget

    # Distribute remaining budget proportionally by actual token count
    other_components = [c for c in components if c != primary_module]
    other_tokens = sum(token_counts.get(c, 0) for c in other_components)

    for comp in other_components:
        comp_tokens = token_counts.get(comp, 0)
        if comp_tokens == 0 or other_tokens == 0:
            allocations[comp] = 0
        else:
            # Proportional allocation by token count
            proportion = comp_tokens / other_tokens
            allocations[comp] = int(remaining_budget * proportion)

    return allocations


def generate_context(
    feature: Feature,
    plan: TransplantPlan,
    source_graph: Optional[Graph],
    target_graph: Graph,
    target_project: Project,
    source_project: Optional[Project] = None,
    output_dir: Optional[str] = None,
    use_learnings: bool = True,
    max_tokens: Optional[int] = None,
) -> str:
    """Generate context file for Claude Code.

    TOKEN BUDGET ENFORCEMENT:
    - If max_tokens is None, uses TOKEN_BUDGET (6500)
    - Code is truncated to fit budget, learnings/summaries preserved
    - Never exceeds the specified budget

    Args:
        feature: Extracted feature
        plan: Transplant plan
        source_graph: Source project's graph (for backward compat knowledge lookup)
        target_graph: Target project's graph
        target_project: Target project
        source_project: Source project (for v2 knowledge and hydration)
        output_dir: Where to save (default: target/.eri-rpg/context/)
        use_learnings: If True, use stored learnings instead of source when available
        max_tokens: Maximum token budget (default: TOKEN_BUDGET = 6500)

    Returns:
        Path to generated context file
    """
    # Initialize token budget
    budget = TokenBudget(total=max_tokens or TOKEN_BUDGET)

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

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Calculate reserved tokens for non-code sections
    # ═══════════════════════════════════════════════════════════════════════════

    # Count interface modules
    relevant_modules = set()
    for mapping in plan.mappings:
        if mapping.target_module:
            relevant_modules.add(mapping.target_module)

    # Reserve tokens for fixed sections
    reserved = (
        RESERVED_HEADER +
        RESERVED_PLAN +
        RESERVED_INSTRUCTIONS +
        (len(relevant_modules) * RESERVED_INTERFACES)
    )

    # Pre-scan components to count learnings vs code
    learnings_count = 0
    code_components = []

    for comp_path in feature.components:
        has_learning = False
        if use_learnings:
            if knowledge_store and knowledge_store.get_learning(comp_path):
                has_learning = True
            elif source_graph and source_graph.knowledge.get_learning(comp_path):
                has_learning = True

        if has_learning:
            learnings_count += 1
            reserved += RESERVED_PER_LEARNING
        else:
            code_components.append(comp_path)

    # Calculate code budget (what's left after reservations)
    budget.code_budget = max(0, budget.total - reserved)

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Generate content with budget enforcement
    # ═══════════════════════════════════════════════════════════════════════════

    # Generate context markdown
    lines = []

    # Header
    header_lines = [
        f"# Transplant: {feature.name}",
        "",
        f"From: **{feature.source_project}**",
        f"To: **{plan.target_project}**",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Token budget: {budget.total} (code: {budget.code_budget})",
        "",
    ]
    lines.extend(header_lines)
    budget.allocate(count_tokens("\n".join(header_lines)), "header")

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
    truncated_files = []

    # Hydrate code from refs if source_path is available
    hydrated_code = {}
    if source_path and feature.code_refs:
        hydrated_code = feature.hydrate_code(source_path)

    # Merge with snapshots for complete code dict
    all_code = {}
    for comp_path in feature.components:
        all_code[comp_path] = hydrated_code.get(comp_path) or feature.code_snapshots.get(comp_path, "")

    # Allocate code budgets per file
    code_budgets = allocate_code_budgets(
        components=code_components,
        code_dict=all_code,
        total_budget=budget.code_budget,
        primary_module=feature.primary_module,
    )

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

            learning_text = learning.format_for_context()
            lines.append(learning_text)
            budget.allocate(count_tokens(learning_text), "learning")
            lines.append("")
            lines.append("**Source**: [SKIPPED - learning exists]")
            lines.append(f"To re-read source: `eri-rpg recall {feature.source_project} {comp_path} --source`")
            lines.append("")
        else:
            # No learning - include source code with budget enforcement
            modules_without_learnings.append(comp_path)

            # Get code and budget for this file
            code = all_code.get(comp_path, "")
            file_budget = code_budgets.get(comp_path, budget.code_budget // max(1, len(code_components)))

            lines.append("**No stored understanding yet.**")
            lines.append("")

            if code:
                # BUDGET ENFORCEMENT: Truncate code if over budget
                truncated_code, actual_tokens, was_truncated = truncate_code(
                    code=code.strip(),
                    max_tokens=file_budget,
                    file_path=comp_path,
                )

                if was_truncated:
                    truncated_files.append(comp_path)
                    lines.append(f"**[TRUNCATED to fit {file_budget} token budget]**")
                    lines.append("")

                fence_lang = get_fence_language(comp_path)
                lines.append(f"```{fence_lang}")
                lines.append(truncated_code)
                lines.append("```")

                budget.allocate(actual_tokens, "code")
            else:
                lines.append("*Code not available - use `--snapshot` when extracting for offline use*")

            lines.append("")
            lines.append(f"After understanding this, store it: `eri-rpg learn {feature.source_project} {comp_path}`")
            lines.append("")

    # Target Interfaces Section
    interface_lines = [
        "---",
        "",
        "## Target Interfaces",
        "",
        f"Existing interfaces in `{plan.target_project}` to integrate with:",
        "",
    ]

    # relevant_modules already calculated in PHASE 1
    if relevant_modules:
        for mod_path in sorted(relevant_modules):
            mod = target_graph.get_module(mod_path)
            if mod:
                interface_lines.append(f"### `{mod_path}`")
                interface_lines.append("")
                interface_lines.append(f"**Summary:** {mod.summary or '(no summary)'}")
                interface_lines.append("")
                interface_lines.append("**Interfaces:**")
                for iface in mod.interfaces:
                    if iface.signature:
                        interface_lines.append(f"- `{iface.signature}`")
                    else:
                        interface_lines.append(f"- `{iface.type} {iface.name}`")
                interface_lines.append("")
    else:
        interface_lines.append("*No existing interfaces to integrate with - creating new files.*")
        interface_lines.append("")

    lines.extend(interface_lines)
    budget.allocate(count_tokens("\n".join(interface_lines)), "interface")

    # Transplant Plan Section
    plan_lines = [
        "---",
        "",
        "## Transplant Plan",
        "",
        "### Mappings",
        "",
        "| Source | Target | Action | Notes |",
        "|--------|--------|--------|-------|",
    ]
    for m in plan.mappings:
        source = f"`{m.source_interface}`"
        target = f"`{m.target_interface or 'NEW'}`" if m.target_interface else "CREATE"
        plan_lines.append(f"| {source} | {target} | {m.action} | {m.notes} |")
    plan_lines.append("")

    # Wiring
    if plan.wiring:
        plan_lines.append("### Wiring Tasks")
        plan_lines.append("")
        for w in plan.wiring:
            plan_lines.append(f"- **{w.file}**: {w.action} - {w.details}")
        plan_lines.append("")

    # Generation Order
    plan_lines.append("### Implementation Order")
    plan_lines.append("")
    plan_lines.append("Create/modify files in this order (dependencies first):")
    plan_lines.append("")
    for i, path in enumerate(plan.generation_order, 1):
        plan_lines.append(f"{i}. `{path}`")
    plan_lines.append("")

    lines.extend(plan_lines)
    budget.allocate(count_tokens("\n".join(plan_lines)), "plan")

    # Instructions Section
    instruction_lines = [
        "---",
        "",
        "## Instructions",
        "",
        "1. **Read** the source code above carefully",
        "2. **Adapt** each component for the target project:",
        "   - Adjust imports to match target structure",
        "   - Implement interface adapters where needed",
        "   - Follow target project conventions",
        "3. **Wire** components together:",
    ]
    for w in plan.wiring:
        instruction_lines.append(f"   - {w.file}: {w.details}")
    instruction_lines.extend([
        "4. **Verify** the transplant works",
        "",
        "After implementation, run: `eri-rpg validate`",
        "",
    ])

    lines.extend(instruction_lines)
    budget.allocate(count_tokens("\n".join(instruction_lines)), "instruction")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Add budget summary and warnings
    # ═══════════════════════════════════════════════════════════════════════════

    lines.append("---")
    lines.append("")
    lines.append("## Token Budget Summary")
    lines.append("")
    lines.append(f"**{budget.summary()}**")
    lines.append("")

    if truncated_files:
        lines.append(f"⚠️ **{len(truncated_files)} file(s) truncated** to fit budget:")
        for f in truncated_files:
            lines.append(f"  - `{f}`")
        lines.append("")
        lines.append("Use `eri-rpg learn` to store understanding and reduce future context size.")
        lines.append("")

    if budget.over_budget:
        lines.append(f"⚠️ **OVER BUDGET** by {budget.used - budget.total} tokens")
        lines.append("Consider using `--max-tokens` with a higher limit or storing more learnings.")
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
    """Calculate ACCURATE token count for context using tiktoken.

    This is no longer an estimate - uses actual tiktoken counting.

    Args:
        feature: The extracted feature
        plan: The transplant plan
        source_project: Source project (needed to hydrate code refs)

    Returns:
        Actual token count
    """
    total_tokens = 0

    # Count code tokens - try to hydrate refs if source_project is available
    if source_project and feature.code_refs:
        try:
            hydrated = feature.hydrate_code(source_project.path)
            for code in hydrated.values():
                total_tokens += count_tokens(code)
        except Exception as e:
            import sys; print(f'[EriRPG] hydration error: {e}', file=sys.stderr)
            # Fall back to snapshots if hydration fails
            for code in feature.code.values():
                total_tokens += count_tokens(code)
    else:
        # Use snapshots
        for code in feature.code.values():
            total_tokens += count_tokens(code)

    # If no code and we have refs, estimate (this is the only estimation)
    if total_tokens == 0 and feature.code_refs:
        # Estimate ~500 tokens per file as fallback
        total_tokens = len(feature.code_refs) * 500

    # Count plan tokens
    plan_text = str(plan.mappings) + str(plan.wiring)
    total_tokens += count_tokens(plan_text)

    # Add fixed overhead for header, instructions, etc.
    total_tokens += RESERVED_HEADER + RESERVED_INSTRUCTIONS

    return total_tokens
