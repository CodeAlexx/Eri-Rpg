"""
Spec file parsing for agent-driven workflows.

Human writes a spec file, agent reads and executes.
No CLI involvement.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class Spec:
    """A goal specification for the agent."""

    goal: str
    source_project: Optional[str] = None
    target_project: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    context_hints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Path to spec file (for relative path resolution)
    spec_path: Optional[str] = None

    @classmethod
    def from_file(cls, path: str) -> "Spec":
        """Load spec from YAML file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Spec file not found: {path}")

        with open(p) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            goal=data.get("goal", ""),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            constraints=data.get("constraints", []),
            verification=data.get("verification", []),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
            spec_path=str(p.absolute()),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Spec":
        """Create spec from dictionary."""
        return cls(
            goal=data.get("goal", ""),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            constraints=data.get("constraints", []),
            verification=data.get("verification", []),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_goal(cls, goal: str, **kwargs) -> "Spec":
        """Create spec from a simple goal string."""
        return cls(goal=goal, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "goal": self.goal,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "constraints": self.constraints,
            "verification": self.verification,
            "context": self.context_hints,
            "metadata": self.metadata,
        }

    def save(self, path: str) -> None:
        """Save spec to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
