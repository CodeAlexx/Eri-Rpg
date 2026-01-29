"""
Dynamic context builder for EriRPG.

This is the core of EriRPG's advantage over SuperClaude:
- SuperClaude loads ~20k static tokens every time
- EriRPG builds ~2-3k dynamic tokens from actual project knowledge

The context is:
1. Project-aware (uses StoredLearnings, patterns, decisions)
2. Stage-aware (knows what phase of work we're in)
3. Persona-aware (adjusts framing based on current persona)
4. Task-aware (includes current goal, must_haves, roadmap)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .persona import Persona, get_persona, PersonaConfig
from .workflow import Stage, get_persona_for_stage, get_stage_description
from .commands import get_help_text


@dataclass
class SessionContext:
    """All context needed for current session."""
    # Core identity
    project_name: str
    project_path: str = ""
    project_description: str = ""

    # Current state
    stage: Stage = Stage.IDLE
    persona: Persona = None
    persona_override: bool = False  # True if persona was explicitly set

    # Project knowledge
    learned_patterns: List[str] = field(default_factory=list)
    recent_decisions: List[str] = field(default_factory=list)
    key_modules: List[str] = field(default_factory=list)

    # Current task
    current_task: Optional[str] = None
    must_haves: List[str] = field(default_factory=list)
    roadmap_summary: Optional[str] = None

    # Session metadata
    started_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Default persona from stage if not set
        if self.persona is None:
            self.persona = get_persona_for_stage(self.stage)

    def set_stage(self, stage: Stage) -> None:
        """Set stage and update persona (unless overridden)."""
        self.stage = stage
        if not self.persona_override:
            self.persona = get_persona_for_stage(stage)

    def set_persona(self, persona: Persona, override: bool = True) -> None:
        """Set persona explicitly."""
        self.persona = persona
        self.persona_override = override

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "project_description": self.project_description,
            "stage": self.stage.name,
            "persona": self.persona.name,
            "persona_override": self.persona_override,
            "learned_patterns": self.learned_patterns,
            "recent_decisions": self.recent_decisions,
            "key_modules": self.key_modules,
            "current_task": self.current_task,
            "must_haves": self.must_haves,
            "roadmap_summary": self.roadmap_summary,
            "started_at": self.started_at.isoformat(),
        }


def build_context(ctx: SessionContext, compact: bool = False) -> str:
    """
    Build dynamic context string.
    This is what gets injected into Claude's context.

    Args:
        ctx: SessionContext with all state
        compact: If True, minimize token usage

    Returns:
        Markdown-formatted context string
    """
    sections = []

    # Header
    sections.append(f"# {ctx.project_name}")
    if ctx.project_description and not compact:
        sections.append(f"\n{ctx.project_description}\n")

    # Current state
    persona_config = get_persona(ctx.persona)
    stage_desc = get_stage_description(ctx.stage)

    if compact:
        sections.append(f"\n**Stage**: {ctx.stage.name} | **Persona**: {persona_config.name}")
        sections.append(f"\n{persona_config.identity}")
    else:
        sections.append(f"""
## Session State
- **Stage**: {ctx.stage.name} - {stage_desc}
- **Persona**: {persona_config.name}

{persona_config.to_prompt()}
""")

    # Current task (if any)
    if ctx.current_task:
        sections.append(f"\n## Current Task\n{ctx.current_task}")
        if ctx.must_haves:
            sections.append("\n**Must-haves**:")
            for mh in ctx.must_haves:
                sections.append(f"- [ ] {mh}")
        sections.append("")

    # Roadmap (if any)
    if ctx.roadmap_summary and not compact:
        sections.append(f"\n## Roadmap\n{ctx.roadmap_summary}\n")

    # Learned patterns (project-specific knowledge)
    if ctx.learned_patterns:
        limit = 5 if compact else 10
        sections.append("\n## Codebase Patterns")
        if not compact:
            sections.append("*Patterns learned from this codebase:*\n")
        for pattern in ctx.learned_patterns[:limit]:
            sections.append(f"- {pattern}")
        if len(ctx.learned_patterns) > limit:
            sections.append(f"- ... and {len(ctx.learned_patterns) - limit} more")
        sections.append("")

    # Key modules
    if ctx.key_modules and not compact:
        sections.append("\n## Key Modules")
        for mod in ctx.key_modules[:10]:
            sections.append(f"- `{mod}`")
        sections.append("")

    # Recent decisions
    if ctx.recent_decisions:
        limit = 3 if compact else 5
        sections.append("\n## Recent Decisions")
        for decision in ctx.recent_decisions[-limit:]:
            sections.append(f"- {decision}")
        sections.append("")

    # Commands reference (minimal)
    if not compact:
        sections.append("""
## Commands
`/analyze` `/discuss` `/implement` `/review` `/debug` - workflow stages
`/architect` `/dev` `/critic` `/mentor` - persona overrides
`/roadmap` `/status` `/learn` `/context` `/help` - project management
""")

    return "\n".join(sections)


def build_minimal_context(persona: Persona) -> str:
    """
    Build minimal context when no project is loaded.
    Still better than SuperClaude because it's focused.
    """
    config = get_persona(persona)
    return f"""# EriRPG Session

{config.to_prompt()}

## Commands
`/analyze` `/discuss` `/implement` `/review` `/debug` - workflow stages
`/architect` `/dev` `/critic` - persona overrides
`/help` - show all commands
"""


def context_from_knowledge_store(
    project_path: str,
    project_name: str,
    stage: Stage = Stage.IDLE,
    persona: Persona = None,
    current_task: str = None,
) -> SessionContext:
    """
    Build SessionContext from EriRPG knowledge store.

    This integrates with existing StoredLearnings, patterns,
    and decisions from knowledge.json.
    """
    from .memory import load_knowledge

    store = load_knowledge(project_path, project_name)

    # Extract patterns from learnings
    patterns = []
    key_modules = []
    for module_path, learning in list(store.learnings.items())[:20]:
        key_modules.append(module_path)
        if learning.gotchas:
            for gotcha in learning.gotchas[:2]:
                patterns.append(f"{module_path}: {gotcha}")
        if learning.implements:
            patterns.append(f"{module_path} implements {learning.implements}")

    # Extract decisions
    decisions = []
    for decision in store.decisions[-10:]:
        decisions.append(f"{decision.title}: {decision.reason[:100]}")

    # Extract from patterns dict
    for name, desc in list(store.patterns.items())[:5]:
        patterns.append(f"Pattern '{name}': {desc[:80]}")

    return SessionContext(
        project_name=project_name,
        project_path=project_path,
        stage=stage,
        persona=persona or get_persona_for_stage(stage),
        learned_patterns=patterns[:15],
        recent_decisions=decisions[:5],
        key_modules=key_modules[:10],
        current_task=current_task,
    )
