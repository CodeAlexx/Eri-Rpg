"""
UAT (User Acceptance Testing) model.

UAT.md captures human verification results:
- Manual tests performed
- Results observed
- Diagnoses for failures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class UATTest:
    """A single user acceptance test."""
    id: str
    description: str  # What to test
    steps: List[str] = field(default_factory=list)  # Steps to perform
    expected: str = ""  # Expected result

    # Results
    status: str = "pending"  # pending, passed, failed
    actual: str = ""  # What was actually observed
    tested_by: str = ""  # Who performed the test
    tested_at: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if not self.id:
            import hashlib
            data = f"{self.description}:{datetime.now().isoformat()}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "steps": self.steps,
            "expected": self.expected,
            "status": self.status,
            "actual": self.actual,
            "tested_by": self.tested_by,
            "tested_at": self.tested_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UATTest":
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            expected=data.get("expected", ""),
            status=data.get("status", "pending"),
            actual=data.get("actual", ""),
            tested_by=data.get("tested_by", ""),
            tested_at=data.get("tested_at"),
            notes=data.get("notes", ""),
        )

    def mark_passed(self, actual: str, tested_by: str = "user") -> None:
        """Mark test as passed."""
        self.status = "passed"
        self.actual = actual
        self.tested_by = tested_by
        self.tested_at = datetime.now().isoformat()

    def mark_failed(self, actual: str, notes: str = "", tested_by: str = "user") -> None:
        """Mark test as failed."""
        self.status = "failed"
        self.actual = actual
        self.notes = notes
        self.tested_by = tested_by
        self.tested_at = datetime.now().isoformat()

    def format_display(self) -> str:
        """Format test for display."""
        icon = {"passed": "✅", "failed": "❌", "pending": "⏳"}.get(self.status, "?")

        lines = [
            f"{icon} **{self.description}**",
        ]

        if self.steps:
            lines.append("Steps:")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"  {i}. {step}")

        lines.append(f"Expected: {self.expected}")

        if self.status != "pending":
            lines.append(f"Actual: {self.actual}")
            if self.notes:
                lines.append(f"Notes: {self.notes}")

        return "\n".join(lines)


@dataclass
class UATDiagnosis:
    """Diagnosis for a failed UAT test."""
    test_id: str
    category: str  # "bug", "user_error", "environment", "spec_unclear"
    description: str
    root_cause: str = ""
    recommended_action: str = ""  # What to do about it
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "category": self.category,
            "description": self.description,
            "root_cause": self.root_cause,
            "recommended_action": self.recommended_action,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UATDiagnosis":
        return cls(
            test_id=data.get("test_id", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            root_cause=data.get("root_cause", ""),
            recommended_action=data.get("recommended_action", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class UAT:
    """User Acceptance Testing report for a phase.

    Stored as {phase}-UAT.md.
    """
    phase: str
    title: str = ""

    # Tests
    tests: List[UATTest] = field(default_factory=list)

    # Diagnoses for failures
    diagnoses: List[UATDiagnosis] = field(default_factory=list)

    # Overall status
    status: str = "pending"  # pending, in_progress, passed, failed
    pass_rate: float = 0.0

    # Metadata
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    tested_by: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "title": self.title,
            "tests": [t.to_dict() for t in self.tests],
            "diagnoses": [d.to_dict() for d in self.diagnoses],
            "status": self.status,
            "pass_rate": self.pass_rate,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tested_by": self.tested_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UAT":
        return cls(
            phase=data.get("phase", ""),
            title=data.get("title", ""),
            tests=[UATTest.from_dict(t) for t in data.get("tests", [])],
            diagnoses=[UATDiagnosis.from_dict(d) for d in data.get("diagnoses", [])],
            status=data.get("status", "pending"),
            pass_rate=data.get("pass_rate", 0.0),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            tested_by=data.get("tested_by", ""),
        )

    def add_test(
        self,
        description: str,
        steps: List[str],
        expected: str,
    ) -> UATTest:
        """Add a test to the UAT."""
        test = UATTest(
            id="",
            description=description,
            steps=steps,
            expected=expected,
        )
        self.tests.append(test)
        return test

    def get_test(self, test_id: str) -> Optional[UATTest]:
        """Get a test by ID."""
        for test in self.tests:
            if test.id == test_id:
                return test
        return None

    def add_diagnosis(
        self,
        test_id: str,
        category: str,
        description: str,
        root_cause: str = "",
        recommended_action: str = "",
    ) -> UATDiagnosis:
        """Add a diagnosis for a failed test."""
        diagnosis = UATDiagnosis(
            test_id=test_id,
            category=category,
            description=description,
            root_cause=root_cause,
            recommended_action=recommended_action,
        )
        self.diagnoses.append(diagnosis)
        return diagnosis

    def compute_status(self) -> None:
        """Compute overall status from test results."""
        if not self.tests:
            self.status = "pending"
            self.pass_rate = 0.0
            return

        total = len(self.tests)
        passed = sum(1 for t in self.tests if t.status == "passed")
        pending = sum(1 for t in self.tests if t.status == "pending")

        self.pass_rate = passed / total if total > 0 else 0.0

        if pending > 0:
            self.status = "in_progress"
        elif passed == total:
            self.status = "passed"
            self.completed_at = datetime.now().isoformat()
        else:
            self.status = "failed"
            self.completed_at = datetime.now().isoformat()

    def format_display(self) -> str:
        """Format UAT report for display."""
        status_icon = {
            "passed": "✅",
            "failed": "❌",
            "in_progress": "🔄",
            "pending": "⏳",
        }.get(self.status, "?")

        lines = [
            "=" * 60,
            f"UAT Report: {self.phase}",
            "=" * 60,
            f"Status: {status_icon} {self.status.upper()}",
            f"Pass Rate: {self.pass_rate * 100:.1f}%",
            "",
            "## Tests",
            "-" * 40,
        ]

        for test in self.tests:
            lines.append(test.format_display())
            lines.append("")

        if self.diagnoses:
            lines.append("## Diagnoses")
            lines.append("-" * 40)
            for d in self.diagnoses:
                lines.append(f"[{d.category}] {d.description}")
                if d.root_cause:
                    lines.append(f"  Root cause: {d.root_cause}")
                if d.recommended_action:
                    lines.append(f"  Action: {d.recommended_action}")
                lines.append("")

        return "\n".join(lines)


def save_uat(project_path: str, uat: UAT) -> str:
    """Save UAT report to project.

    Args:
        project_path: Path to project root
        uat: UAT to save

    Returns:
        Path to saved file
    """
    import os

    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", uat.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, f"{uat.phase}-UAT.json")
    with open(file_path, "w") as f:
        json.dump(uat.to_dict(), f, indent=2)

    return file_path


def load_uat(project_path: str, phase: str) -> Optional[UAT]:
    """Load UAT report from project.

    Args:
        project_path: Path to project root
        phase: Phase name

    Returns:
        UAT if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "phases", phase, f"{phase}-UAT.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return UAT.from_dict(data)
