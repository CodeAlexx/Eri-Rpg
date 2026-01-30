"""
Verification models for three-level verification system.

Three levels:
1. Existence - File exists, not empty
2. Substantive - Real code, not stub
3. Wired - Connected to the system

Verification produces a report with status:
- passed: All checks passed
- gaps_found: Some checks failed
- human_needed: Human verification required
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class VerificationLevel(Enum):
    """Level of verification performed."""
    EXISTENCE = "existence"      # File exists, not empty
    SUBSTANTIVE = "substantive"  # Real code, not stub
    WIRED = "wired"              # Connected to system


class VerificationStatus(Enum):
    """Status of verification."""
    PASSED = "passed"
    GAPS_FOUND = "gaps_found"
    HUMAN_NEEDED = "human_needed"


@dataclass
class TruthVerification:
    """Verification result for an observable truth."""
    truth_id: str
    description: str
    status: str = "pending"  # passed, failed, human_needed
    verification_method: str = ""  # How it was verified
    evidence: str = ""  # Evidence of verification
    verified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "description": self.description,
            "status": self.status,
            "verification_method": self.verification_method,
            "evidence": self.evidence,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TruthVerification":
        return cls(
            truth_id=data.get("truth_id", ""),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            verification_method=data.get("verification_method", ""),
            evidence=data.get("evidence", ""),
            verified_at=data.get("verified_at"),
        )

    def mark_passed(self, method: str, evidence: str) -> None:
        """Mark truth as verified."""
        self.status = "passed"
        self.verification_method = method
        self.evidence = evidence
        self.verified_at = datetime.now().isoformat()

    def mark_failed(self, method: str, evidence: str) -> None:
        """Mark truth as failed verification."""
        self.status = "failed"
        self.verification_method = method
        self.evidence = evidence
        self.verified_at = datetime.now().isoformat()

    def mark_human_needed(self) -> None:
        """Mark truth as requiring human verification."""
        self.status = "human_needed"
        self.verification_method = "manual"
        self.verified_at = datetime.now().isoformat()


@dataclass
class ArtifactVerification:
    """Verification result for a required artifact."""
    path: str
    provides: str

    # Level 1: Existence
    exists: bool = False
    is_empty: bool = True
    line_count: int = 0

    # Level 2: Substantive
    is_stub: bool = True
    stub_indicators: List[str] = field(default_factory=list)  # What made it look like a stub
    substantive_score: float = 0.0  # 0-1, how "real" the code is

    # Level 3: Wired
    is_wired: bool = False
    wiring_evidence: List[str] = field(default_factory=list)  # How it's connected

    # Overall
    status: str = "pending"  # passed, failed
    verified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "provides": self.provides,
            "exists": self.exists,
            "is_empty": self.is_empty,
            "line_count": self.line_count,
            "is_stub": self.is_stub,
            "stub_indicators": self.stub_indicators,
            "substantive_score": self.substantive_score,
            "is_wired": self.is_wired,
            "wiring_evidence": self.wiring_evidence,
            "status": self.status,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactVerification":
        return cls(
            path=data.get("path", ""),
            provides=data.get("provides", ""),
            exists=data.get("exists", False),
            is_empty=data.get("is_empty", True),
            line_count=data.get("line_count", 0),
            is_stub=data.get("is_stub", True),
            stub_indicators=data.get("stub_indicators", []),
            substantive_score=data.get("substantive_score", 0.0),
            is_wired=data.get("is_wired", False),
            wiring_evidence=data.get("wiring_evidence", []),
            status=data.get("status", "pending"),
            verified_at=data.get("verified_at"),
        )

    def passes_level(self, level: VerificationLevel) -> bool:
        """Check if artifact passes a verification level."""
        if level == VerificationLevel.EXISTENCE:
            return self.exists and not self.is_empty
        elif level == VerificationLevel.SUBSTANTIVE:
            return self.exists and not self.is_stub
        elif level == VerificationLevel.WIRED:
            return self.exists and not self.is_stub and self.is_wired
        return False


@dataclass
class LinkVerification:
    """Verification result for a key link."""
    from_component: str
    to_component: str
    via: str

    # Verification
    connected: bool = False
    verification_method: str = ""  # How connection was verified
    evidence: str = ""  # Evidence of connection

    status: str = "pending"  # passed, failed
    verified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_component,
            "to": self.to_component,
            "via": self.via,
            "connected": self.connected,
            "verification_method": self.verification_method,
            "evidence": self.evidence,
            "status": self.status,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkVerification":
        return cls(
            from_component=data.get("from", ""),
            to_component=data.get("to", ""),
            via=data.get("via", ""),
            connected=data.get("connected", False),
            verification_method=data.get("verification_method", ""),
            evidence=data.get("evidence", ""),
            status=data.get("status", "pending"),
            verified_at=data.get("verified_at"),
        )


@dataclass
class VerificationReport:
    """Complete verification report for a phase.

    Stored as {phase}-VERIFICATION.md.
    """
    phase: str
    verified_at: str = ""

    # Overall status
    status: VerificationStatus = VerificationStatus.GAPS_FOUND
    score: float = 0.0  # 0-1, percentage of checks passed

    # Individual results
    truths: List[TruthVerification] = field(default_factory=list)
    artifacts: List[ArtifactVerification] = field(default_factory=list)
    links: List[LinkVerification] = field(default_factory=list)

    # Gaps summary
    gaps: List[str] = field(default_factory=list)
    human_verification_needed: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.verified_at:
            self.verified_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "verified_at": self.verified_at,
            "status": self.status.value,
            "score": self.score,
            "truths": [t.to_dict() for t in self.truths],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "links": [l.to_dict() for l in self.links],
            "gaps": self.gaps,
            "human_verification_needed": self.human_verification_needed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationReport":
        status_str = data.get("status", "gaps_found")
        try:
            status = VerificationStatus(status_str)
        except ValueError:
            status = VerificationStatus.GAPS_FOUND

        return cls(
            phase=data.get("phase", ""),
            verified_at=data.get("verified_at", ""),
            status=status,
            score=data.get("score", 0.0),
            truths=[TruthVerification.from_dict(t) for t in data.get("truths", [])],
            artifacts=[ArtifactVerification.from_dict(a) for a in data.get("artifacts", [])],
            links=[LinkVerification.from_dict(l) for l in data.get("links", [])],
            gaps=data.get("gaps", []),
            human_verification_needed=data.get("human_verification_needed", []),
        )

    def compute_status(self) -> None:
        """Compute overall status from individual results."""
        total_checks = len(self.truths) + len(self.artifacts) + len(self.links)
        if total_checks == 0:
            self.status = VerificationStatus.PASSED
            self.score = 1.0
            return

        passed = 0
        human_needed = 0

        for t in self.truths:
            if t.status == "passed":
                passed += 1
            elif t.status == "human_needed":
                human_needed += 1

        for a in self.artifacts:
            if a.status == "passed":
                passed += 1

        for l in self.links:
            if l.status == "passed":
                passed += 1

        self.score = passed / total_checks

        if human_needed > 0:
            self.status = VerificationStatus.HUMAN_NEEDED
        elif passed == total_checks:
            self.status = VerificationStatus.PASSED
        else:
            self.status = VerificationStatus.GAPS_FOUND

    def format_display(self) -> str:
        """Format report for display."""
        status_icon = {
            VerificationStatus.PASSED: "✅",
            VerificationStatus.GAPS_FOUND: "⚠️",
            VerificationStatus.HUMAN_NEEDED: "👤",
        }.get(self.status, "?")

        lines = [
            "=" * 60,
            f"Verification Report: {self.phase}",
            "=" * 60,
            f"Status: {status_icon} {self.status.value.upper()}",
            f"Score: {self.score * 100:.1f}%",
            "",
        ]

        # Truths
        lines.append("## Observable Truths")
        lines.append("-" * 40)
        for t in self.truths:
            icon = "✅" if t.status == "passed" else ("👤" if t.status == "human_needed" else "❌")
            lines.append(f"{icon} {t.description}")
        lines.append("")

        # Artifacts
        lines.append("## Required Artifacts")
        lines.append("-" * 40)
        for a in self.artifacts:
            icon = "✅" if a.status == "passed" else "❌"
            stub = " (STUB)" if a.is_stub else ""
            lines.append(f"{icon} {a.path}{stub} [{a.line_count} lines]")
        lines.append("")

        # Links
        lines.append("## Key Links")
        lines.append("-" * 40)
        for l in self.links:
            icon = "✅" if l.status == "passed" else "❌"
            lines.append(f"{icon} {l.from_component} → {l.to_component} via {l.via}")
        lines.append("")

        # Gaps
        if self.gaps:
            lines.append("## Gaps")
            lines.append("-" * 40)
            for g in self.gaps:
                lines.append(f"  • {g}")
            lines.append("")

        # Human verification
        if self.human_verification_needed:
            lines.append("## Human Verification Needed")
            lines.append("-" * 40)
            for h in self.human_verification_needed:
                lines.append(f"  👤 {h}")

        return "\n".join(lines)


def save_verification_report(project_path: str, report: VerificationReport) -> str:
    """Save verification report to project.

    Args:
        project_path: Path to project root
        report: Report to save

    Returns:
        Path to saved file
    """
    import os

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", report.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, f"{report.phase}-VERIFICATION.json")
    with open(file_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    return file_path


def load_verification_report(project_path: str, phase: str) -> Optional[VerificationReport]:
    """Load verification report from project.

    Args:
        project_path: Path to project root
        phase: Phase name

    Returns:
        Report if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "phases", phase, f"{phase}-VERIFICATION.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return VerificationReport.from_dict(data)
