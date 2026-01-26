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
class SpecStep:
    """A step defined in the spec file."""
    id: str
    goal: str
    description: str = ""
    context_files: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpecStep":
        return cls(
            id=d.get("id", ""),
            goal=d.get("goal", ""),
            description=d.get("description", ""),
            context_files=d.get("context_files", []),
            verification=d.get("verification", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "description": self.description,
            "context_files": self.context_files,
            "verification": self.verification,
        }


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
    steps: List[SpecStep] = field(default_factory=list)  # Custom steps

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

        # Parse custom steps if provided
        steps = []
        for s in data.get("steps", []):
            steps.append(SpecStep.from_dict(s))

        return cls(
            goal=data.get("goal", ""),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            constraints=data.get("constraints", []),
            verification=data.get("verification", []),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
            steps=steps,
            spec_path=str(p.absolute()),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Spec":
        """Create spec from dictionary."""
        steps = [SpecStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            goal=data.get("goal", ""),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            constraints=data.get("constraints", []),
            verification=data.get("verification", []),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
            steps=steps,
        )

    @classmethod
    def from_goal(cls, goal: str, **kwargs) -> "Spec":
        """Create spec from a simple goal string."""
        return cls(goal=goal, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = {
            "goal": self.goal,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "constraints": self.constraints,
            "verification": self.verification,
            "context": self.context_hints,
            "metadata": self.metadata,
        }
        if self.steps:
            d["steps"] = [s.to_dict() for s in self.steps]
        return d

    def save(self, path: str) -> None:
        """Save spec to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
