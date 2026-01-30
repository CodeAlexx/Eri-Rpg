"""
Checkpoint model for human-in-the-loop execution.

Checkpoints allow:
- Verification by human before continuing
- Decisions that require human input
- Actions that only humans can perform

Continuation spawns a FRESH agent with:
- Completed tasks
- Resume point
- User response
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class CheckpointType(Enum):
    """Type of checkpoint."""
    HUMAN_VERIFY = "human-verify"    # Human must verify something worked
    DECISION = "decision"            # Human must make a decision
    HUMAN_ACTION = "human-action"    # Human must perform an action


@dataclass
class CompletedTask:
    """A task that was completed before the checkpoint."""
    name: str
    commit_hash: Optional[str] = None
    files_touched: List[str] = field(default_factory=list)
    notes: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "commit_hash": self.commit_hash,
            "files_touched": self.files_touched,
            "notes": self.notes,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletedTask":
        return cls(
            name=data.get("name", ""),
            commit_hash=data.get("commit_hash"),
            files_touched=data.get("files_touched", []),
            notes=data.get("notes", ""),
            completed_at=data.get("completed_at"),
        )


@dataclass
class CheckpointState:
    """Serialized state at a checkpoint for continuation.

    When a checkpoint is hit:
    1. State is serialized
    2. Checkpoint is returned to user
    3. User provides response
    4. Fresh agent spawned with this state + response
    """
    checkpoint_id: str
    plan_id: str
    phase: str

    # Progress
    completed_tasks: List[CompletedTask] = field(default_factory=list)
    current_task_index: int = 0
    current_task_name: str = ""

    # Checkpoint details
    checkpoint_type: CheckpointType = CheckpointType.HUMAN_VERIFY
    blocker: str = ""  # What's blocking progress
    awaiting: str = ""  # What we're waiting for from user

    # Context for continuation
    execution_context: str = ""  # Context to pass to continuation agent
    files_modified: List[str] = field(default_factory=list)

    # Timestamps
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    user_response: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.checkpoint_id:
            import hashlib
            data = f"{self.plan_id}:{self.current_task_name}:{self.created_at}"
            self.checkpoint_id = hashlib.sha1(data.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "plan_id": self.plan_id,
            "phase": self.phase,
            "completed_tasks": [t.to_dict() for t in self.completed_tasks],
            "current_task_index": self.current_task_index,
            "current_task_name": self.current_task_name,
            "checkpoint_type": self.checkpoint_type.value,
            "blocker": self.blocker,
            "awaiting": self.awaiting,
            "execution_context": self.execution_context,
            "files_modified": self.files_modified,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "user_response": self.user_response,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointState":
        cp_type_str = data.get("checkpoint_type", "human-verify")
        try:
            cp_type = CheckpointType(cp_type_str)
        except ValueError:
            cp_type = CheckpointType.HUMAN_VERIFY

        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            plan_id=data.get("plan_id", ""),
            phase=data.get("phase", ""),
            completed_tasks=[CompletedTask.from_dict(t) for t in data.get("completed_tasks", [])],
            current_task_index=data.get("current_task_index", 0),
            current_task_name=data.get("current_task_name", ""),
            checkpoint_type=cp_type,
            blocker=data.get("blocker", ""),
            awaiting=data.get("awaiting", ""),
            execution_context=data.get("execution_context", ""),
            files_modified=data.get("files_modified", []),
            created_at=data.get("created_at"),
            resolved_at=data.get("resolved_at"),
            user_response=data.get("user_response"),
        )

    def resolve(self, response: str) -> None:
        """Mark checkpoint as resolved with user response."""
        self.resolved_at = datetime.now().isoformat()
        self.user_response = response

    def is_resolved(self) -> bool:
        """Check if checkpoint has been resolved."""
        return self.resolved_at is not None


@dataclass
class Checkpoint:
    """A checkpoint in plan execution that requires human interaction.

    Format for display:
    - Type
    - Plan
    - Progress (X of Y tasks)
    - Completed Tasks table
    - Current Task
    - Checkpoint Details
    - Awaiting
    """
    state: CheckpointState
    progress_display: str = ""  # "2 of 5 tasks completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "progress_display": self.progress_display,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            state=CheckpointState.from_dict(data.get("state", {})),
            progress_display=data.get("progress_display", ""),
        )

    def format_display(self) -> str:
        """Format checkpoint for display to user."""
        lines = [
            "=" * 60,
            f"⏸️  CHECKPOINT: {self.state.checkpoint_type.value.upper()}",
            "=" * 60,
            "",
            f"Plan: {self.state.plan_id}",
            f"Phase: {self.state.phase}",
            f"Progress: {len(self.state.completed_tasks)} tasks completed",
            "",
        ]

        if self.state.completed_tasks:
            lines.append("Completed Tasks:")
            lines.append("-" * 40)
            for task in self.state.completed_tasks:
                commit = f" [{task.commit_hash[:8]}]" if task.commit_hash else ""
                lines.append(f"  ✓ {task.name}{commit}")
            lines.append("")

        lines.extend([
            f"Current Task: {self.state.current_task_name}",
            "",
            "Checkpoint Details:",
            f"  {self.state.blocker}",
            "",
            "Awaiting:",
            f"  {self.state.awaiting}",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)


def save_checkpoint(project_path: str, checkpoint: Checkpoint) -> str:
    """Save a checkpoint to the project.

    Args:
        project_path: Path to project root
        checkpoint: Checkpoint to save

    Returns:
        Path to saved file
    """
    import os

    checkpoint_dir = os.path.join(project_path, ".eri-rpg", "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    file_path = os.path.join(checkpoint_dir, f"{checkpoint.state.checkpoint_id}.json")
    with open(file_path, "w") as f:
        json.dump(checkpoint.to_dict(), f, indent=2)

    return file_path


def load_checkpoint(project_path: str, checkpoint_id: str) -> Optional[Checkpoint]:
    """Load a checkpoint from the project.

    Args:
        project_path: Path to project root
        checkpoint_id: ID of checkpoint to load

    Returns:
        Checkpoint if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "checkpoints", f"{checkpoint_id}.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return Checkpoint.from_dict(data)


def list_pending_checkpoints(project_path: str) -> List[Checkpoint]:
    """List all unresolved checkpoints.

    Args:
        project_path: Path to project root

    Returns:
        List of unresolved checkpoints
    """
    import os
    import glob

    checkpoint_dir = os.path.join(project_path, ".eri-rpg", "checkpoints")
    pattern = os.path.join(checkpoint_dir, "*.json")

    checkpoints = []
    for file_path in glob.glob(pattern):
        with open(file_path, "r") as f:
            data = json.load(f)
        checkpoint = Checkpoint.from_dict(data)
        if not checkpoint.state.is_resolved():
            checkpoints.append(checkpoint)

    return checkpoints


def resolve_checkpoint(
    project_path: str,
    checkpoint_id: str,
    response: str,
) -> Optional[Checkpoint]:
    """Resolve a checkpoint with user response.

    Args:
        project_path: Path to project root
        checkpoint_id: ID of checkpoint to resolve
        response: User's response

    Returns:
        Updated checkpoint if found, None otherwise
    """
    checkpoint = load_checkpoint(project_path, checkpoint_id)
    if not checkpoint:
        return None

    checkpoint.state.resolve(response)
    save_checkpoint(project_path, checkpoint)

    return checkpoint
