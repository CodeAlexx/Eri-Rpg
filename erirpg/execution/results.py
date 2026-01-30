"""
Execution result models.

Separated to avoid circular imports between wave_executor and parallel_agents.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from erirpg.models.summary import Summary


@dataclass
class PlanResult:
    """Result of executing a single plan."""
    plan_id: str
    status: str  # "completed", "failed", "checkpoint"
    summary: Optional[Summary] = None
    checkpoint_id: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "summary": self.summary.to_dict() if self.summary else None,
            "checkpoint_id": self.checkpoint_id,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class WaveResult:
    """Result of executing a wave of plans."""
    wave_number: int
    plan_results: List[PlanResult] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def all_completed(self) -> bool:
        """Check if all plans in wave completed successfully."""
        return all(r.status == "completed" for r in self.plan_results)

    @property
    def has_failures(self) -> bool:
        """Check if any plans failed."""
        return any(r.status == "failed" for r in self.plan_results)

    @property
    def has_checkpoints(self) -> bool:
        """Check if any plans hit checkpoints."""
        return any(r.status == "checkpoint" for r in self.plan_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave_number": self.wave_number,
            "plan_results": [r.to_dict() for r in self.plan_results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "all_completed": self.all_completed,
            "has_failures": self.has_failures,
            "has_checkpoints": self.has_checkpoints,
        }


@dataclass
class PhaseResult:
    """Result of executing an entire phase."""
    phase: str
    wave_results: List[WaveResult] = field(default_factory=list)
    status: str = "pending"  # "completed", "failed", "checkpoint"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def all_completed(self) -> bool:
        """Check if all waves completed successfully."""
        return all(w.all_completed for w in self.wave_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "wave_results": [w.to_dict() for w in self.wave_results],
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
