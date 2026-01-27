"""
Run state management.

Tracks execution state across sessions, allowing resume.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from erirpg.spec import Spec
from erirpg.agent.plan import Plan, Step, StepStatus


@dataclass
class Decision:
    """A decision made during run execution."""
    id: str
    decision: str  # What was decided
    rationale: str = ""  # Why this decision was made
    step_id: str = ""  # Which step this relates to
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision": self.decision,
            "rationale": self.rationale,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Decision":
        return cls(
            id=d["id"],
            decision=d["decision"],
            rationale=d.get("rationale", ""),
            step_id=d.get("step_id", ""),
            timestamp=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else datetime.now(),
        )


@dataclass
class RunSummary:
    """Summary of a completed run."""
    run_id: str
    spec_id: str
    one_liner: str  # Brief summary of what was accomplished
    decisions: List[Decision] = field(default_factory=list)
    artifacts_created: List[Dict[str, Any]] = field(default_factory=list)  # {path, lines_added, description}
    duration_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "spec_id": self.spec_id,
            "one_liner": self.one_liner,
            "decisions": [d.to_dict() for d in self.decisions],
            "artifacts_created": self.artifacts_created,
            "duration_seconds": self.duration_seconds,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunSummary":
        return cls(
            run_id=d["run_id"],
            spec_id=d["spec_id"],
            one_liner=d["one_liner"],
            decisions=[Decision.from_dict(dec) for dec in d.get("decisions", [])],
            artifacts_created=d.get("artifacts_created", []),
            duration_seconds=d.get("duration_seconds"),
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
        )


@dataclass
class RunState:
    """Persistent state for an agent run."""

    id: str
    spec: Spec
    plan: Plan
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Execution log
    log: List[Dict[str, Any]] = field(default_factory=list)

    # Files learned during this run
    files_learned: List[str] = field(default_factory=list)

    # Files edited during this run (tracked for enforcement)
    files_edited: List[Dict[str, Any]] = field(default_factory=list)

    # Decisions made during this run
    decisions: List[Decision] = field(default_factory=list)

    # Working directory
    work_dir: Optional[str] = None

    def current_step(self) -> Optional[Step]:
        """Get current step to execute."""
        return self.plan.current_step()

    def is_complete(self) -> bool:
        """Check if run is complete."""
        return self.plan.is_complete()

    def progress(self) -> tuple:
        """Return (completed, total) step counts."""
        return self.plan.progress()

    def add_log(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Add entry to execution log."""
        self.log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {},
        })

    def start_step(self, step: Step) -> None:
        """Mark step as in progress."""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now()
        self.add_log("step_started", {"step_id": step.id, "goal": step.goal})

    def complete_step(
        self,
        step: Step,
        files_touched: List[str],
        notes: str = "",
    ) -> None:
        """Mark step as completed."""
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.now()
        step.files_touched = files_touched
        step.notes = notes
        self.add_log("step_completed", {
            "step_id": step.id,
            "files_touched": files_touched,
            "notes": notes,
        })

    def fail_step(self, step: Step, error: str) -> None:
        """Mark step as failed."""
        step.status = StepStatus.FAILED
        step.completed_at = datetime.now()
        step.error = error
        self.add_log("step_failed", {"step_id": step.id, "error": error})

    def skip_step(self, step: Step, reason: str = "") -> None:
        """Skip a step."""
        step.status = StepStatus.SKIPPED
        step.completed_at = datetime.now()
        step.notes = f"Skipped: {reason}" if reason else "Skipped"
        self.add_log("step_skipped", {"step_id": step.id, "reason": reason})

    def add_learned_files(self, files: List[str]) -> None:
        """Track files that were learned during this run."""
        self.files_learned.extend(files)
        self.add_log("files_learned", {"files": files})

    def track_file_edit(
        self,
        file_path: str,
        description: str,
        step_id: str,
    ) -> None:
        """Track a file edit made through agent.edit_file()."""
        edit_record = {
            "file_path": file_path,
            "description": description,
            "step_id": step_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.files_edited.append(edit_record)
        self.add_log("file_edited", edit_record)

    def add_decision(
        self,
        decision: str,
        rationale: str = "",
        step_id: str = "",
    ) -> Decision:
        """Record a decision made during the run.
        
        Args:
            decision: What was decided
            rationale: Why this decision was made
            step_id: Which step this relates to (defaults to current)
        
        Returns:
            The created Decision
        """
        import uuid
        dec = Decision(
            id=uuid.uuid4().hex[:8],
            decision=decision,
            rationale=rationale,
            step_id=step_id or (self.current_step().id if self.current_step() else ""),
        )
        self.decisions.append(dec)
        self.add_log("decision_made", dec.to_dict())
        return dec

    def generate_summary(self, one_liner: str = "") -> RunSummary:
        """Generate a summary of the completed run.
        
        Args:
            one_liner: Brief summary of what was accomplished.
                      If not provided, generates from spec goal.
        
        Returns:
            RunSummary object
        """
        # Calculate duration
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        
        # Build artifacts_created from files_edited
        artifacts = []
        for edit in self.files_edited:
            artifacts.append({
                "path": edit["file_path"],
                "description": edit.get("description", ""),
                "step_id": edit.get("step_id", ""),
            })
        
        # Generate one_liner if not provided
        if not one_liner:
            goal = self.spec.goal
            if len(goal) > 100:
                one_liner = goal[:97] + "..."
            else:
                one_liner = goal
        
        return RunSummary(
            run_id=self.id,
            spec_id=self.spec.id,
            one_liner=one_liner,
            decisions=list(self.decisions),
            artifacts_created=artifacts,
            duration_seconds=duration,
            completed_at=self.completed_at,
        )

    def get_report(self) -> Dict[str, Any]:
        """Generate a run report."""
        completed, total = self.progress()
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            "id": self.id,
            "goal": self.spec.goal,
            "status": "completed" if self.is_complete() else "in_progress",
            "progress": f"{completed}/{total} steps",
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "files_learned": self.files_learned,
            "steps": [
                {
                    "id": s.id,
                    "goal": s.goal,
                    "status": s.status.value,
                    "files_touched": s.files_touched,
                }
                for s in self.plan.steps
            ],
            "failed_steps": [
                {"id": s.id, "error": s.error}
                for s in self.plan.failed_steps()
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "spec": self.spec.to_dict(),
            "plan": self.plan.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "log": self.log,
            "files_learned": self.files_learned,
            "files_edited": self.files_edited,
            "decisions": [d.to_dict() for d in self.decisions],
            "work_dir": self.work_dir,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunState":
        return cls(
            id=d["id"],
            spec=Spec.from_dict(d["spec"]),
            plan=Plan.from_dict(d["plan"]),
            started_at=datetime.fromisoformat(d["started_at"]),
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
            log=d.get("log", []),
            files_learned=d.get("files_learned", []),
            files_edited=d.get("files_edited", []),
            decisions=[Decision.from_dict(dec) for dec in d.get("decisions", [])],
            work_dir=d.get("work_dir"),
        )

    def save(self, path: str) -> None:
        """Save run state to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "RunState":
        """Load run state from file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))


