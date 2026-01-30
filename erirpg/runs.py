"""
Run record storage for EriRPG.

Persists run state, step results, and artifacts to enable
pause/resume and post-run analysis.

Storage structure:
    .eri-rpg/runs/
        <run_id>/
            run.json        # Run metadata and step results
            contexts/       # Step context files
            artifacts/      # Step output artifacts
            logs/           # Execution logs
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import os
import shutil
import uuid


class RunStatus(Enum):
    """Status of a run."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    status: str = "pending"  # StepStatus value
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: str = ""
    error: str = ""
    artifacts: List[str] = field(default_factory=list)
    context_file: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output": self.output,
            "error": self.error,
            "artifacts": self.artifacts,
            "context_file": self.context_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepResult":
        """Deserialize from dictionary."""
        return cls(
            step_id=data.get("step_id", ""),
            status=data.get("status", "pending"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            output=data.get("output", ""),
            error=data.get("error", ""),
            artifacts=data.get("artifacts", []),
            context_file=data.get("context_file", ""),
        )

    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class RunRecord:
    """Record of a plan execution run."""
    id: str
    plan_id: str
    plan_path: str
    spec_id: str = ""

    # Status
    status: str = "pending"  # RunStatus value
    current_step: str = ""

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Results
    step_results: List[StepResult] = field(default_factory=list)

    # Metadata
    project_path: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate the run record."""
        errors = []
        if not self.id:
            errors.append("id is required")
        if not self.plan_id:
            errors.append("plan_id is required")
        if not self.plan_path:
            errors.append("plan_path is required")

        valid_statuses = {s.value for s in RunStatus}
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "plan_path": self.plan_path,
            "spec_id": self.spec_id,
            "status": self.status,
            "current_step": self.current_step,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "step_results": [r.to_dict() for r in self.step_results],
            "project_path": self.project_path,
            "notes": self.notes,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            plan_id=data.get("plan_id", ""),
            plan_path=data.get("plan_path", ""),
            spec_id=data.get("spec_id", ""),
            status=data.get("status", "pending"),
            current_step=data.get("current_step", ""),
            started_at=datetime.fromisoformat(data["started_at"]) if "started_at" in data else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            step_results=[StepResult.from_dict(r) for r in data.get("step_results", [])],
            project_path=data.get("project_path", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
        )

    def get_step_result(self, step_id: str) -> Optional[StepResult]:
        """Get result for a specific step."""
        for result in self.step_results:
            if result.step_id == step_id:
                return result
        return None

    def add_step_result(self, result: StepResult) -> None:
        """Add or update a step result."""
        existing = self.get_step_result(result.step_id)
        if existing:
            # Update existing
            idx = self.step_results.index(existing)
            self.step_results[idx] = result
        else:
            self.step_results.append(result)

    @property
    def duration(self) -> Optional[float]:
        """Get total run duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def completed_steps(self) -> int:
        """Count completed steps."""
        return sum(1 for r in self.step_results if r.status == "completed")

    @property
    def failed_steps(self) -> int:
        """Count failed steps."""
        return sum(1 for r in self.step_results if r.status == "failed")

    def format_summary(self) -> str:
        """Format a summary of the run."""
        lines = [
            f"Run: {self.id}",
            f"Plan: {self.plan_id}",
            f"Status: {self.status}",
            f"Started: {self.started_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        if self.completed_at:
            lines.append(f"Completed: {self.completed_at.strftime('%Y-%m-%d %H:%M')}")

        total = len(self.step_results)
        completed = self.completed_steps
        failed = self.failed_steps

        lines.append(f"Progress: {completed}/{total} steps")
        if failed > 0:
            lines.append(f"Failed: {failed} steps")

        return "\n".join(lines)


# =============================================================================
# Run Storage
# =============================================================================

def get_runs_dir(project_path: str) -> str:
    """Get the runs directory for a project."""
    return os.path.join(project_path, ".eri-rpg", "runs")


def get_run_dir(project_path: str, run_id: str) -> str:
    """Get directory for a specific run."""
    return os.path.join(get_runs_dir(project_path), run_id)


def _generate_run_id(plan_id: str) -> str:
    """Generate a unique run ID."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Use first 10 chars of plan_id
    plan_short = plan_id[:10] if len(plan_id) > 10 else plan_id
    # Add short unique suffix to handle multiple runs per second
    suffix = uuid.uuid4().hex[:6]
    return f"run-{plan_short}-{timestamp}-{suffix}"


def create_run(plan: "Plan", project_path: str) -> RunRecord:
    """Create a new run record for a plan.

    Args:
        plan: The plan to execute
        project_path: Path to the project

    Returns:
        A new RunRecord with initialized directories
    """
    from erirpg.planner import Plan

    run_id = _generate_run_id(plan.id)

    # Create run directory structure
    run_dir = get_run_dir(project_path, run_id)
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, "contexts"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "logs"), exist_ok=True)

    # Save a copy of the plan
    plan_copy_path = os.path.join(run_dir, "plan.json")
    plan.save(plan_copy_path)

    run = RunRecord(
        id=run_id,
        plan_id=plan.id,
        plan_path=plan_copy_path,
        spec_id=plan.spec_id,
        status=RunStatus.PENDING.value,
        project_path=project_path,
    )

    return run


def save_run(project_path: str, run: RunRecord) -> str:
    """Save a run record to disk.

    Args:
        project_path: Path to the project
        run: The run record to save

    Returns:
        Path to the saved run.json file
    """
    run_dir = get_run_dir(project_path, run.id)
    os.makedirs(run_dir, exist_ok=True)

    run_path = os.path.join(run_dir, "run.json")
    with open(run_path, "w") as f:
        json.dump(run.to_dict(), f, indent=2)

    # Sync status files after run state change
    from erirpg.status_sync import sync_status_files
    sync_status_files(project_path)

    return run_path


def load_run(project_path: str, run_id: str) -> Optional[RunRecord]:
    """Load a run record from disk.

    Args:
        project_path: Path to the project
        run_id: ID of the run to load

    Returns:
        The RunRecord or None if not found
    """
    run_path = os.path.join(get_run_dir(project_path, run_id), "run.json")

    if not os.path.exists(run_path):
        return None

    with open(run_path, "r") as f:
        data = json.load(f)

    return RunRecord.from_dict(data)


def delete_run(project_path: str, run_id: str) -> bool:
    """Delete a run and all its artifacts.

    Args:
        project_path: Path to the project
        run_id: ID of the run to delete

    Returns:
        True if deleted, False if not found
    """
    run_dir = get_run_dir(project_path, run_id)

    if not os.path.exists(run_dir):
        return False

    shutil.rmtree(run_dir)
    return True


def list_run_ids(project_path: str) -> List[str]:
    """List all run IDs in a project.

    Args:
        project_path: Path to the project

    Returns:
        List of run IDs, sorted by creation time (newest first)
    """
    runs_dir = get_runs_dir(project_path)

    if not os.path.exists(runs_dir):
        return []

    run_entries = []
    for name in os.listdir(runs_dir):
        run_dir = os.path.join(runs_dir, name)
        run_json = os.path.join(run_dir, "run.json")
        if os.path.isdir(run_dir) and os.path.exists(run_json):
            # Use file mtime for accurate sorting
            mtime = os.path.getmtime(run_json)
            run_entries.append((name, mtime))

    # Sort by modification time (newest first)
    run_entries.sort(key=lambda x: x[1], reverse=True)
    return [entry[0] for entry in run_entries]


def get_latest_run(project_path: str) -> Optional[RunRecord]:
    """Get the most recent run for a project.

    Args:
        project_path: Path to the project

    Returns:
        The most recent RunRecord or None
    """
    run_ids = list_run_ids(project_path)
    if not run_ids:
        return None

    return load_run(project_path, run_ids[0])


def save_artifact(
    project_path: str,
    run_id: str,
    step_id: str,
    name: str,
    content: str,
) -> str:
    """Save an artifact for a step.

    Args:
        project_path: Path to the project
        run_id: ID of the run
        step_id: ID of the step
        name: Artifact filename
        content: Artifact content

    Returns:
        Path to the saved artifact
    """
    artifacts_dir = os.path.join(get_run_dir(project_path, run_id), "artifacts", step_id)
    os.makedirs(artifacts_dir, exist_ok=True)

    artifact_path = os.path.join(artifacts_dir, name)
    with open(artifact_path, "w") as f:
        f.write(content)

    return artifact_path


def get_artifacts(project_path: str, run_id: str, step_id: str) -> List[str]:
    """Get all artifacts for a step.

    Args:
        project_path: Path to the project
        run_id: ID of the run
        step_id: ID of the step

    Returns:
        List of artifact paths
    """
    artifacts_dir = os.path.join(get_run_dir(project_path, run_id), "artifacts", step_id)

    if not os.path.exists(artifacts_dir):
        return []

    return [
        os.path.join(artifacts_dir, f)
        for f in os.listdir(artifacts_dir)
        if os.path.isfile(os.path.join(artifacts_dir, f))
    ]
