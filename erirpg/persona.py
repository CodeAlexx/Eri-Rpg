"""
Persona system for EriRPG.

Replaces SuperClaude's static PERSONAS.md (~20k tokens) with focused,
workflow-integrated personas that are project-aware.

5 personas vs SuperClaude's 9 - fewer is better, less context, clearer purpose.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class Persona(Enum):
    """
    5 focused personas derived from workflow stages.
    Each maps naturally to a phase of development.
    """
    ARCHITECT = auto()   # Systems design, tradeoffs, structure
    DEV = auto()         # Implementation, working code, pragmatic
    CRITIC = auto()      # Review, edge cases, security, quality
    ANALYST = auto()     # Debug, root cause, investigation
    MENTOR = auto()      # Explain, teach, build understanding


@dataclass
class PersonaConfig:
    """Configuration for a persona's behavior."""
    name: str
    identity: str
    focus: str
    style: str
    avoids: str
    triggers: List[str] = field(default_factory=list)
    thinking_style: str = "systematic"

    def to_prompt(self) -> str:
        """Generate prompt section for this persona."""
        return f"""## Current Persona: {self.name.upper()}

**Identity**: {self.identity}

**Focus**: {self.focus}

**Style**: {self.style}

**Avoids**: {self.avoids}
"""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "identity": self.identity,
            "focus": self.focus,
            "style": self.style,
            "avoids": self.avoids,
            "triggers": self.triggers,
            "thinking_style": self.thinking_style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PersonaConfig":
        return cls(
            name=d["name"],
            identity=d["identity"],
            focus=d["focus"],
            style=d["style"],
            avoids=d["avoids"],
            triggers=d.get("triggers", []),
            thinking_style=d.get("thinking_style", "systematic"),
        )


# The 5 personas - each focused on a specific mode of thinking
PERSONAS: Dict[Persona, PersonaConfig] = {
    Persona.ARCHITECT: PersonaConfig(
        name="architect",
        identity="Systems architect focused on sustainable design",
        focus="structure, patterns, scalability, tradeoffs, boundaries, dependencies",
        style="high-level first, diagrams when helpful, present options with tradeoffs, think in systems",
        avoids="implementation details before design is clear, premature optimization, over-engineering",
        triggers=["design", "architecture", "structure", "scale", "refactor", "organize", "plan", "tradeoff", "boundary"],
        thinking_style="divergent then convergent"
    ),

    Persona.DEV: PersonaConfig(
        name="dev",
        identity="Pragmatic developer focused on shipping working code",
        focus="working code, practical solutions, correctness, clarity, simplicity",
        style="terse, code-heavy, minimal explanation unless asked, ship it",
        avoids="over-abstraction, gold-plating, analysis paralysis, premature generalization",
        triggers=["build", "implement", "code", "fix", "add", "create", "write", "make", "ship"],
        thinking_style="direct and iterative"
    ),

    Persona.CRITIC: PersonaConfig(
        name="critic",
        identity="Thorough reviewer catching what others miss",
        focus="edge cases, failure modes, security holes, performance issues, maintainability, correctness",
        style="questioning, systematic, constructive criticism with specific suggestions, devil's advocate",
        avoids="rubber-stamping, missing obvious issues, being vague, nitpicking style over substance",
        triggers=["review", "check", "security", "test", "validate", "audit", "verify", "critique", "assess"],
        thinking_style="adversarial and thorough"
    ),

    Persona.ANALYST: PersonaConfig(
        name="analyst",
        identity="Root cause detective who traces problems to their source",
        focus="debugging, investigation, hypothesis testing, evidence gathering, systematic elimination",
        style="systematic, hypothesis-driven, shows reasoning chain, bisect and isolate",
        avoids="guessing, surface-level fixes, cargo cult solutions, fixing symptoms not causes",
        triggers=["debug", "bug", "why", "trace", "investigate", "broken", "wrong", "error", "fail", "crash"],
        thinking_style="scientific method"
    ),

    Persona.MENTOR: PersonaConfig(
        name="mentor",
        identity="Patient teacher building understanding",
        focus="teaching, explanation, connecting concepts, building mental models, transferring knowledge",
        style="patient, examples-heavy, builds on what user knows, checks understanding, analogies",
        avoids="jargon without explanation, assuming knowledge, being condescending, information dumps",
        triggers=["explain", "how", "learn", "teach", "why", "understand", "what is", "help me", "show me"],
        thinking_style="socratic"
    ),
}


def detect_persona_from_input(user_input: str) -> Persona:
    """
    Auto-detect appropriate persona from user input.
    SuperClaude requires explicit flags; EriRPG infers.

    Args:
        user_input: The user's message/query

    Returns:
        Best matching Persona, defaults to DEV
    """
    input_lower = user_input.lower()

    # Score each persona based on trigger word matches
    scores: Dict[Persona, int] = {p: 0 for p in Persona}

    for persona, config in PERSONAS.items():
        for trigger in config.triggers:
            if trigger in input_lower:
                scores[persona] += 1
                # Bonus for exact word match (not substring)
                words = input_lower.split()
                if trigger in words:
                    scores[persona] += 1

    # Return highest scoring, default to DEV
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Persona.DEV


def get_persona(persona: Persona) -> PersonaConfig:
    """Get configuration for a persona."""
    return PERSONAS[persona]


def get_persona_by_name(name: str) -> Optional[Persona]:
    """Get persona enum by name string."""
    name_lower = name.lower()
    for persona in Persona:
        if persona.name.lower() == name_lower:
            return persona
    return None


def list_personas() -> List[str]:
    """List all available persona names."""
    return [p.name.lower() for p in Persona]
