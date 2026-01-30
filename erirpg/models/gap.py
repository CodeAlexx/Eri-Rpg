"""
Gap model for tracking verification failures.

Gaps represent things that should exist/work but don't:
- Missing truths (observable outcomes not achieved)
- Missing artifacts (required files don't exist or are stubs)
- Missing key links (components not wired together)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class GapStatus(Enum):
    """Status of a gap."""
    OPEN = "open"           # Gap exists, not addressed
    IN_PROGRESS = "in_progress"  # Being worked on
    RESOLVED = "resolved"   # Fixed
    DEFERRED = "deferred"   # Postponed to later phase
    WONT_FIX = "wont_fix"  # Accepted as not needed


class GapType(Enum):
    """Type of gap."""
    TRUTH = "truth"        # Observable truth not verified
    ARTIFACT = "artifact"  # Required file missing/stub
    KEY_LINK = "key_link"  # Components not connected


@dataclass
class Gap:
    """A gap in verification - something that should exist but doesn't.

    Gaps are the output of verification and input to gap-fixing phases.
    """
    id: str
    gap_type: GapType
    phase: str  # Phase where gap was found
    plan_id: str  # Plan that created the gap

    # What's wrong
    description: str  # Human-readable description
    expected: str  # What was expected
    actual: str  # What was found

    # For artifact gaps
    artifact_path: Optional[str] = None

    # For key_link gaps
    from_component: Optional[str] = None
    to_component: Optional[str] = None

    # Status
    status: GapStatus = GapStatus.OPEN
    resolution: str = ""  # How it was resolved

    # Tracking
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    deferred_to: Optional[str] = None  # Phase deferred to

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            import hashlib
            data = f"{self.gap_type.value}:{self.description}:{self.created_at}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gap_type": self.gap_type.value,
            "phase": self.phase,
            "plan_id": self.plan_id,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
            "artifact_path": self.artifact_path,
            "from_component": self.from_component,
            "to_component": self.to_component,
            "status": self.status.value,
            "resolution": self.resolution,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "deferred_to": self.deferred_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gap":
        gap_type_str = data.get("gap_type", "truth")
        try:
            gap_type = GapType(gap_type_str)
        except ValueError:
            gap_type = GapType.TRUTH

        status_str = data.get("status", "open")
        try:
            status = GapStatus(status_str)
        except ValueError:
            status = GapStatus.OPEN

        return cls(
            id=data.get("id", ""),
            gap_type=gap_type,
            phase=data.get("phase", ""),
            plan_id=data.get("plan_id", ""),
            description=data.get("description", ""),
            expected=data.get("expected", ""),
            actual=data.get("actual", ""),
            artifact_path=data.get("artifact_path"),
            from_component=data.get("from_component"),
            to_component=data.get("to_component"),
            status=status,
            resolution=data.get("resolution", ""),
            created_at=data.get("created_at"),
            resolved_at=data.get("resolved_at"),
            deferred_to=data.get("deferred_to"),
        )

    def resolve(self, resolution: str) -> None:
        """Mark gap as resolved."""
        self.status = GapStatus.RESOLVED
        self.resolution = resolution
        self.resolved_at = datetime.now().isoformat()

    def defer(self, to_phase: str) -> None:
        """Defer gap to a later phase."""
        self.status = GapStatus.DEFERRED
        self.deferred_to = to_phase

    def is_open(self) -> bool:
        """Check if gap is still open."""
        return self.status in (GapStatus.OPEN, GapStatus.IN_PROGRESS)

    def format_display(self) -> str:
        """Format gap for display."""
        status_icon = {
            GapStatus.OPEN: "❌",
            GapStatus.IN_PROGRESS: "🔄",
            GapStatus.RESOLVED: "✅",
            GapStatus.DEFERRED: "⏸️",
            GapStatus.WONT_FIX: "➖",
        }.get(self.status, "?")

        lines = [
            f"{status_icon} [{self.gap_type.value.upper()}] {self.description}",
            f"   Expected: {self.expected}",
            f"   Actual: {self.actual}",
        ]

        if self.artifact_path:
            lines.append(f"   Path: {self.artifact_path}")

        if self.from_component and self.to_component:
            lines.append(f"   Link: {self.from_component} → {self.to_component}")

        if self.status == GapStatus.DEFERRED and self.deferred_to:
            lines.append(f"   Deferred to: {self.deferred_to}")

        if self.status == GapStatus.RESOLVED:
            lines.append(f"   Resolution: {self.resolution}")

        return "\n".join(lines)


@dataclass
class GapSummary:
    """Summary of gaps for a phase or plan."""
    total: int = 0
    open_count: int = 0
    resolved: int = 0
    deferred: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "open": self.open_count,
            "resolved": self.resolved,
            "deferred": self.deferred,
            "by_type": self.by_type,
        }

    @classmethod
    def from_gaps(cls, gaps: List[Gap]) -> "GapSummary":
        """Create summary from list of gaps."""
        summary = cls(total=len(gaps))

        for gap in gaps:
            # Count by status
            if gap.is_open():
                summary.open_count += 1
            elif gap.status == GapStatus.RESOLVED:
                summary.resolved += 1
            elif gap.status == GapStatus.DEFERRED:
                summary.deferred += 1

            # Count by type
            type_name = gap.gap_type.value
            summary.by_type[type_name] = summary.by_type.get(type_name, 0) + 1

        return summary

    def format_display(self) -> str:
        """Format summary for display."""
        lines = [
            f"Gap Summary: {self.total} total",
            f"  Open: {self.open_count}",
            f"  Resolved: {self.resolved}",
            f"  Deferred: {self.deferred}",
        ]

        if self.by_type:
            lines.append("  By Type:")
            for type_name, count in self.by_type.items():
                lines.append(f"    {type_name}: {count}")

        return "\n".join(lines)


def create_gap_from_truth(
    phase: str,
    plan_id: str,
    truth_description: str,
    expected: str,
    actual: str,
) -> Gap:
    """Create a gap for an unverified truth."""
    return Gap(
        id="",
        gap_type=GapType.TRUTH,
        phase=phase,
        plan_id=plan_id,
        description=f"Truth not verified: {truth_description}",
        expected=expected,
        actual=actual,
    )


def create_gap_from_artifact(
    phase: str,
    plan_id: str,
    artifact_path: str,
    expected: str,
    actual: str,
) -> Gap:
    """Create a gap for a missing/stub artifact."""
    return Gap(
        id="",
        gap_type=GapType.ARTIFACT,
        phase=phase,
        plan_id=plan_id,
        description=f"Artifact missing or stub: {artifact_path}",
        expected=expected,
        actual=actual,
        artifact_path=artifact_path,
    )


def create_gap_from_key_link(
    phase: str,
    plan_id: str,
    from_component: str,
    to_component: str,
    expected: str,
    actual: str,
) -> Gap:
    """Create a gap for an unverified key link."""
    return Gap(
        id="",
        gap_type=GapType.KEY_LINK,
        phase=phase,
        plan_id=plan_id,
        description=f"Components not connected: {from_component} → {to_component}",
        expected=expected,
        actual=actual,
        from_component=from_component,
        to_component=to_component,
    )
