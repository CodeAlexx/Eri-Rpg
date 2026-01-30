"""
Plan model for ERI goal-backward methodology.

A Plan defines:
- Goal statement (outcome, not task)
- Must-haves: truths, artifacts, key_links
- Tasks to execute
- Verification criteria
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class PlanType(Enum):
    """Type of plan execution."""
    AUTONOMOUS = "autonomous"      # Fully automated
    CHECKPOINT = "checkpoint"      # Has human checkpoints
    USER_SETUP = "user_setup"     # Requires user setup first


@dataclass
class Truth:
    """An observable truth that must be verifiable after execution.

    Truths are user-observable outcomes, not implementation details.
    Example: "User can log in with email/password" not "Auth module exists"
    """
    id: str
    description: str
    verifiable_by: str = ""  # How to verify: "manual", "test", "observation"
    verified: bool = False
    verified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "verifiable_by": self.verifiable_by,
            "verified": self.verified,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Truth":
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            verifiable_by=data.get("verifiable_by", ""),
            verified=data.get("verified", False),
            verified_at=data.get("verified_at"),
        )


@dataclass
class Artifact:
    """A required artifact (file) that must exist after execution.

    Artifacts are specific files with minimum content requirements.
    """
    path: str
    provides: str  # What capability this file provides
    min_lines: int = 10  # Minimum lines (stubs usually < 10)
    exists: bool = False
    verified_at: Optional[str] = None
    actual_lines: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "provides": self.provides,
            "min_lines": self.min_lines,
            "exists": self.exists,
            "verified_at": self.verified_at,
            "actual_lines": self.actual_lines,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        return cls(
            path=data.get("path", ""),
            provides=data.get("provides", ""),
            min_lines=data.get("min_lines", 10),
            exists=data.get("exists", False),
            verified_at=data.get("verified_at"),
            actual_lines=data.get("actual_lines", 0),
        )


@dataclass
class KeyLink:
    """A required connection between components.

    Key links verify that components are actually wired together,
    not just existing independently.
    """
    from_component: str  # Source component/file
    to_component: str    # Target component/file
    via: str            # How they connect (import, API call, event, etc.)
    verified: bool = False
    verified_at: Optional[str] = None
    evidence: str = ""  # How verification was confirmed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_component,
            "to": self.to_component,
            "via": self.via,
            "verified": self.verified,
            "verified_at": self.verified_at,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyLink":
        return cls(
            from_component=data.get("from", ""),
            to_component=data.get("to", ""),
            via=data.get("via", ""),
            verified=data.get("verified", False),
            verified_at=data.get("verified_at"),
            evidence=data.get("evidence", ""),
        )


@dataclass
class MustHaves:
    """Required outcomes for plan success (goal-backward methodology).

    These are derived from the goal:
    1. State the Goal
    2. Derive Observable Truths (3-7)
    3. Derive Required Artifacts
    4. Derive Required Wiring (Key Links)
    """
    truths: List[Truth] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    key_links: List[KeyLink] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "truths": [t.to_dict() for t in self.truths],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "key_links": [k.to_dict() for k in self.key_links],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MustHaves":
        return cls(
            truths=[Truth.from_dict(t) for t in data.get("truths", [])],
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
            key_links=[KeyLink.from_dict(k) for k in data.get("key_links", [])],
        )

    def all_truths_verified(self) -> bool:
        """Check if all truths are verified."""
        return all(t.verified for t in self.truths)

    def all_artifacts_exist(self) -> bool:
        """Check if all artifacts exist."""
        return all(a.exists for a in self.artifacts)

    def all_links_verified(self) -> bool:
        """Check if all key links are verified."""
        return all(k.verified for k in self.key_links)

    def is_complete(self) -> bool:
        """Check if all must-haves are satisfied."""
        return (
            self.all_truths_verified() and
            self.all_artifacts_exist() and
            self.all_links_verified()
        )

    def get_gaps(self) -> Dict[str, List[str]]:
        """Get lists of unverified/missing items."""
        return {
            "truths": [t.description for t in self.truths if not t.verified],
            "artifacts": [a.path for a in self.artifacts if not a.exists],
            "key_links": [f"{k.from_component} → {k.to_component}" for k in self.key_links if not k.verified],
        }


@dataclass
class Plan:
    """An executable plan following goal-backward methodology.

    Plans are scoped to complete within ~50% context budget.
    Split triggers: >3 tasks, multiple subsystems, >5 files/task.
    """
    id: str
    phase: str  # Phase this plan belongs to
    plan_number: int  # Plan number within phase (01, 02, etc.)

    # Type and execution
    plan_type: PlanType = PlanType.AUTONOMOUS
    wave: int = 1  # Execution wave (parallel within same wave)
    depends_on: List[str] = field(default_factory=list)  # Plan IDs this depends on

    # Goal-backward methodology
    objective: str = ""  # The goal statement
    must_haves: MustHaves = field(default_factory=MustHaves)

    # Context for execution
    execution_context: str = ""  # What the executor needs to know
    context: str = ""  # Background information

    # Tasks (XML format in files, structured here)
    tasks: List[Dict[str, Any]] = field(default_factory=list)

    # Verification
    verification: List[str] = field(default_factory=list)  # Verification commands
    success_criteria: List[str] = field(default_factory=list)

    # Metadata
    files_modified: List[str] = field(default_factory=list)
    autonomous: bool = True  # Can run without human intervention
    user_setup: List[str] = field(default_factory=list)  # Setup required from user

    # Timestamps
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Status
    status: str = "pending"  # pending, in_progress, completed, failed

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase,
            "plan_number": self.plan_number,
            "plan_type": self.plan_type.value,
            "wave": self.wave,
            "depends_on": self.depends_on,
            "objective": self.objective,
            "must_haves": self.must_haves.to_dict(),
            "execution_context": self.execution_context,
            "context": self.context,
            "tasks": self.tasks,
            "verification": self.verification,
            "success_criteria": self.success_criteria,
            "files_modified": self.files_modified,
            "autonomous": self.autonomous,
            "user_setup": self.user_setup,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        plan_type_str = data.get("plan_type", "autonomous")
        try:
            plan_type = PlanType(plan_type_str)
        except ValueError:
            plan_type = PlanType.AUTONOMOUS

        return cls(
            id=data.get("id", ""),
            phase=data.get("phase", ""),
            plan_number=data.get("plan_number", 1),
            plan_type=plan_type,
            wave=data.get("wave", 1),
            depends_on=data.get("depends_on", []),
            objective=data.get("objective", ""),
            must_haves=MustHaves.from_dict(data.get("must_haves", {})),
            execution_context=data.get("execution_context", ""),
            context=data.get("context", ""),
            tasks=data.get("tasks", []),
            verification=data.get("verification", []),
            success_criteria=data.get("success_criteria", []),
            files_modified=data.get("files_modified", []),
            autonomous=data.get("autonomous", True),
            user_setup=data.get("user_setup", []),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            status=data.get("status", "pending"),
        )

    def get_plan_name(self) -> str:
        """Get the plan file name (e.g., '01-auth' for plan 1 in auth phase)."""
        return f"{self.plan_number:02d}-{self.phase}"

    def mark_started(self) -> None:
        """Mark plan as started."""
        self.status = "in_progress"
        self.started_at = datetime.now().isoformat()

    def mark_completed(self) -> None:
        """Mark plan as completed."""
        self.status = "completed"
        self.completed_at = datetime.now().isoformat()

    def mark_failed(self) -> None:
        """Mark plan as failed."""
        self.status = "failed"
        self.completed_at = datetime.now().isoformat()

    def is_ready(self, completed_plans: List[str]) -> bool:
        """Check if this plan is ready to execute (all dependencies complete)."""
        if not self.depends_on:
            return True
        return all(dep in completed_plans for dep in self.depends_on)

    def validate(self) -> List[str]:
        """Validate plan structure. Returns list of errors."""
        errors = []

        if not self.objective:
            errors.append("Plan has no objective")

        if not self.must_haves.truths:
            errors.append("Plan has no observable truths")

        if len(self.must_haves.truths) > 7:
            errors.append("Plan has too many truths (max 7)")

        if len(self.tasks) > 3:
            errors.append("Plan has too many tasks (max 3) - consider splitting")

        # Check for task completeness
        for i, task in enumerate(self.tasks):
            if not task.get("name"):
                errors.append(f"Task {i} has no name")
            if not task.get("action"):
                errors.append(f"Task {i} has no action")
            if task.get("type") == "auto":
                if not task.get("files"):
                    errors.append(f"Task {i} (auto) has no files")
                if not task.get("verify"):
                    errors.append(f"Task {i} (auto) has no verify")
                if not task.get("done"):
                    errors.append(f"Task {i} (auto) has no done criteria")

        return errors


def save_plan(project_path: str, plan: Plan) -> str:
    """Save a plan to the project's phases directory.

    Args:
        project_path: Path to project root
        plan: Plan to save

    Returns:
        Path to saved file
    """
    import os

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", plan.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, f"{plan.get_plan_name()}-PLAN.json")
    with open(file_path, "w") as f:
        json.dump(plan.to_dict(), f, indent=2)

    return file_path


def load_plan(project_path: str, phase: str, plan_number: int) -> Optional[Plan]:
    """Load a plan from the project's phases directory.

    Args:
        project_path: Path to project root
        phase: Phase name
        plan_number: Plan number within phase

    Returns:
        Plan if found, None otherwise
    """
    import os
    import glob

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", phase)
    pattern = os.path.join(phase_dir, f"{plan_number:02d}-*-PLAN.json")

    matches = glob.glob(pattern)
    if not matches:
        return None

    with open(matches[0], "r") as f:
        data = json.load(f)

    return Plan.from_dict(data)


def list_plans(project_path: str, phase: str) -> List[Plan]:
    """List all plans for a phase.

    Args:
        project_path: Path to project root
        phase: Phase name

    Returns:
        List of plans sorted by plan_number
    """
    import os
    import glob

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", phase)
    pattern = os.path.join(phase_dir, "*-PLAN.json")

    plans = []
    for file_path in glob.glob(pattern):
        with open(file_path, "r") as f:
            data = json.load(f)
        plans.append(Plan.from_dict(data))

    return sorted(plans, key=lambda p: p.plan_number)
