"""
Workflow stage management with persona integration.

Maps workflow stages to default personas - the key insight that makes
EriRPG smarter than static persona selection.

When you're analyzing, you think like an architect.
When you're implementing, you think like a dev.
When you're reviewing, you think like a critic.
"""

from enum import Enum, auto
from typing import Optional

from .persona import Persona, get_persona, PersonaConfig


class Stage(Enum):
    """
    Workflow stages - each implies a default persona.
    These map to the natural phases of development work.
    """
    IDLE = auto()       # Ready for new task
    ANALYZE = auto()    # Understanding codebase, patterns, structure
    DISCUSS = auto()    # Planning approach, generating roadmap
    IMPLEMENT = auto()  # Writing code to spec
    REVIEW = auto()     # Critiquing work, finding issues
    DEBUG = auto()      # Investigating problems, finding root cause


# Stage to persona mapping - the key insight
# Each stage has a natural way of thinking
STAGE_PERSONA: dict[Stage, Persona] = {
    Stage.IDLE: Persona.DEV,           # Default: ready to build
    Stage.ANALYZE: Persona.ARCHITECT,  # Understanding requires systems thinking
    Stage.DISCUSS: Persona.ARCHITECT,  # Planning requires design thinking
    Stage.IMPLEMENT: Persona.DEV,      # Building requires pragmatic thinking
    Stage.REVIEW: Persona.CRITIC,      # Reviewing requires critical thinking
    Stage.DEBUG: Persona.ANALYST,      # Debugging requires detective thinking
}


# Stage descriptions for UI/context
STAGE_DESCRIPTIONS: dict[Stage, str] = {
    Stage.IDLE: "Ready for new task",
    Stage.ANALYZE: "Understanding codebase structure and patterns",
    Stage.DISCUSS: "Planning approach, generating roadmap",
    Stage.IMPLEMENT: "Writing code to spec",
    Stage.REVIEW: "Critiquing work, finding issues",
    Stage.DEBUG: "Investigating problems, finding root cause",
}


# Stage transitions - what stages can follow what
STAGE_TRANSITIONS: dict[Stage, list[Stage]] = {
    Stage.IDLE: [Stage.ANALYZE, Stage.DISCUSS, Stage.IMPLEMENT, Stage.DEBUG],
    Stage.ANALYZE: [Stage.DISCUSS, Stage.IMPLEMENT, Stage.IDLE],
    Stage.DISCUSS: [Stage.IMPLEMENT, Stage.ANALYZE, Stage.IDLE],
    Stage.IMPLEMENT: [Stage.REVIEW, Stage.DEBUG, Stage.IDLE],
    Stage.REVIEW: [Stage.IMPLEMENT, Stage.IDLE],  # Back to implement for fixes
    Stage.DEBUG: [Stage.IMPLEMENT, Stage.ANALYZE, Stage.IDLE],
}


def get_persona_for_stage(stage: Stage) -> Persona:
    """Get the default persona for a workflow stage."""
    return STAGE_PERSONA.get(stage, Persona.DEV)


def get_stage_description(stage: Stage) -> str:
    """Human-readable stage description."""
    return STAGE_DESCRIPTIONS.get(stage, "Unknown stage")


def get_stage_by_name(name: str) -> Optional[Stage]:
    """Get stage enum by name string."""
    name_lower = name.lower()
    for stage in Stage:
        if stage.name.lower() == name_lower:
            return stage
    return None


def list_stages() -> list[str]:
    """List all available stage names."""
    return [s.name.lower() for s in Stage]


def can_transition(from_stage: Stage, to_stage: Stage) -> bool:
    """Check if a stage transition is valid."""
    allowed = STAGE_TRANSITIONS.get(from_stage, [])
    return to_stage in allowed


def get_next_stages(current: Stage) -> list[Stage]:
    """Get valid next stages from current stage."""
    return STAGE_TRANSITIONS.get(current, [])


def detect_stage_from_input(user_input: str) -> Optional[Stage]:
    """
    Detect workflow stage from user input.
    Returns None if no clear stage detected.
    """
    input_lower = user_input.lower()

    # Stage trigger patterns
    stage_triggers = {
        Stage.ANALYZE: ["analyze", "understand", "explore", "structure", "how does", "what is"],
        Stage.DISCUSS: ["plan", "discuss", "roadmap", "approach", "strategy", "design"],
        Stage.IMPLEMENT: ["implement", "build", "create", "write", "add", "make", "code"],
        Stage.REVIEW: ["review", "check", "audit", "verify", "validate", "assess"],
        Stage.DEBUG: ["debug", "fix", "broken", "error", "bug", "why", "trace", "investigate"],
    }

    for stage, triggers in stage_triggers.items():
        for trigger in triggers:
            if trigger in input_lower:
                return stage

    return None
