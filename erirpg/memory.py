"""
Persistent semantic memory for EriRPG.

This module provides the KnowledgeStore - a separate storage layer for
semantic knowledge that persists independently of the structural graph.

Key design principles:
- Knowledge survives reindexing (stored in separate knowledge.json)
- Staleness is tracked via CodeRefs
- Search enables finding relevant learnings by query

Storage structure:
    .eri-rpg/
    ├── graph.json       # Structural index (rebuildable)
    ├── knowledge.json   # Semantic memory (PRESERVED)
    └── runs/            # Execution history (in knowledge.json)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import json
import os
from pathlib import Path

from erirpg.refs import CodeRef


@dataclass
class RunRecord:
    """Record of a command execution for context tracking.

    Attributes:
        timestamp: When the command was run
        command: The command that was executed
        modules_read: List of modules that were read during execution
        modules_written: List of modules that were written/modified
        success: Whether the command completed successfully
        duration_ms: How long the command took in milliseconds
        notes: Optional notes about the run
    """
    timestamp: datetime
    command: str
    modules_read: List[str] = field(default_factory=list)
    modules_written: List[str] = field(default_factory=list)
    success: bool = True
    duration_ms: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "command": self.command,
            "modules_read": self.modules_read,
            "modules_written": self.modules_written,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunRecord":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            command=d["command"],
            modules_read=d.get("modules_read", []),
            modules_written=d.get("modules_written", []),
            success=d.get("success", True),
            duration_ms=d.get("duration_ms", 0),
            notes=d.get("notes", ""),
        )


@dataclass
class StoredLearning:
    """A learning stored in the knowledge store.

    This is the storage representation that includes the CodeRef.
    The Learning class in knowledge.py can be converted to/from this.
    """
    module_path: str
    learned_at: datetime
    summary: str
    purpose: str
    key_functions: Dict[str, str] = field(default_factory=dict)
    key_params: Dict[str, str] = field(default_factory=dict)
    gotchas: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    transplanted_to: Optional[str] = None
    source_ref: Optional[CodeRef] = None
    confidence: float = 1.0
    version: int = 1

    def is_stale(self, project_path: str) -> bool:
        """Check if this learning is stale (source changed)."""
        if self.source_ref is None:
            return False  # No ref to check
        return self.source_ref.is_stale(project_path)

    def format_for_context(self, project_path: str = None) -> str:
        """Format learning for inclusion in context file.

        Args:
            project_path: If provided, include staleness warning if source changed

        Returns:
            Formatted string for CLI display
        """
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

        # Add staleness warning if we can check
        if project_path and self.is_stale(project_path):
            lines.insert(0, "⚠️  **WARNING**: Source file has changed since this learning was created!")
            lines.insert(1, "")

        return "\n".join(lines)

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
    def from_dict(cls, d: dict) -> "StoredLearning":
        source_ref = None
        if "source_ref" in d:
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


@dataclass
class StoredDecision:
    """An architectural or design decision stored in knowledge."""
    id: str
    date: datetime
    title: str
    reason: str
    affects: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

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
    def from_dict(cls, d: dict) -> "StoredDecision":
        return cls(
            id=d["id"],
            date=datetime.fromisoformat(d["date"]),
            title=d["title"],
            reason=d.get("reason", ""),
            affects=d.get("affects", []),
            alternatives=d.get("alternatives", []),
        )


@dataclass
class KnowledgeStore:
    """Persistent semantic knowledge store.

    Stores learnings, decisions, patterns, and run history
    independently of the structural graph. Survives reindexing.
    """
    project: str
    version: str = "2.0.0"
    learnings: Dict[str, StoredLearning] = field(default_factory=dict)
    decisions: List[StoredDecision] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)
    runs: List[RunRecord] = field(default_factory=list)

    # CRUD for learnings

    def add_learning(self, learning: StoredLearning) -> None:
        """Add or update a learning."""
        self.learnings[learning.module_path] = learning

    def get_learning(self, module_path: str) -> Optional[StoredLearning]:
        """Get learning for a module path."""
        return self.learnings.get(module_path)

    def has_learning(self, module_path: str) -> bool:
        """Check if learning exists for a module."""
        return module_path in self.learnings

    def remove_learning(self, module_path: str) -> bool:
        """Remove a learning. Returns True if it existed."""
        if module_path in self.learnings:
            del self.learnings[module_path]
            return True
        return False

    # CRUD for decisions

    def add_decision(self, decision: StoredDecision) -> None:
        """Add a decision."""
        self.decisions.append(decision)

    def get_decisions_for_module(self, module_path: str) -> List[StoredDecision]:
        """Get all decisions affecting a module."""
        return [d for d in self.decisions if module_path in d.affects]

    # CRUD for patterns

    def add_pattern(self, name: str, description: str) -> None:
        """Add or update a pattern."""
        self.patterns[name] = description

    def get_pattern(self, name: str) -> Optional[str]:
        """Get a pattern by name."""
        return self.patterns.get(name)

    # Run tracking

    def add_run(self, run: RunRecord) -> None:
        """Add a run record."""
        self.runs.append(run)

    def get_recent_runs(self, limit: int = 10) -> List[RunRecord]:
        """Get most recent run records."""
        return sorted(self.runs, key=lambda r: r.timestamp, reverse=True)[:limit]

    # Staleness detection

    def get_stale_learnings(self, project_path: str) -> List[str]:
        """Find all learnings whose source files have changed.

        Args:
            project_path: Root path of the project

        Returns:
            List of module paths with stale learnings
        """
        stale = []
        for module_path, learning in self.learnings.items():
            if learning.is_stale(project_path):
                stale.append(module_path)
        return stale

    def get_fresh_learnings(self, project_path: str) -> List[str]:
        """Find all learnings that are still fresh.

        Args:
            project_path: Root path of the project

        Returns:
            List of module paths with fresh learnings
        """
        fresh = []
        for module_path, learning in self.learnings.items():
            if not learning.is_stale(project_path):
                fresh.append(module_path)
        return fresh

    # Search

    def search(self, query: str, limit: int = 10) -> List[tuple[str, StoredLearning, float]]:
        """Search learnings by query.

        Simple keyword-based search matching against:
        - Module path
        - Summary
        - Purpose
        - Key function names and descriptions
        - Gotchas

        Args:
            query: Search query (space-separated keywords)
            limit: Maximum results to return

        Returns:
            List of (module_path, learning, score) tuples
        """
        from erirpg.search import search_learnings
        return search_learnings(self.learnings, query, limit)

    # Statistics

    def stats(self) -> dict:
        """Get knowledge store statistics."""
        return {
            "learnings": len(self.learnings),
            "decisions": len(self.decisions),
            "patterns": len(self.patterns),
            "runs": len(self.runs),
        }

    # Persistence

    def save(self, path: str) -> None:
        """Save knowledge store to JSON file.

        Args:
            path: Path to knowledge.json file
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project": self.project,
            "version": self.version,
            "saved_at": datetime.now().isoformat(),
            "learnings": {k: v.to_dict() for k, v in self.learnings.items()},
            "decisions": [d.to_dict() for d in self.decisions],
            "patterns": self.patterns,
            "runs": [r.to_dict() for r in self.runs[-100:]],  # Keep last 100 runs
        }

        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "KnowledgeStore":
        """Load knowledge store from JSON file.

        Args:
            path: Path to knowledge.json file

        Returns:
            Loaded KnowledgeStore, or empty one if file doesn't exist
        """
        if not os.path.exists(path):
            # Return empty store - caller should set project name
            return cls(project="unknown")

        with open(path, "r") as f:
            data = json.load(f)

        return cls(
            project=data.get("project", "unknown"),
            version=data.get("version", "2.0.0"),
            learnings={
                k: StoredLearning.from_dict(v)
                for k, v in data.get("learnings", {}).items()
            },
            decisions=[
                StoredDecision.from_dict(d)
                for d in data.get("decisions", [])
            ],
            patterns=data.get("patterns", {}),
            runs=[
                RunRecord.from_dict(r)
                for r in data.get("runs", [])
            ],
        )


def get_knowledge_path(project_path: str) -> str:
    """Get the path to knowledge.json for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Path to .eri-rpg/knowledge.json
    """
    return os.path.join(project_path, ".eri-rpg", "knowledge.json")


def load_knowledge(project_path: str, project_name: str) -> KnowledgeStore:
    """Load knowledge store for a project.

    Args:
        project_path: Root path of the project
        project_name: Name of the project

    Returns:
        KnowledgeStore for the project
    """
    path = get_knowledge_path(project_path)
    store = KnowledgeStore.load(path)
    if store.project == "unknown":
        store.project = project_name
    return store


def save_knowledge(project_path: str, store: KnowledgeStore) -> None:
    """Save knowledge store for a project.

    Args:
        project_path: Root path of the project
        store: KnowledgeStore to save
    """
    path = get_knowledge_path(project_path)
    store.save(path)
