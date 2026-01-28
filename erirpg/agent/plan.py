"""
Plan generation from specs.

Converts a goal spec into executable steps.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import hashlib


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected in step graph."""
    def __init__(self, step_id: str):
        self.step_id = step_id
        super().__init__(f"Circular dependency detected at step: {step_id}")


@dataclass
class AvoidPattern:
    """A pattern to avoid during step execution."""
    pattern: str   # "Don't use raw SQL"
    reason: str    # "Use repository for testability"
    source: str    # "RESEARCH.md" | "previous_failure"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "reason": self.reason,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AvoidPattern":
        return cls(
            pattern=d["pattern"],
            reason=d["reason"],
            source=d["source"],
        )


@dataclass
class Step:
    """A single executable step in a plan."""

    id: str
    goal: str
    description: str
    order: int

    # What the agent needs to do this step
    context_files: List[str] = field(default_factory=list)
    knowledge_needed: List[str] = field(default_factory=list)

    # Execution state
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    files_touched: List[str] = field(default_factory=list)
    notes: str = ""
    error: Optional[str] = None

    # Verification
    verification_commands: List[str] = field(default_factory=list)
    verification_passed: Optional[bool] = None

    # Multi-agent support
    parallelizable: bool = False  # Can run in parallel with other parallelizable steps
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on

    # Research pipeline additions
    action: str = ""  # Specific instruction for this step
    avoid: List[AvoidPattern] = field(default_factory=list)  # Patterns to avoid
    done_criteria: str = ""  # Human-observable acceptance criteria
    checkpoint_type: Optional[str] = None  # "human-verify" | "decision" | None
    wave: int = 0  # Execution wave (set by compute_waves)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "description": self.description,
            "order": self.order,
            "context_files": self.context_files,
            "knowledge_needed": self.knowledge_needed,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files_touched": self.files_touched,
            "notes": self.notes,
            "error": self.error,
            "verification_commands": self.verification_commands,
            "verification_passed": self.verification_passed,
            "parallelizable": self.parallelizable,
            "depends_on": self.depends_on,
            "action": self.action,
            "avoid": [a.to_dict() for a in self.avoid],
            "done_criteria": self.done_criteria,
            "checkpoint_type": self.checkpoint_type,
            "wave": self.wave,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Step":
        return cls(
            id=d["id"],
            goal=d["goal"],
            description=d["description"],
            order=d["order"],
            context_files=d.get("context_files", []),
            knowledge_needed=d.get("knowledge_needed", []),
            status=StepStatus(d.get("status", "pending")),
            started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
            files_touched=d.get("files_touched", []),
            notes=d.get("notes", ""),
            error=d.get("error"),
            verification_commands=d.get("verification_commands", []),
            verification_passed=d.get("verification_passed"),
            parallelizable=d.get("parallelizable", False),
            depends_on=d.get("depends_on", []),
            action=d.get("action", ""),
            avoid=[AvoidPattern.from_dict(a) for a in d.get("avoid", [])],
            done_criteria=d.get("done_criteria", ""),
            checkpoint_type=d.get("checkpoint_type"),
            wave=d.get("wave", 0),
        )


@dataclass
class Plan:
    """An executable plan generated from a spec."""

    id: str
    goal: str
    steps: List[Step] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    # Global verification (run after all steps)
    final_verification: List[str] = field(default_factory=list)

    # Metadata
    source_project: Optional[str] = None
    target_project: Optional[str] = None
    constraints: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, goal: str, steps: List[Step], **kwargs) -> "Plan":
        """Create a new plan with generated ID."""
        plan_id = hashlib.sha256(f"{goal}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        return cls(id=plan_id, goal=goal, steps=steps, **kwargs)

    def current_step(self) -> Optional[Step]:
        """Get the current step to execute."""
        for step in self.steps:
            if step.status == StepStatus.IN_PROGRESS:
                return step
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    def next_step(self) -> Optional[Step]:
        """Get the next pending step."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return all(
            step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for step in self.steps
        )

    def completed_steps(self) -> List[Step]:
        """Get completed steps."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def failed_steps(self) -> List[Step]:
        """Get failed steps."""
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    def progress(self) -> tuple:
        """Return (completed, total) step counts."""
        completed = len([s for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)])
        return completed, len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "final_verification": self.final_verification,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "constraints": self.constraints,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Plan":
        return cls(
            id=d["id"],
            goal=d["goal"],
            steps=[Step.from_dict(s) for s in d.get("steps", [])],
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
            final_verification=d.get("final_verification", []),
            source_project=d.get("source_project"),
            target_project=d.get("target_project"),
            constraints=d.get("constraints", []),
        )

    def save(self, path: str) -> None:
        """Save plan to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Plan":
        """Load plan from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))

    @property
    def waves(self) -> Dict[int, List[Step]]:
        """Get steps grouped by wave number."""
        return compute_waves(self.steps)


def compute_waves(steps: List[Step]) -> Dict[int, List[Step]]:
    """
    Compute execution waves based on step dependencies.

    Steps with no dependencies go in wave 1.
    Steps depending on wave N steps go in wave N+1.

    Args:
        steps: List of steps with depends_on field

    Returns:
        Dict mapping wave number to list of steps

    Raises:
        CircularDependencyError: If circular dependencies detected
    """
    if not steps:
        return {}

    # Build lookup
    steps_by_id = {s.id: s for s in steps}
    step_to_wave: Dict[str, int] = {}
    visiting: set = set()  # Currently being visited (for cycle detection)
    visited: set = set()   # Fully processed

    def get_wave(step_id: str) -> int:
        """Recursively compute wave for a step."""
        if step_id in step_to_wave:
            return step_to_wave[step_id]

        if step_id in visiting:
            raise CircularDependencyError(step_id)

        if step_id not in steps_by_id:
            # Dependency not in step list, treat as resolved
            return 0

        visiting.add(step_id)
        step = steps_by_id[step_id]

        if not step.depends_on:
            wave = 1
        else:
            # Wave is max of dependency waves + 1
            dep_waves = [get_wave(dep_id) for dep_id in step.depends_on]
            wave = max(dep_waves) + 1

        visiting.remove(step_id)
        visited.add(step_id)
        step_to_wave[step_id] = wave
        step.wave = wave

        return wave

    # Compute waves for all steps
    for step in steps:
        get_wave(step.id)

    # Group by wave
    waves: Dict[int, List[Step]] = {}
    for step in steps:
        wave_num = step.wave
        if wave_num not in waves:
            waves[wave_num] = []
        waves[wave_num].append(step)

    return waves
