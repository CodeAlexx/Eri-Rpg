"""
Discussion context output.

Generates CONTEXT.md from discussion phase.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from erirpg.discovery import detect_discovery_level, is_discretion_answer


@dataclass
class DiscussionContext:
    """Context extracted from discussion phase."""
    phase_id: str
    goal: str
    phase_boundary: str           # What this phase delivers
    decisions: Dict[str, List[str]] = field(default_factory=dict)  # Category → decisions
    claudes_discretion: List[str] = field(default_factory=list)    # "you decide" items
    deferred_ideas: List[str] = field(default_factory=list)
    discovery_level: int = 0
    discovery_reason: str = ""

    def to_markdown(self) -> str:
        """Generate CONTEXT.md content."""
        lines = [
            f"# Context: {self.goal}",
            "",
            f"**Phase ID:** {self.phase_id}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Phase Boundary",
            "",
            self.phase_boundary if self.phase_boundary else "_Not defined_",
            "",
        ]

        # Decisions by category
        if self.decisions:
            lines.append("## Decisions")
            lines.append("")
            for category, items in self.decisions.items():
                lines.append(f"### {category}")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        # Claude's discretion
        if self.claudes_discretion:
            lines.append("### Claude's Discretion")
            lines.append("")
            for item in self.claudes_discretion:
                lines.append(f"- {item}")
            lines.append("")

        # Deferred
        if self.deferred_ideas:
            lines.append("## Deferred")
            lines.append("")
            for idea in self.deferred_ideas:
                lines.append(f"- {idea}")
            lines.append("")

        # Research recommendation
        lines.append("## Research Recommendation")
        lines.append("")
        level_desc = {
            0: "Skip (internal work)",
            1: "Quick (single lib lookup)",
            2: "Standard (choosing options)",
            3: "Deep (architectural)",
        }
        lines.append(f"**Level:** {self.discovery_level} - {level_desc.get(self.discovery_level, 'Unknown')}")
        if self.discovery_reason:
            lines.append(f"**Reason:** {self.discovery_reason}")
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "goal": self.goal,
            "phase_boundary": self.phase_boundary,
            "decisions": self.decisions,
            "claudes_discretion": self.claudes_discretion,
            "deferred_ideas": self.deferred_ideas,
            "discovery_level": self.discovery_level,
            "discovery_reason": self.discovery_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DiscussionContext":
        return cls(
            phase_id=d["phase_id"],
            goal=d["goal"],
            phase_boundary=d.get("phase_boundary", ""),
            decisions=d.get("decisions", {}),
            claudes_discretion=d.get("claudes_discretion", []),
            deferred_ideas=d.get("deferred_ideas", []),
            discovery_level=d.get("discovery_level", 0),
            discovery_reason=d.get("discovery_reason", ""),
        )

    def save(self, output_dir: str) -> tuple:
        """
        Save context to files.

        Args:
            output_dir: Directory to save to (e.g., .eri-rpg/phases/{id}/)

        Returns:
            (markdown_path, json_path)
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        md_path = os.path.join(output_dir, "CONTEXT.md")
        json_path = os.path.join(output_dir, "context.json")

        with open(md_path, "w") as f:
            f.write(self.to_markdown())

        with open(json_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return md_path, json_path

    @classmethod
    def load(cls, output_dir: str) -> Optional["DiscussionContext"]:
        """Load context from JSON file."""
        json_path = os.path.join(output_dir, "context.json")
        if not os.path.exists(json_path):
            return None
        with open(json_path) as f:
            return cls.from_dict(json.load(f))


def build_discussion_context(
    phase_id: str,
    goal: str,
    phase_boundary: str = "",
    decisions: Dict[str, List[str]] = None,
    answers: Dict[str, str] = None,
    deferred: List[str] = None,
    known_deps: set = None,
) -> DiscussionContext:
    """
    Build discussion context from phase outputs.

    Args:
        phase_id: Unique phase identifier
        goal: The goal being discussed
        phase_boundary: What this phase delivers
        decisions: Category → list of decisions made
        answers: Question → answer pairs (to detect discretion)
        deferred: Ideas deferred for later
        known_deps: Dependencies already known to project

    Returns:
        DiscussionContext ready to save
    """
    decisions = decisions or {}
    answers = answers or {}
    deferred = deferred or []
    known_deps = known_deps or set()

    # Detect discovery level
    level, reason = detect_discovery_level(goal, known_deps)

    # Extract "Claude's discretion" items from answers
    discretion = []
    for question, answer in answers.items():
        if is_discretion_answer(answer):
            discretion.append(question)

    return DiscussionContext(
        phase_id=phase_id,
        goal=goal,
        phase_boundary=phase_boundary,
        decisions=decisions,
        claudes_discretion=discretion,
        deferred_ideas=deferred,
        discovery_level=level,
        discovery_reason=reason,
    )
