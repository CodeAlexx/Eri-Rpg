"""
Summary model for plan execution results.

SUMMARY.md is created after plan execution with:
- One-liner description
- Deliverables
- Tasks completed
- Decisions made
- Deviations from plan
- Next phase readiness
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class TechStack:
    """Tech stack additions from plan execution."""
    added: List[str] = field(default_factory=list)  # New dependencies/frameworks
    patterns: List[str] = field(default_factory=list)  # New patterns established

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": self.added,
            "patterns": self.patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TechStack":
        return cls(
            added=data.get("added", []),
            patterns=data.get("patterns", []),
        )


@dataclass
class KeyFile:
    """A key file created or modified."""
    path: str
    action: str  # "created" or "modified"
    purpose: str = ""  # What this file does

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "action": self.action,
            "purpose": self.purpose,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyFile":
        return cls(
            path=data.get("path", ""),
            action=data.get("action", ""),
            purpose=data.get("purpose", ""),
        )


@dataclass
class Deviation:
    """A deviation from the original plan."""
    type: str  # "auto-fix", "auto-add", "blocking-fix", "architectural"
    description: str
    reason: str = ""
    files_affected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "reason": self.reason,
            "files_affected": self.files_affected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deviation":
        return cls(
            type=data.get("type", ""),
            description=data.get("description", ""),
            reason=data.get("reason", ""),
            files_affected=data.get("files_affected", []),
        )


@dataclass
class CompletedTask:
    """A task that was completed during execution."""
    name: str
    commit_hash: Optional[str] = None
    duration_seconds: float = 0
    files_touched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "commit_hash": self.commit_hash,
            "duration_seconds": self.duration_seconds,
            "files_touched": self.files_touched,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletedTask":
        return cls(
            name=data.get("name", ""),
            commit_hash=data.get("commit_hash"),
            duration_seconds=data.get("duration_seconds", 0),
            files_touched=data.get("files_touched", []),
        )


@dataclass
class Summary:
    """Execution summary for a plan.

    Created after plan execution, stored as {plan}-SUMMARY.md.
    """
    phase: str
    plan: str
    subsystem: str = ""

    # Classification
    tags: List[str] = field(default_factory=list)  # e.g., ["auth", "api", "security"]
    requires: List[str] = field(default_factory=list)  # What this plan requires
    provides: List[str] = field(default_factory=list)  # What this plan provides
    affects: List[str] = field(default_factory=list)  # What systems are affected

    # Tech stack
    tech_stack: TechStack = field(default_factory=TechStack)

    # Key files
    key_files: List[KeyFile] = field(default_factory=list)

    # Results
    one_liner: str = ""  # Single sentence summary
    deliverables: List[str] = field(default_factory=list)
    tasks_completed: List[CompletedTask] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    deviations: List[Deviation] = field(default_factory=list)

    # Next phase readiness
    next_phase_ready: bool = True
    next_phase_blockers: List[str] = field(default_factory=list)

    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_minutes: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "plan": self.plan,
            "subsystem": self.subsystem,
            "tags": self.tags,
            "requires": self.requires,
            "provides": self.provides,
            "affects": self.affects,
            "tech_stack": self.tech_stack.to_dict(),
            "key_files": [f.to_dict() for f in self.key_files],
            "one_liner": self.one_liner,
            "deliverables": self.deliverables,
            "tasks_completed": [t.to_dict() for t in self.tasks_completed],
            "decisions_made": self.decisions_made,
            "deviations": [d.to_dict() for d in self.deviations],
            "next_phase_ready": self.next_phase_ready,
            "next_phase_blockers": self.next_phase_blockers,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_minutes": self.duration_minutes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Summary":
        return cls(
            phase=data.get("phase", ""),
            plan=data.get("plan", ""),
            subsystem=data.get("subsystem", ""),
            tags=data.get("tags", []),
            requires=data.get("requires", []),
            provides=data.get("provides", []),
            affects=data.get("affects", []),
            tech_stack=TechStack.from_dict(data.get("tech_stack", {})),
            key_files=[KeyFile.from_dict(f) for f in data.get("key_files", [])],
            one_liner=data.get("one_liner", ""),
            deliverables=data.get("deliverables", []),
            tasks_completed=[CompletedTask.from_dict(t) for t in data.get("tasks_completed", [])],
            decisions_made=data.get("decisions_made", []),
            deviations=[Deviation.from_dict(d) for d in data.get("deviations", [])],
            next_phase_ready=data.get("next_phase_ready", True),
            next_phase_blockers=data.get("next_phase_blockers", []),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_minutes=data.get("duration_minutes", 0),
        )

    def format_display(self) -> str:
        """Format summary for display."""
        lines = [
            f"# Summary: {self.phase}/{self.plan}",
            "",
            f"**{self.one_liner}**",
            "",
        ]

        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
            lines.append("")

        if self.deliverables:
            lines.append("## Deliverables")
            for d in self.deliverables:
                lines.append(f"- {d}")
            lines.append("")

        if self.tasks_completed:
            lines.append("## Tasks Completed")
            for t in self.tasks_completed:
                commit = f" [{t.commit_hash[:8]}]" if t.commit_hash else ""
                lines.append(f"- {t.name}{commit}")
            lines.append("")

        if self.decisions_made:
            lines.append("## Decisions Made")
            for d in self.decisions_made:
                lines.append(f"- {d}")
            lines.append("")

        if self.deviations:
            lines.append("## Deviations")
            for d in self.deviations:
                lines.append(f"- [{d.type}] {d.description}")
            lines.append("")

        if self.key_files:
            lines.append("## Key Files")
            for f in self.key_files:
                lines.append(f"- {f.path} ({f.action}): {f.purpose}")
            lines.append("")

        lines.append("## Next Phase Readiness")
        if self.next_phase_ready:
            lines.append("✅ Ready for next phase")
        else:
            lines.append("❌ Blockers:")
            for b in self.next_phase_blockers:
                lines.append(f"  - {b}")

        lines.append("")
        lines.append(f"Duration: {self.duration_minutes:.1f} minutes")

        return "\n".join(lines)


def save_summary(project_path: str, summary: Summary) -> str:
    """Save summary to project.

    Args:
        project_path: Path to project root
        summary: Summary to save

    Returns:
        Path to saved file
    """
    import os

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", summary.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, f"{summary.plan}-SUMMARY.json")
    with open(file_path, "w") as f:
        json.dump(summary.to_dict(), f, indent=2)

    return file_path


def load_summary(project_path: str, phase: str, plan: str) -> Optional[Summary]:
    """Load summary from project.

    Args:
        project_path: Path to project root
        phase: Phase name
        plan: Plan name

    Returns:
        Summary if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "phases", phase, f"{plan}-SUMMARY.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return Summary.from_dict(data)
