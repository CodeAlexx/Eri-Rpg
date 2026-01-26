"""
Knowledge storage for EriRPG.

Stores learnings about code so Claude Code doesn't have to re-read
and re-learn modules every session.

Components:
- Learning: What was understood about a module (summary, key functions, gotchas)
- Decision: Architectural/design decisions with rationale
- Pattern: Reusable patterns and gotchas
- HistoryEntry: Log of actions taken (transplants, modifications)

Note: This module maintains backward compatibility with v1 storage.
For v2 persistent storage that survives reindexing, see memory.py.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from erirpg.refs import CodeRef


@dataclass
class Learning:
    """What Claude Code learned about a module.

    Attributes:
        module_path: Path to the module relative to project root
        learned_at: When the learning was created
        summary: One-line purpose/summary
        purpose: Detailed explanation
        key_functions: Map of function name -> description
        key_params: Map of parameter name -> explanation
        gotchas: List of things to watch out for
        dependencies: External dependencies used
        transplanted_to: If this was transplanted somewhere
        source_ref: Reference to the source code (for staleness detection)
        confidence: How confident we are in this learning (0.0-1.0)
        version: Version number for tracking updates
    """
    module_path: str
    learned_at: datetime
    summary: str  # One-line purpose
    purpose: str  # Detailed explanation
    key_functions: Dict[str, str] = field(default_factory=dict)  # name -> description
    key_params: Dict[str, str] = field(default_factory=dict)  # param -> explanation
    gotchas: List[str] = field(default_factory=list)  # Things to watch out for
    dependencies: List[str] = field(default_factory=list)  # External deps used
    transplanted_to: Optional[str] = None  # If transplanted somewhere
    source_ref: Optional["CodeRef"] = None  # Reference to source code
    confidence: float = 1.0  # Confidence score (0.0-1.0)
    version: int = 1  # Version number

    def is_stale(self, project_path: str) -> bool:
        """Check if this learning is stale (source code changed).

        Args:
            project_path: Root path of the project

        Returns:
            True if source_ref exists and file has changed, False otherwise
        """
        if self.source_ref is None:
            return False  # No ref to check against
        return self.source_ref.is_stale(project_path)

    def to_dict(self) -> dict:
        d = {
            "module_path": self.module_path,
            "learned_at": self.learned_at.isoformat(),
            "summary": self.summary,
            "purpose": self.purpose,
            "key_functions": self.key_functions,
            "key_params": self.key_params,
            "gotchas": self.gotchas,
            "dependencies": self.dependencies,
            "transplanted_to": self.transplanted_to,
            "confidence": self.confidence,
            "version": self.version,
        }
        if self.source_ref:
            d["source_ref"] = self.source_ref.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Learning":
        source_ref = None
        if "source_ref" in d:
            from erirpg.refs import CodeRef
            source_ref = CodeRef.from_dict(d["source_ref"])

        return cls(
            module_path=d["module_path"],
            learned_at=datetime.fromisoformat(d["learned_at"]),
            summary=d.get("summary", ""),
            purpose=d.get("purpose", ""),
            key_functions=d.get("key_functions", {}),
            key_params=d.get("key_params", {}),
            gotchas=d.get("gotchas", []),
            dependencies=d.get("dependencies", []),
            transplanted_to=d.get("transplanted_to"),
            source_ref=source_ref,
            confidence=d.get("confidence", 1.0),
            version=d.get("version", 1),
        )

    def format_for_context(self) -> str:
        """Format learning for inclusion in context file."""
        lines = [
            f"### Stored Understanding (from {self.learned_at.strftime('%Y-%m-%d')})",
            f"",
            f"**Summary**: {self.summary}",
            f"",
            f"**Purpose**: {self.purpose}",
        ]

        if self.key_functions:
            lines.append("")
            lines.append("**Key Functions**:")
            for name, desc in self.key_functions.items():
                lines.append(f"- `{name}`: {desc}")

        if self.key_params:
            lines.append("")
            lines.append("**Key Parameters**:")
            for name, desc in self.key_params.items():
                lines.append(f"- `{name}`: {desc}")

        if self.gotchas:
            lines.append("")
            lines.append("**Gotchas**:")
            for g in self.gotchas:
                lines.append(f"- {g}")

        if self.dependencies:
            lines.append("")
            lines.append(f"**Dependencies**: {', '.join(self.dependencies)}")

        if self.transplanted_to:
            lines.append("")
            lines.append(f"**Transplanted to**: `{self.transplanted_to}`")

        return "\n".join(lines)


@dataclass
class Decision:
    """An architectural or design decision."""
    id: str
    date: datetime
    title: str
    reason: str
    affects: List[str] = field(default_factory=list)  # Module paths affected
    alternatives: List[str] = field(default_factory=list)  # What was considered

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "title": self.title,
            "reason": self.reason,
            "affects": self.affects,
            "alternatives": self.alternatives,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Decision":
        return cls(
            id=d["id"],
            date=datetime.fromisoformat(d["date"]),
            title=d["title"],
            reason=d.get("reason", ""),
            affects=d.get("affects", []),
            alternatives=d.get("alternatives", []),
        )


@dataclass
class HistoryEntry:
    """A logged action in the project history."""
    date: datetime
    action: str  # "transplant", "create", "modify", "delete"
    description: str
    feature: Optional[str] = None
    from_project: Optional[str] = None
    to_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "action": self.action,
            "description": self.description,
            "feature": self.feature,
            "from_project": self.from_project,
            "to_path": self.to_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            date=datetime.fromisoformat(d["date"]),
            action=d["action"],
            description=d.get("description", ""),
            feature=d.get("feature"),
            from_project=d.get("from_project"),
            to_path=d.get("to_path"),
        )


@dataclass
class Knowledge:
    """All knowledge stored for a project."""
    learnings: Dict[str, Learning] = field(default_factory=dict)  # module_path -> Learning
    decisions: List[Decision] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)  # name -> description
    history: List[HistoryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "learnings": {k: v.to_dict() for k, v in self.learnings.items()},
            "decisions": [d.to_dict() for d in self.decisions],
            "patterns": self.patterns,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Knowledge":
        return cls(
            learnings={k: Learning.from_dict(v) for k, v in d.get("learnings", {}).items()},
            decisions=[Decision.from_dict(x) for x in d.get("decisions", [])],
            patterns=d.get("patterns", {}),
            history=[HistoryEntry.from_dict(x) for x in d.get("history", [])],
        )

    # CRUD operations

    def add_learning(self, learning: Learning) -> None:
        """Add or update a learning for a module."""
        self.learnings[learning.module_path] = learning

    def get_learning(self, module_path: str) -> Optional[Learning]:
        """Get learning for a module, if exists."""
        return self.learnings.get(module_path)

    def has_learning(self, module_path: str) -> bool:
        """Check if learning exists for a module."""
        return module_path in self.learnings

    def remove_learning(self, module_path: str) -> bool:
        """Remove learning for a module. Returns True if removed."""
        if module_path in self.learnings:
            del self.learnings[module_path]
            return True
        return False

    def add_decision(self, decision: Decision) -> None:
        """Add a decision."""
        self.decisions.append(decision)

    def get_decisions_for_module(self, module_path: str) -> List[Decision]:
        """Get all decisions affecting a module."""
        return [d for d in self.decisions if module_path in d.affects]

    def add_pattern(self, name: str, description: str) -> None:
        """Add or update a pattern."""
        self.patterns[name] = description

    def get_pattern(self, name: str) -> Optional[str]:
        """Get a pattern by name."""
        return self.patterns.get(name)

    def log_action(self, entry: HistoryEntry) -> None:
        """Log an action to history."""
        self.history.append(entry)

    def get_recent_history(self, limit: int = 10) -> List[HistoryEntry]:
        """Get most recent history entries."""
        return sorted(self.history, key=lambda h: h.date, reverse=True)[:limit]

    def stats(self) -> dict:
        """Get knowledge statistics."""
        return {
            "learnings": len(self.learnings),
            "decisions": len(self.decisions),
            "patterns": len(self.patterns),
            "history_entries": len(self.history),
        }


def load_knowledge(graph_path: str) -> Knowledge:
    """Load knowledge from a graph.json file."""
    path = Path(graph_path)
    if not path.exists():
        return Knowledge()

    with open(path) as f:
        data = json.load(f)

    if "knowledge" not in data:
        return Knowledge()

    return Knowledge.from_dict(data["knowledge"])


def save_knowledge(graph_path: str, knowledge: Knowledge) -> None:
    """Save knowledge to a graph.json file (merges with existing)."""
    path = Path(graph_path)

    if path.exists():
        with open(path) as f:
            data = json.load(f)
    else:
        data = {}

    data["knowledge"] = knowledge.to_dict()

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
