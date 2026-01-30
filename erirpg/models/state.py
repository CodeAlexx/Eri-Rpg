"""
State model for tracking current position and session continuity.

STATE.md is source of truth (human-editable).
state.json is auto-generated for Claude to read.

State tracks:
- Current phase and plan
- Performance metrics
- Accumulated decisions, todos, blockers
- Continuity for session handoff
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class StatePosition:
    """Current position in the workflow."""
    current_milestone: str = ""  # e.g., "v1"
    current_phase: str = ""  # e.g., "02-authentication"
    current_plan: str = ""  # e.g., "01"
    current_task: str = ""  # Task name if in progress

    status: str = "idle"  # idle, planning, executing, verifying, blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_milestone": self.current_milestone,
            "current_phase": self.current_phase,
            "current_plan": self.current_plan,
            "current_task": self.current_task,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatePosition":
        return cls(
            current_milestone=data.get("current_milestone", ""),
            current_phase=data.get("current_phase", ""),
            current_plan=data.get("current_plan", ""),
            current_task=data.get("current_task", ""),
            status=data.get("status", "idle"),
        )

    def format_display(self) -> str:
        """Format position for display."""
        if not self.current_phase:
            return "No active work"

        parts = []
        if self.current_milestone:
            parts.append(f"Milestone: {self.current_milestone}")
        parts.append(f"Phase: {self.current_phase}")
        if self.current_plan:
            parts.append(f"Plan: {self.current_plan}")
        if self.current_task:
            parts.append(f"Task: {self.current_task}")
        parts.append(f"Status: {self.status}")

        return " | ".join(parts)


@dataclass
class StateMetrics:
    """Performance metrics for the project."""
    plans_completed: int = 0
    plans_failed: int = 0
    total_duration_minutes: float = 0
    average_plan_duration_minutes: float = 0

    phases_completed: int = 0
    total_tasks_completed: int = 0
    total_commits: int = 0

    verification_pass_rate: float = 0.0  # 0-1
    gaps_found: int = 0
    gaps_resolved: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plans_completed": self.plans_completed,
            "plans_failed": self.plans_failed,
            "total_duration_minutes": self.total_duration_minutes,
            "average_plan_duration_minutes": self.average_plan_duration_minutes,
            "phases_completed": self.phases_completed,
            "total_tasks_completed": self.total_tasks_completed,
            "total_commits": self.total_commits,
            "verification_pass_rate": self.verification_pass_rate,
            "gaps_found": self.gaps_found,
            "gaps_resolved": self.gaps_resolved,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateMetrics":
        return cls(
            plans_completed=data.get("plans_completed", 0),
            plans_failed=data.get("plans_failed", 0),
            total_duration_minutes=data.get("total_duration_minutes", 0),
            average_plan_duration_minutes=data.get("average_plan_duration_minutes", 0),
            phases_completed=data.get("phases_completed", 0),
            total_tasks_completed=data.get("total_tasks_completed", 0),
            total_commits=data.get("total_commits", 0),
            verification_pass_rate=data.get("verification_pass_rate", 0.0),
            gaps_found=data.get("gaps_found", 0),
            gaps_resolved=data.get("gaps_resolved", 0),
        )

    def record_plan_completion(self, duration_minutes: float, passed: bool) -> None:
        """Record a plan completion."""
        self.total_duration_minutes += duration_minutes
        if passed:
            self.plans_completed += 1
        else:
            self.plans_failed += 1

        total_plans = self.plans_completed + self.plans_failed
        self.average_plan_duration_minutes = self.total_duration_minutes / total_plans


@dataclass
class StateContinuity:
    """Session continuity for handoff/resume."""
    last_session: Optional[str] = None  # ISO datetime
    last_action: str = ""  # What was done last
    stopped_at: str = ""  # Where execution stopped
    resume_file: Optional[str] = None  # File to resume from

    pending_checkpoint: Optional[str] = None  # Checkpoint ID if blocked

    # For session handoff
    handoff_context: str = ""  # Context for next session
    pending_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_session": self.last_session,
            "last_action": self.last_action,
            "stopped_at": self.stopped_at,
            "resume_file": self.resume_file,
            "pending_checkpoint": self.pending_checkpoint,
            "handoff_context": self.handoff_context,
            "pending_actions": self.pending_actions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateContinuity":
        return cls(
            last_session=data.get("last_session"),
            last_action=data.get("last_action", ""),
            stopped_at=data.get("stopped_at", ""),
            resume_file=data.get("resume_file"),
            pending_checkpoint=data.get("pending_checkpoint"),
            handoff_context=data.get("handoff_context", ""),
            pending_actions=data.get("pending_actions", []),
        )

    def record_session(self, action: str, stopped_at: str = "") -> None:
        """Record current session activity."""
        self.last_session = datetime.now().isoformat()
        self.last_action = action
        if stopped_at:
            self.stopped_at = stopped_at


@dataclass
class State:
    """Complete project state.

    Synced between STATE.md (human-readable) and state.json (machine-readable).
    STATE.md is source of truth.
    """
    project_name: str

    # Current position
    position: StatePosition = field(default_factory=StatePosition)

    # Performance metrics
    metrics: StateMetrics = field(default_factory=StateMetrics)

    # Accumulated context
    decisions: List[Dict[str, str]] = field(default_factory=list)  # [{decision, rationale, date}]
    todos: List[str] = field(default_factory=list)  # Captured ideas
    blockers: List[str] = field(default_factory=list)  # Current blockers

    # Continuity
    continuity: StateContinuity = field(default_factory=StateContinuity)

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
            "position": self.position.to_dict(),
            "metrics": self.metrics.to_dict(),
            "decisions": self.decisions,
            "todos": self.todos,
            "blockers": self.blockers,
            "continuity": self.continuity.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        return cls(
            project_name=data.get("project_name", ""),
            position=StatePosition.from_dict(data.get("position", {})),
            metrics=StateMetrics.from_dict(data.get("metrics", {})),
            decisions=data.get("decisions", []),
            todos=data.get("todos", []),
            blockers=data.get("blockers", []),
            continuity=StateContinuity.from_dict(data.get("continuity", {})),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def add_decision(self, decision: str, rationale: str) -> None:
        """Add a decision to the state."""
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "date": datetime.now().isoformat(),
        })
        self._touch()

    def add_todo(self, todo: str) -> None:
        """Add a todo to the state."""
        self.todos.append(todo)
        self._touch()

    def add_blocker(self, blocker: str) -> None:
        """Add a blocker to the state."""
        self.blockers.append(blocker)
        self._touch()

    def resolve_blocker(self, blocker: str) -> None:
        """Remove a blocker from the state."""
        if blocker in self.blockers:
            self.blockers.remove(blocker)
            self._touch()

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()


def load_state(project_path: str) -> Optional[State]:
    """Load state from project.

    Args:
        project_path: Path to project root

    Returns:
        State if found, None otherwise
    """
    import os

    state_path = os.path.join(project_path, ".eri-rpg", "state.json")
    if not os.path.exists(state_path):
        return None

    with open(state_path, "r") as f:
        data = json.load(f)

    return State.from_dict(data)


def save_state(project_path: str, state: State) -> str:
    """Save state to project.

    Args:
        project_path: Path to project root
        state: State to save

    Returns:
        Path to saved file
    """
    import os

    state_dir = os.path.join(project_path, ".eri-rpg")
    os.makedirs(state_dir, exist_ok=True)

    state_path = os.path.join(state_dir, "state.json")
    state._touch()

    with open(state_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    return state_path


def init_state(project_path: str, project_name: str) -> State:
    """Initialize state for a new project.

    Args:
        project_path: Path to project root
        project_name: Name of the project

    Returns:
        New State
    """
    state = State(project_name=project_name)
    save_state(project_path, state)
    return state
