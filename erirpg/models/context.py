"""
Context model for implementation decisions.

CONTEXT.md captures decisions made during phase discussion:
- Technology choices
- Architecture decisions
- Implementation approach
- Constraints and assumptions
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class ContextDecision:
    """A decision captured during discussion."""
    id: str
    topic: str  # What the decision is about
    decision: str  # What was decided
    rationale: str = ""  # Why this decision
    alternatives: List[str] = field(default_factory=list)  # Alternatives considered
    constraints: List[str] = field(default_factory=list)  # Constraints that influenced
    decided_at: Optional[str] = None

    def __post_init__(self):
        if not self.decided_at:
            self.decided_at = datetime.now().isoformat()
        if not self.id:
            import hashlib
            data = f"{self.topic}:{self.decision}:{self.decided_at}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "constraints": self.constraints,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextDecision":
        return cls(
            id=data.get("id", ""),
            topic=data.get("topic", ""),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            alternatives=data.get("alternatives", []),
            constraints=data.get("constraints", []),
            decided_at=data.get("decided_at"),
        )

    def format_display(self) -> str:
        """Format decision for display."""
        lines = [
            f"### {self.topic}",
            "",
            f"**Decision:** {self.decision}",
        ]

        if self.rationale:
            lines.append(f"**Rationale:** {self.rationale}")

        if self.alternatives:
            lines.append("**Alternatives considered:**")
            for alt in self.alternatives:
                lines.append(f"  - {alt}")

        if self.constraints:
            lines.append("**Constraints:**")
            for c in self.constraints:
                lines.append(f"  - {c}")

        return "\n".join(lines)


@dataclass
class Context:
    """Implementation context for a phase.

    Captured during /eri:discuss-phase and stored as {phase}-CONTEXT.md.
    """
    phase: str
    title: str = ""  # Phase title

    # Overview
    goal: str = ""  # What this phase achieves
    scope: str = ""  # What's in/out of scope
    approach: str = ""  # High-level approach

    # Decisions
    decisions: List[ContextDecision] = field(default_factory=list)

    # Technical context
    dependencies: List[str] = field(default_factory=list)  # What this phase depends on
    provides: List[str] = field(default_factory=list)  # What this phase provides to others
    assumptions: List[str] = field(default_factory=list)  # Assumptions we're making
    risks: List[str] = field(default_factory=list)  # Identified risks

    # Questions resolved
    questions_asked: List[str] = field(default_factory=list)
    answers: Dict[str, str] = field(default_factory=dict)

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "title": self.title,
            "goal": self.goal,
            "scope": self.scope,
            "approach": self.approach,
            "decisions": [d.to_dict() for d in self.decisions],
            "dependencies": self.dependencies,
            "provides": self.provides,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "questions_asked": self.questions_asked,
            "answers": self.answers,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        return cls(
            phase=data.get("phase", ""),
            title=data.get("title", ""),
            goal=data.get("goal", ""),
            scope=data.get("scope", ""),
            approach=data.get("approach", ""),
            decisions=[ContextDecision.from_dict(d) for d in data.get("decisions", [])],
            dependencies=data.get("dependencies", []),
            provides=data.get("provides", []),
            assumptions=data.get("assumptions", []),
            risks=data.get("risks", []),
            questions_asked=data.get("questions_asked", []),
            answers=data.get("answers", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()

    def add_decision(
        self,
        topic: str,
        decision: str,
        rationale: str = "",
        alternatives: List[str] = None,
    ) -> ContextDecision:
        """Add a decision to the context."""
        d = ContextDecision(
            id="",
            topic=topic,
            decision=decision,
            rationale=rationale,
            alternatives=alternatives or [],
        )
        self.decisions.append(d)
        self._touch()
        return d

    def add_question_answer(self, question: str, answer: str) -> None:
        """Add a Q&A to the context."""
        self.questions_asked.append(question)
        self.answers[question] = answer
        self._touch()

    def format_display(self) -> str:
        """Format context for display."""
        lines = [
            f"# Context: {self.phase}",
            f"## {self.title}",
            "",
        ]

        if self.goal:
            lines.append("## Goal")
            lines.append(self.goal)
            lines.append("")

        if self.scope:
            lines.append("## Scope")
            lines.append(self.scope)
            lines.append("")

        if self.approach:
            lines.append("## Approach")
            lines.append(self.approach)
            lines.append("")

        if self.decisions:
            lines.append("## Decisions")
            for d in self.decisions:
                lines.append(d.format_display())
                lines.append("")

        if self.dependencies:
            lines.append("## Dependencies")
            for dep in self.dependencies:
                lines.append(f"- {dep}")
            lines.append("")

        if self.assumptions:
            lines.append("## Assumptions")
            for a in self.assumptions:
                lines.append(f"- {a}")
            lines.append("")

        if self.risks:
            lines.append("## Risks")
            for r in self.risks:
                lines.append(f"- {r}")
            lines.append("")

        return "\n".join(lines)


def save_context(project_path: str, context: Context) -> str:
    """Save context to project.

    Args:
        project_path: Path to project root
        context: Context to save

    Returns:
        Path to saved file
    """
    import os

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", context.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, f"{context.phase}-CONTEXT.json")
    with open(file_path, "w") as f:
        json.dump(context.to_dict(), f, indent=2)

    return file_path


def load_context(project_path: str, phase: str) -> Optional[Context]:
    """Load context from project.

    Args:
        project_path: Path to project root
        phase: Phase name

    Returns:
        Context if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "phases", phase, f"{phase}-CONTEXT.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return Context.from_dict(data)
