"""
Spec-driven execution format for EriRPG.

This replaces ad-hoc goal-based execution with structured specs.
Claude Code follows the spec. Step by step. No freestyling.

Usage:
    spec = Spec.generate(goal, project, graph, knowledge)
    spec.save(".eri-rpg/spec.yaml")

    # Or load existing
    spec = Spec.load(".eri-rpg/spec.yaml")
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import yaml
import hashlib

if TYPE_CHECKING:
    from erirpg.graph import Graph
    from erirpg.memory import KnowledgeStore


@dataclass
class Step:
    """A single step in an execution spec.

    Each step has:
    - Clear action type
    - Explicit file targets
    - Verification criteria
    - Dependencies on other steps
    """
    id: str
    action: str  # learn | refactor | create | modify | delete | verify
    targets: List[str]  # files to touch
    description: str
    depends_on: List[str] = field(default_factory=list)  # step ids
    verification: str = ""  # how to verify success

    # Execution state
    status: str = "pending"  # pending | in_progress | completed | failed | skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Results
    files_modified: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "targets": self.targets,
            "description": self.description,
            "depends_on": self.depends_on,
            "verification": self.verification,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "files_modified": self.files_modified,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Step":
        return cls(
            id=d["id"],
            action=d["action"],
            targets=d.get("targets", []),
            description=d.get("description", ""),
            depends_on=d.get("depends_on", []),
            verification=d.get("verification", ""),
            status=d.get("status", "pending"),
            started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
            error=d.get("error"),
            files_modified=d.get("files_modified", []),
            notes=d.get("notes", ""),
        )

    def is_blocked(self, completed_steps: List[str]) -> bool:
        """Check if this step is blocked by incomplete dependencies."""
        for dep in self.depends_on:
            if dep not in completed_steps:
                return True
        return False


@dataclass
class SpecStep:
    """A goal-based step (legacy/compatibility format).

    This is the simpler goal-oriented step format used in agent workflows.
    Maps to Step with action="execute".
    """
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

    def to_step(self) -> Step:
        """Convert to action-based Step."""
        return Step(
            id=self.id,
            action="execute",
            targets=self.context_files,
            description=f"{self.goal}: {self.description}" if self.description else self.goal,
            verification=self.verification[0] if self.verification else "",
        )


@dataclass
class Spec:
    """A complete execution specification.

    Contains:
    - Goal description
    - Ordered steps with dependencies
    - Global verification

    Supports both action-based steps (Step) and goal-based steps (SpecStep).
    """
    id: str
    goal: str
    project: str
    steps: List[Step] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    verification: List[str] = field(default_factory=list)  # global verification commands
    constraints: List[str] = field(default_factory=list)

    # Legacy/compatibility fields from agent/spec.py
    source_project: Optional[str] = None
    target_project: Optional[str] = None
    context_hints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    spec_path: Optional[str] = None

    # State tracking
    current_step_id: Optional[str] = None

    @classmethod
    def generate(
        cls,
        goal: str,
        project: str,
        graph: Optional["Graph"] = None,
        knowledge: Optional["KnowledgeStore"] = None,
    ) -> "Spec":
        """
        Analyze goal + codebase, generate concrete steps.

        This is the intelligence layer that turns a goal into
        an ordered list of steps with proper dependencies.
        """
        from erirpg.planner import Planner

        planner = Planner(project, graph, knowledge)
        return planner.plan(goal)

    @classmethod
    def load(cls, path: str) -> "Spec":
        """Load spec from YAML file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Spec not found: {path}")

        with open(p) as f:
            data = yaml.safe_load(f) or {}

        steps = [Step.from_dict(s) for s in data.get("steps", [])]

        spec = cls(
            id=data.get("id", ""),
            goal=data.get("goal", ""),
            project=data.get("project", ""),
            steps=steps,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            verification=data.get("verification", []),
            constraints=data.get("constraints", []),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
            current_step_id=data.get("current_step_id"),
        )
        spec.spec_path = str(p.absolute())
        return spec

    # Compatibility aliases for agent/spec.py
    @classmethod
    def from_file(cls, path: str) -> "Spec":
        """Load spec from YAML file (alias for load())."""
        return cls.load(path)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Spec":
        """Create spec from dictionary."""
        steps = [Step.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=data.get("id", generate_spec_id(data.get("goal", ""))),
            goal=data.get("goal", ""),
            project=data.get("project", ""),
            steps=steps,
            verification=data.get("verification", []),
            constraints=data.get("constraints", []),
            source_project=data.get("source_project"),
            target_project=data.get("target_project"),
            context_hints=data.get("context", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_goal(cls, goal: str, project: str = "", **kwargs) -> "Spec":
        """Create spec from a simple goal string."""
        return cls(
            id=generate_spec_id(goal),
            goal=goal,
            project=project,
            **kwargs,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = {
            "id": self.id,
            "goal": self.goal,
            "project": self.project,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "verification": self.verification,
            "constraints": self.constraints,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "context": self.context_hints,
            "metadata": self.metadata,
            "current_step_id": self.current_step_id,
        }
        return d

    def save(self, path: str) -> None:
        """Save spec to YAML file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "id": self.id,
            "goal": self.goal,
            "project": self.project,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "verification": self.verification,
            "constraints": self.constraints,
            "current_step_id": self.current_step_id,
        }

        with open(p, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def current_step(self) -> Optional[Step]:
        """Get the current step being executed."""
        if self.current_step_id:
            return self.get_step(self.current_step_id)
        return self.next_step()

    def next_step(self) -> Optional[Step]:
        """Get the next step to execute (respects dependencies)."""
        completed = [s.id for s in self.steps if s.status == "completed"]

        for step in self.steps:
            if step.status == "pending" and not step.is_blocked(completed):
                return step
        return None

    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return all(s.status in ("completed", "skipped") for s in self.steps)

    def progress(self) -> tuple:
        """Return (completed, total) step counts."""
        completed = len([s for s in self.steps if s.status in ("completed", "skipped")])
        return completed, len(self.steps)

    def start_step(self, step_id: str) -> Optional[Step]:
        """Mark a step as in progress."""
        step = self.get_step(step_id)
        if step:
            step.status = "in_progress"
            step.started_at = datetime.now()
            self.current_step_id = step_id
        return step

    def complete_step(self, step_id: str, files_modified: List[str] = None, notes: str = "") -> Optional[Step]:
        """Mark a step as completed."""
        step = self.get_step(step_id)
        if step:
            step.status = "completed"
            step.completed_at = datetime.now()
            step.files_modified = files_modified or []
            step.notes = notes
            self.current_step_id = None
        return step

    def fail_step(self, step_id: str, error: str) -> Optional[Step]:
        """Mark a step as failed."""
        step = self.get_step(step_id)
        if step:
            step.status = "failed"
            step.completed_at = datetime.now()
            step.error = error
        return step

    def format_status(self) -> str:
        """Format spec status for display."""
        lines = [
            f"{'═' * 50}",
            f" SPEC: {self.goal[:40]}{'...' if len(self.goal) > 40 else ''}",
            f"{'═' * 50}",
            f"Project: {self.project}",
            f"ID: {self.id}",
            "",
        ]

        completed, total = self.progress()
        lines.append(f"Progress: {completed}/{total} steps")
        lines.append("")

        for step in self.steps:
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "failed": "✗",
                "skipped": "◌",
            }.get(step.status, "?")

            lines.append(f"  {status_icon} [{step.id}] {step.action}: {step.description[:40]}")
            if step.depends_on:
                lines.append(f"      depends: {', '.join(step.depends_on)}")
            if step.error:
                lines.append(f"      error: {step.error}")

        lines.append("")

        current = self.current_step()
        if current:
            lines.append(f"Next: {current.action} - {current.description}")
            if current.targets:
                lines.append(f"  Targets: {', '.join(current.targets[:3])}")
            if current.verification:
                lines.append(f"  Verify: {current.verification}")
        elif self.is_complete():
            lines.append("✓ COMPLETE")
        else:
            failed = [s for s in self.steps if s.status == "failed"]
            if failed:
                lines.append(f"✗ BLOCKED - {len(failed)} step(s) failed")

        return "\n".join(lines)


def generate_spec_id(goal: str) -> str:
    """Generate a unique spec ID from goal."""
    return hashlib.sha256(
        f"{goal}:{datetime.now().isoformat()}".encode()
    ).hexdigest()[:12]
