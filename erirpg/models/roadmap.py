"""
Roadmap model for phase planning and tracking.

ROADMAP.md is source of truth (human-editable).
roadmap.json is auto-generated for Claude to read.

Roadmap tracks:
- Phases with goals and success criteria
- Mappings to requirements (REQ-IDs)
- Phase status and dependencies
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class PhaseGoal:
    """A goal within a phase."""
    id: str
    description: str
    requirement_ids: List[str] = field(default_factory=list)  # REQ-IDs this maps to
    success_criteria: List[str] = field(default_factory=list)
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "requirement_ids": self.requirement_ids,
            "success_criteria": self.success_criteria,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseGoal":
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            requirement_ids=data.get("requirement_ids", []),
            success_criteria=data.get("success_criteria", []),
            completed=data.get("completed", False),
        )


@dataclass
class Phase:
    """A phase in the roadmap."""
    number: int  # Phase number (01, 02, etc.)
    name: str  # Phase name (e.g., "authentication")
    title: str  # Human-readable title

    # Goals and scope
    goals: List[PhaseGoal] = field(default_factory=list)
    description: str = ""

    # Status
    status: str = "pending"  # pending, in_progress, completed, blocked
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Planning
    estimated_plans: int = 0  # Estimated number of plans
    actual_plans: int = 0  # Actual plans created
    plans_completed: int = 0

    # Dependencies
    depends_on: List[int] = field(default_factory=list)  # Phase numbers this depends on

    def __post_init__(self):
        if not self.name:
            # Generate name from title
            self.name = self.title.lower().replace(" ", "-").replace("_", "-")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "title": self.title,
            "goals": [g.to_dict() for g in self.goals],
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "estimated_plans": self.estimated_plans,
            "actual_plans": self.actual_plans,
            "plans_completed": self.plans_completed,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Phase":
        return cls(
            number=data.get("number", 0),
            name=data.get("name", ""),
            title=data.get("title", ""),
            goals=[PhaseGoal.from_dict(g) for g in data.get("goals", [])],
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            estimated_plans=data.get("estimated_plans", 0),
            actual_plans=data.get("actual_plans", 0),
            plans_completed=data.get("plans_completed", 0),
            depends_on=data.get("depends_on", []),
        )

    def get_phase_dir_name(self) -> str:
        """Get directory name for this phase (e.g., '02-authentication')."""
        return f"{self.number:02d}-{self.name}"

    def is_ready(self, completed_phases: List[int]) -> bool:
        """Check if this phase is ready to start."""
        if not self.depends_on:
            return True
        return all(dep in completed_phases for dep in self.depends_on)

    def mark_started(self) -> None:
        """Mark phase as started."""
        self.status = "in_progress"
        self.started_at = datetime.now().isoformat()

    def mark_completed(self) -> None:
        """Mark phase as completed."""
        self.status = "completed"
        self.completed_at = datetime.now().isoformat()

    def all_goals_completed(self) -> bool:
        """Check if all goals are completed."""
        return all(g.completed for g in self.goals)


@dataclass
class Milestone:
    """A milestone (version) grouping phases."""
    version: str  # e.g., "v1", "v2"
    name: str  # e.g., "MVP", "Beta"
    description: str = ""

    # Phase range
    start_phase: int = 0
    end_phase: int = 0

    # Status
    status: str = "pending"  # pending, in_progress, completed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "start_phase": self.start_phase,
            "end_phase": self.end_phase,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        return cls(
            version=data.get("version", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            start_phase=data.get("start_phase", 0),
            end_phase=data.get("end_phase", 0),
            status=data.get("status", "pending"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class Roadmap:
    """Complete project roadmap.

    Synced between ROADMAP.md (human-readable) and roadmap.json (machine-readable).
    ROADMAP.md is source of truth.
    """
    project_name: str

    # Milestones
    milestones: List[Milestone] = field(default_factory=list)

    # Phases
    phases: List[Phase] = field(default_factory=list)

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "milestones": [m.to_dict() for m in self.milestones],
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Roadmap":
        return cls(
            project_name=data.get("project_name", ""),
            milestones=[Milestone.from_dict(m) for m in data.get("milestones", [])],
            phases=[Phase.from_dict(p) for p in data.get("phases", [])],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()

    def get_phase(self, number: int) -> Optional[Phase]:
        """Get a phase by number."""
        for phase in self.phases:
            if phase.number == number:
                return phase
        return None

    def get_phase_by_name(self, name: str) -> Optional[Phase]:
        """Get a phase by name."""
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None

    def get_current_phase(self) -> Optional[Phase]:
        """Get the current (in_progress) phase."""
        for phase in self.phases:
            if phase.status == "in_progress":
                return phase
        return None

    def get_next_phase(self) -> Optional[Phase]:
        """Get the next phase to work on."""
        completed = [p.number for p in self.phases if p.status == "completed"]
        for phase in sorted(self.phases, key=lambda p: p.number):
            if phase.status == "pending" and phase.is_ready(completed):
                return phase
        return None

    def add_phase(self, phase: Phase) -> None:
        """Add a phase to the roadmap."""
        self.phases.append(phase)
        self.phases.sort(key=lambda p: p.number)
        self._touch()

    def insert_phase(self, after_number: int, phase: Phase) -> None:
        """Insert a phase after a given phase number.

        Renumbers subsequent phases.
        """
        phase.number = after_number + 1

        # Renumber phases after insertion point
        for p in self.phases:
            if p.number >= phase.number:
                p.number += 1

        self.phases.append(phase)
        self.phases.sort(key=lambda p: p.number)
        self._touch()

    def remove_phase(self, number: int) -> Optional[Phase]:
        """Remove a phase by number.

        Only removes pending phases. Renumbers subsequent phases.
        """
        phase = self.get_phase(number)
        if not phase:
            return None

        if phase.status != "pending":
            return None  # Can't remove non-pending phases

        self.phases.remove(phase)

        # Renumber phases after removal
        for p in self.phases:
            if p.number > number:
                p.number -= 1

        self._touch()
        return phase

    def get_completed_phases(self) -> List[Phase]:
        """Get all completed phases."""
        return [p for p in self.phases if p.status == "completed"]

    def get_pending_phases(self) -> List[Phase]:
        """Get all pending phases."""
        return [p for p in self.phases if p.status == "pending"]

    def get_milestone(self, version: str) -> Optional[Milestone]:
        """Get a milestone by version."""
        for milestone in self.milestones:
            if milestone.version == version:
                return milestone
        return None

    def get_phases_for_milestone(self, version: str) -> List[Phase]:
        """Get all phases for a milestone."""
        milestone = self.get_milestone(version)
        if not milestone:
            return []
        return [p for p in self.phases if milestone.start_phase <= p.number <= milestone.end_phase]


def load_roadmap(project_path: str) -> Optional[Roadmap]:
    """Load roadmap from project.

    Args:
        project_path: Path to project root

    Returns:
        Roadmap if found, None otherwise
    """
    import os

    roadmap_path = os.path.join(project_path, ".eri-rpg", "roadmap.json")
    if not os.path.exists(roadmap_path):
        return None

    with open(roadmap_path, "r") as f:
        data = json.load(f)

    return Roadmap.from_dict(data)


def save_roadmap(project_path: str, roadmap: Roadmap) -> str:
    """Save roadmap to project.

    Args:
        project_path: Path to project root
        roadmap: Roadmap to save

    Returns:
        Path to saved file
    """
    import os

    roadmap_dir = os.path.join(project_path, ".eri-rpg")
    os.makedirs(roadmap_dir, exist_ok=True)

    roadmap_path = os.path.join(roadmap_dir, "roadmap.json")
    roadmap._touch()

    with open(roadmap_path, "w") as f:
        json.dump(roadmap.to_dict(), f, indent=2)

    return roadmap_path


def init_roadmap(project_path: str, project_name: str) -> Roadmap:
    """Initialize roadmap for a new project.

    Args:
        project_path: Path to project root
        project_name: Name of the project

    Returns:
        New Roadmap
    """
    roadmap = Roadmap(project_name=project_name)
    save_roadmap(project_path, roadmap)
    return roadmap
