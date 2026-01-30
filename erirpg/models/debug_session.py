"""
Debug session model for systematic debugging.

Uses scientific method:
1. Observe symptoms
2. Form hypotheses
3. Eliminate hypotheses
4. Gather evidence
5. Find resolution
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class Hypothesis:
    """A hypothesis about the bug cause."""
    id: str
    description: str

    # Status
    status: str = "active"  # active, eliminated, confirmed
    elimination_reason: str = ""  # Why it was eliminated
    confirmation_evidence: str = ""  # Evidence that confirmed it

    # Testing
    test_approach: str = ""  # How to test this hypothesis
    tested_at: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            import hashlib
            data = f"{self.description}:{datetime.now().isoformat()}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "elimination_reason": self.elimination_reason,
            "confirmation_evidence": self.confirmation_evidence,
            "test_approach": self.test_approach,
            "tested_at": self.tested_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hypothesis":
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            status=data.get("status", "active"),
            elimination_reason=data.get("elimination_reason", ""),
            confirmation_evidence=data.get("confirmation_evidence", ""),
            test_approach=data.get("test_approach", ""),
            tested_at=data.get("tested_at"),
        )

    def eliminate(self, reason: str) -> None:
        """Eliminate this hypothesis."""
        self.status = "eliminated"
        self.elimination_reason = reason
        self.tested_at = datetime.now().isoformat()

    def confirm(self, evidence: str) -> None:
        """Confirm this hypothesis as the cause."""
        self.status = "confirmed"
        self.confirmation_evidence = evidence
        self.tested_at = datetime.now().isoformat()


@dataclass
class Evidence:
    """Evidence gathered during debugging."""
    id: str
    type: str  # "log", "stack_trace", "repro_steps", "test_result", "observation"
    description: str
    content: str = ""  # The actual evidence (log output, etc.)
    source: str = ""  # Where this came from
    gathered_at: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            import hashlib
            data = f"{self.type}:{self.description}:{datetime.now().isoformat()}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:8]
        if not self.gathered_at:
            self.gathered_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "content": self.content,
            "source": self.source,
            "gathered_at": self.gathered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            description=data.get("description", ""),
            content=data.get("content", ""),
            source=data.get("source", ""),
            gathered_at=data.get("gathered_at"),
        )


@dataclass
class DebugSession:
    """A debugging session using scientific method.

    Stored as .eri-rpg/debug/active-session.md while active.
    Moved to .eri-rpg/debug/resolved/ when resolved.
    """
    id: str

    # Trigger
    trigger: str = ""  # What triggered this debug session
    error_message: str = ""
    stack_trace: str = ""

    # Status
    status: str = "investigating"  # investigating, root_cause_found, resolved, abandoned

    # Symptoms
    symptoms: List[str] = field(default_factory=list)

    # Hypotheses
    hypotheses: List[Hypothesis] = field(default_factory=list)

    # Evidence
    evidence: List[Evidence] = field(default_factory=list)

    # Resolution
    root_cause: str = ""
    resolution: str = ""  # How it was fixed
    fix_files: List[str] = field(default_factory=list)  # Files modified in fix

    # Metadata
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            import hashlib
            data = f"{self.trigger}:{self.created_at}"
            self.id = hashlib.sha1(data.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "status": self.status,
            "symptoms": self.symptoms,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "evidence": [e.to_dict() for e in self.evidence],
            "root_cause": self.root_cause,
            "resolution": self.resolution,
            "fix_files": self.fix_files,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugSession":
        return cls(
            id=data.get("id", ""),
            trigger=data.get("trigger", ""),
            error_message=data.get("error_message", ""),
            stack_trace=data.get("stack_trace", ""),
            status=data.get("status", "investigating"),
            symptoms=data.get("symptoms", []),
            hypotheses=[Hypothesis.from_dict(h) for h in data.get("hypotheses", [])],
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            root_cause=data.get("root_cause", ""),
            resolution=data.get("resolution", ""),
            fix_files=data.get("fix_files", []),
            created_at=data.get("created_at"),
            resolved_at=data.get("resolved_at"),
        )

    def add_symptom(self, symptom: str) -> None:
        """Add an observed symptom."""
        self.symptoms.append(symptom)

    def add_hypothesis(self, description: str, test_approach: str = "") -> Hypothesis:
        """Add a hypothesis."""
        h = Hypothesis(
            id="",
            description=description,
            test_approach=test_approach,
        )
        self.hypotheses.append(h)
        return h

    def add_evidence(
        self,
        type: str,
        description: str,
        content: str = "",
        source: str = "",
    ) -> Evidence:
        """Add evidence."""
        e = Evidence(
            id="",
            type=type,
            description=description,
            content=content,
            source=source,
        )
        self.evidence.append(e)
        return e

    def get_active_hypotheses(self) -> List[Hypothesis]:
        """Get hypotheses that haven't been eliminated."""
        return [h for h in self.hypotheses if h.status == "active"]

    def get_confirmed_hypothesis(self) -> Optional[Hypothesis]:
        """Get the confirmed hypothesis if any."""
        for h in self.hypotheses:
            if h.status == "confirmed":
                return h
        return None

    def set_root_cause(self, root_cause: str) -> None:
        """Set the root cause."""
        self.root_cause = root_cause
        self.status = "root_cause_found"

    def resolve(self, resolution: str, fix_files: List[str] = None) -> None:
        """Mark session as resolved."""
        self.resolution = resolution
        self.fix_files = fix_files or []
        self.status = "resolved"
        self.resolved_at = datetime.now().isoformat()

    def abandon(self, reason: str) -> None:
        """Abandon this debug session."""
        self.status = "abandoned"
        self.resolution = f"Abandoned: {reason}"
        self.resolved_at = datetime.now().isoformat()

    def format_display(self) -> str:
        """Format session for display."""
        status_icon = {
            "investigating": "🔍",
            "root_cause_found": "🎯",
            "resolved": "✅",
            "abandoned": "❌",
        }.get(self.status, "?")

        lines = [
            "=" * 60,
            f"Debug Session: {self.id}",
            "=" * 60,
            f"Status: {status_icon} {self.status.upper()}",
            "",
            "## Trigger",
            self.trigger,
            "",
        ]

        if self.error_message:
            lines.extend(["## Error Message", self.error_message, ""])

        if self.symptoms:
            lines.append("## Symptoms")
            for s in self.symptoms:
                lines.append(f"- {s}")
            lines.append("")

        if self.hypotheses:
            lines.append("## Hypotheses")
            for h in self.hypotheses:
                icon = {"active": "❓", "eliminated": "❌", "confirmed": "✅"}.get(h.status, "?")
                lines.append(f"{icon} {h.description}")
                if h.status == "eliminated":
                    lines.append(f"   Eliminated: {h.elimination_reason}")
                elif h.status == "confirmed":
                    lines.append(f"   Confirmed: {h.confirmation_evidence}")
            lines.append("")

        if self.evidence:
            lines.append("## Evidence")
            for e in self.evidence:
                lines.append(f"[{e.type}] {e.description}")
            lines.append("")

        if self.root_cause:
            lines.append("## Root Cause")
            lines.append(self.root_cause)
            lines.append("")

        if self.resolution:
            lines.append("## Resolution")
            lines.append(self.resolution)
            if self.fix_files:
                lines.append("Files modified:")
                for f in self.fix_files:
                    lines.append(f"  - {f}")

        return "\n".join(lines)