def get_run_dir(project_path: str) -> str:
    """Get the runs directory for a project."""
    return os.path.join(project_path, ".eri-rpg", "runs")


def save_run(project_path: str, run: RunState) -> str:
    """Save a run to the project's runs directory."""
    run_dir = get_run_dir(project_path)
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(run_dir, f"{run.id}.json")
    run.save(path)
    return path


def load_run(project_path: str, run_id: str) -> Optional[RunState]:
    """Load a run by ID."""
    path = os.path.join(get_run_dir(project_path), f"{run_id}.json")
    if not os.path.exists(path):
        return None
    return RunState.load(path)


def list_runs(project_path: str) -> List[Dict[str, Any]]:
    """List all runs for a project."""
    run_dir = get_run_dir(project_path)
    if not os.path.exists(run_dir):
        return []

    runs = []
    for f in os.listdir(run_dir):
        if f.endswith(".json"):
            try:
                run = RunState.load(os.path.join(run_dir, f))
                runs.append({
                    "id": run.id,
                    "goal": run.spec.goal,
                    "status": "completed" if run.is_complete() else "in_progress",
                    "progress": run.progress(),
                    "started_at": run.started_at.isoformat(),
                })
            except Exception as e:
                import sys; print(f"[EriRPG] {e}", file=sys.stderr)
    return sorted(runs, key=lambda r: r["started_at"], reverse=True)


def get_latest_run(project_path: str) -> Optional[RunState]:
    """Get the most recent run."""
    runs = list_runs(project_path)
    if not runs:
        return None
    return load_run(project_path, runs[0]["id"])
