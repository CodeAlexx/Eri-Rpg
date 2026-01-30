"""
Issue model for plan checker findings.

Issues are problems found during plan verification:
- Requirement coverage gaps
- Task completeness problems
- Dependency cycles
- Scope violations
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class IssueSeverity(Enum):
    """Severity of a plan issue."""
    BLOCKER = "blocker"  # Cannot proceed until fixed
    WARNING = "warning"  # Should be fixed, but can proceed
    INFO = "info"        # Informational, optional fix


class IssueDimension(Enum):
    """Dimension of plan checking where issue was found."""
    REQUIREMENT_COVERAGE = "requirement_coverage"  # Every requirement has tasks
    TASK_COMPLETENESS = "task_completeness"        # All tasks have required fields
    DEPENDENCY_CORRECTNESS = "dependency_correctness"  # No cycles, valid refs
    KEY_LINKS_PLANNED = "key_links_planned"        # Wiring in task actions
    SCOPE_SANITY = "scope_sanity"                  # ≤3 tasks, ≤8 files
    MUST_HAVES_DERIVATION = "must_haves_derivation"  # Truths user-observable


@dataclass
class Issue:
    """An issue found during plan verification.

    Plan checker examines plans along 6 dimensions:
    1. Requirement Coverage - Every phase requirement has task(s)
    2. Task Completeness - All auto tasks have files, action, verify, done
    3. Dependency Correctness - All depends_on exist, no cycles, waves consistent
    4. Key Links Planned - Wiring in task actions
    5. Scope Sanity - ≤3 tasks/plan, ≤8 files/plan
    6. Must-Haves Derivation - Truths user-observable, artifacts support truths
    """
    id: str
    dimension: IssueDimension
    severity: IssueSeverity

    # Details
    message: str  # Human-readable description
    location: str = ""  # Where in the plan (task name, field, etc.)
    suggestion: str = ""  # How to fix

    # Context
    plan_id: str = ""
    phase: str = ""

    # Tracking
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            import hashlib
            data = f"{self.dimension.value}:{self.message}:{self.created_at}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "plan_id": self.plan_id,
            "phase": self.phase,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        dim_str = data.get("dimension", "task_completeness")
        try:
            dimension = IssueDimension(dim_str)
        except ValueError:
            dimension = IssueDimension.TASK_COMPLETENESS

        sev_str = data.get("severity", "warning")
        try:
            severity = IssueSeverity(sev_str)
        except ValueError:
            severity = IssueSeverity.WARNING

        return cls(
            id=data.get("id", ""),
            dimension=dimension,
            severity=severity,
            message=data.get("message", ""),
            location=data.get("location", ""),
            suggestion=data.get("suggestion", ""),
            plan_id=data.get("plan_id", ""),
            phase=data.get("phase", ""),
            created_at=data.get("created_at"),
            resolved_at=data.get("resolved_at"),
            resolution=data.get("resolution", ""),
        )

    def is_blocker(self) -> bool:
        """Check if this issue blocks execution."""
        return self.severity == IssueSeverity.BLOCKER

    def resolve(self, resolution: str) -> None:
        """Mark issue as resolved."""
        self.resolved_at = datetime.now().isoformat()
        self.resolution = resolution

    def format_display(self) -> str:
        """Format issue for display."""
        icon = {
            IssueSeverity.BLOCKER: "🚫",
            IssueSeverity.WARNING: "⚠️",
            IssueSeverity.INFO: "ℹ️",
        }.get(self.severity, "?")

        lines = [
            f"{icon} [{self.severity.value.upper()}] {self.message}",
            f"   Dimension: {self.dimension.value}",
        ]

        if self.location:
            lines.append(f"   Location: {self.location}")

        if self.suggestion:
            lines.append(f"   Suggestion: {self.suggestion}")

        return "\n".join(lines)


@dataclass
class PlanCheckResult:
    """Result of plan checking across all dimensions."""
    plan_id: str
    phase: str
    issues: List[Issue] = field(default_factory=list)
    passed: bool = True
    checked_at: Optional[str] = None

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now().isoformat()

    @property
    def blockers(self) -> List[Issue]:
        """Get all blocker issues."""
        return [i for i in self.issues if i.is_blocker()]

    @property
    def warnings(self) -> List[Issue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]

    @property
    def infos(self) -> List[Issue]:
        """Get all info issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.INFO]

    def has_blockers(self) -> bool:
        """Check if there are any blocker issues."""
        return len(self.blockers) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "phase": self.phase,
            "issues": [i.to_dict() for i in self.issues],
            "passed": self.passed,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanCheckResult":
        return cls(
            plan_id=data.get("plan_id", ""),
            phase=data.get("phase", ""),
            issues=[Issue.from_dict(i) for i in data.get("issues", [])],
            passed=data.get("passed", True),
            checked_at=data.get("checked_at"),
        )

    def format_display(self) -> str:
        """Format check result for display."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"

        lines = [
            "=" * 50,
            f"Plan Check: {self.plan_id}",
            f"Status: {status}",
            f"Issues: {len(self.blockers)} blockers, {len(self.warnings)} warnings, {len(self.infos)} info",
            "=" * 50,
        ]

        if self.blockers:
            lines.append("\nBlockers (must fix):")
            for issue in self.blockers:
                lines.append(issue.format_display())

        if self.warnings:
            lines.append("\nWarnings (should fix):")
            for issue in self.warnings:
                lines.append(issue.format_display())

        if self.infos:
            lines.append("\nInfo:")
            for issue in self.infos:
                lines.append(issue.format_display())

        return "\n".join(lines)


# Factory functions for common issues

def issue_missing_requirement_coverage(
    plan_id: str,
    phase: str,
    requirement: str,
) -> Issue:
    """Create issue for requirement without tasks."""
    return Issue(
        id="",
        dimension=IssueDimension.REQUIREMENT_COVERAGE,
        severity=IssueSeverity.BLOCKER,
        message=f"Requirement has no tasks: {requirement}",
        suggestion="Add task(s) that implement this requirement",
        plan_id=plan_id,
        phase=phase,
    )


def issue_incomplete_task(
    plan_id: str,
    phase: str,
    task_name: str,
    missing_field: str,
) -> Issue:
    """Create issue for incomplete task definition."""
    return Issue(
        id="",
        dimension=IssueDimension.TASK_COMPLETENESS,
        severity=IssueSeverity.BLOCKER,
        message=f"Task '{task_name}' missing required field: {missing_field}",
        location=task_name,
        suggestion=f"Add '{missing_field}' to task definition",
        plan_id=plan_id,
        phase=phase,
    )


def issue_dependency_cycle(
    plan_id: str,
    phase: str,
    cycle: List[str],
) -> Issue:
    """Create issue for dependency cycle."""
    return Issue(
        id="",
        dimension=IssueDimension.DEPENDENCY_CORRECTNESS,
        severity=IssueSeverity.BLOCKER,
        message=f"Dependency cycle detected: {' → '.join(cycle)}",
        suggestion="Break the cycle by removing one dependency",
        plan_id=plan_id,
        phase=phase,
    )


def issue_scope_too_large(
    plan_id: str,
    phase: str,
    metric: str,
    value: int,
    limit: int,
) -> Issue:
    """Create issue for plan scope too large."""
    return Issue(
        id="",
        dimension=IssueDimension.SCOPE_SANITY,
        severity=IssueSeverity.WARNING,
        message=f"Plan scope too large: {metric} = {value} (limit: {limit})",
        suggestion="Consider splitting this plan into smaller plans",
        plan_id=plan_id,
        phase=phase,
    )


def issue_truth_not_observable(
    plan_id: str,
    phase: str,
    truth: str,
) -> Issue:
    """Create issue for truth that isn't user-observable."""
    return Issue(
        id="",
        dimension=IssueDimension.MUST_HAVES_DERIVATION,
        severity=IssueSeverity.WARNING,
        message=f"Truth is not user-observable: {truth}",
        suggestion="Reframe as something a user can verify",
        plan_id=plan_id,
        phase=phase,
    )