def save_debug_session(project_path: str, session: DebugSession) -> str:
    """Save debug session to project.

    Args:
        project_path: Path to project root
        session: Session to save

    Returns:
        Path to saved file
    """
    import os

    if session.status in ("resolved", "abandoned"):
        debug_dir = os.path.join(project_path, ".eri-rpg", "debug", "resolved")
    else:
        debug_dir = os.path.join(project_path, ".eri-rpg", "debug")

    os.makedirs(debug_dir, exist_ok=True)

    if session.status in ("resolved", "abandoned"):
        file_path = os.path.join(debug_dir, f"{session.id}.json")
    else:
        file_path = os.path.join(debug_dir, "active-session.json")

    with open(file_path, "w") as f:
        json.dump(session.to_dict(), f, indent=2)

    return file_path


def load_active_debug_session(project_path: str) -> Optional[DebugSession]:
    """Load the active debug session if any.

    Args:
        project_path: Path to project root

    Returns:
        Active DebugSession if found, None otherwise
    """
    import os

    file_path = os.path.join(project_path, ".eri-rpg", "debug", "active-session.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return DebugSession.from_dict(data)


def load_debug_session(project_path: str, session_id: str) -> Optional[DebugSession]:
    """Load a debug session by ID.

    Args:
        project_path: Path to project root
        session_id: Session ID

    Returns:
        DebugSession if found, None otherwise
    """
    import os

    # Check active session
    active = load_active_debug_session(project_path)
    if active and active.id == session_id:
        return active

    # Check resolved sessions
    file_path = os.path.join(project_path, ".eri-rpg", "debug", "resolved", f"{session_id}.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return DebugSession.from_dict(data)
