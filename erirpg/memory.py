"""
Persistent semantic memory for EriRPG.

This module provides the KnowledgeStore - a separate storage layer for
semantic knowledge that persists independently of the structural graph.

Key design principles:
- Knowledge survives reindexing (stored in separate knowledge.json)
- Staleness is tracked via CodeRefs
- Search enables finding relevant learnings by query
- Version history enables rollback and operation tracking

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
import hashlib
import subprocess
from pathlib import Path

from erirpg.refs import CodeRef


# ============================================================================
# Helper Functions
# ============================================================================

def hash_file(path: str) -> str:
    """Get SHA256 hash of file content (first 16 chars)."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ""


def read_file_content(path: str) -> str:
    """Read file content safely."""
    try:
        with open(path, 'r', errors='replace') as f:
            return f.read()
    except Exception:
        return ""


def git_head() -> Optional[str]:
    """Get current git HEAD commit (first 12 chars)."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except Exception:
        pass
    return None


def in_git_repo() -> bool:
    """Check if we're in a git repo."""
    return git_head() is not None


# ============================================================================
# Learning Version (Snapshot)
# ============================================================================

@dataclass
class LearningVersion:
    """Snapshot of a learning at a point in time.

    Captures the state of a learning before a change is made,
    enabling rollback if something goes wrong.
    """
    version: int
    timestamp: datetime
    operation: str  # "refactor" | "modify" | "transplant" | "create"

    # Snapshot of understanding
    summary: str
    purpose: str
    key_functions: Dict[str, str] = field(default_factory=dict)
    gotchas: List[str] = field(default_factory=list)

    # What changed
    change_description: str = ""

    # File state at snapshot time
    files_hashes: Dict[str, str] = field(default_factory=dict)  # path -> content hash
    files_content: Optional[Dict[str, str]] = None  # path -> content (for small files)

    # Git info (if available)
    commit_before: Optional[str] = None
    commit_after: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "summary": self.summary,
            "purpose": self.purpose,
            "key_functions": self.key_functions,
            "gotchas": self.gotchas,
            "change_description": self.change_description,
            "files_hashes": self.files_hashes,
            "commit_before": self.commit_before,
            "commit_after": self.commit_after,
        }
        # Only include files_content if present and non-empty
        if self.files_content:
            d["files_content"] = self.files_content
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LearningVersion":
        return cls(
            version=d["version"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            operation=d["operation"],
            summary=d.get("summary", ""),
            purpose=d.get("purpose", ""),
            key_functions=d.get("key_functions", {}),
            gotchas=d.get("gotchas", []),
            change_description=d.get("change_description", ""),
            files_hashes=d.get("files_hashes", {}),
            files_content=d.get("files_content"),
            commit_before=d.get("commit_before"),
            commit_after=d.get("commit_after"),
        )


@dataclass
class RollbackResult:
    """Result of a file rollback operation.

    Tracks what was restored, what failed, and provides
    a formatted report for display.
    """
    from_version: int
    to_version: int
    module_path: str
    success: bool = True
    error: str = ""
    metadata_restored: bool = False
    files_restored: List[Dict] = field(default_factory=list)
    files_failed: List[str] = field(default_factory=list)
    git_commit: Optional[str] = None  # If git rollback was used

    def format(self) -> str:
        """Format rollback result for display."""
        lines = [
            f"{'═' * 50}",
            f" ROLLBACK: {self.module_path}",
            f"{'═' * 50}",
            f"From version: {self.from_version} → {self.to_version}",
        ]

        if not self.success:
            lines.append(f"\n✗ FAILED: {self.error}")
            return "\n".join(lines)

        lines.append("")

        if self.files_restored:
            lines.append(f"Files ({len(self.files_restored)}):")
            for f in self.files_restored:
                action = f.get("action", "unknown")
                path = f.get("path", "?")
                size = f.get("bytes", 0)

                if action == "restored":
                    lines.append(f"  ✓ {path} ({size} bytes)")
                elif action == "would_restore":
                    lines.append(f"  ○ {path} ({size} bytes) [dry run]")
                elif action == "failed":
                    lines.append(f"  ✗ {path}: {f.get('error', 'unknown error')}")

        if self.files_failed:
            lines.append(f"\nFailed files ({len(self.files_failed)}):")
            for path in self.files_failed:
                lines.append(f"  ✗ {path}")

        if self.metadata_restored:
            lines.append("\n✓ Learning metadata restored")

        if self.git_commit:
            lines.append(f"\nGit: reverted to {self.git_commit}")

        lines.append("")
        if self.success:
            lines.append("✅ ROLLBACK COMPLETE")
        else:
            lines.append("⚠️  ROLLBACK PARTIAL - some files failed")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "module_path": self.module_path,
            "success": self.success,
            "error": self.error,
            "metadata_restored": self.metadata_restored,
            "files_restored": self.files_restored,
            "files_failed": self.files_failed,
            "git_commit": self.git_commit,
        }


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

    Now includes version history for rollback capability.
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

    # Transplant tracking (enhanced)
    transplanted_from: Optional[str] = None  # "project:path" if this was transplanted
    transplanted_to_list: List[str] = field(default_factory=list)  # ["project:path", ...]

    # Version history for rollback
    versions: List[LearningVersion] = field(default_factory=list)
    current_version: int = 0

    def is_stale(self, project_path: str) -> bool:
        """Check if this learning is stale (source changed)."""
        if self.source_ref is None:
            return False  # No ref to check
        return self.source_ref.is_stale(project_path)

    def snapshot(
        self,
        operation: str,
        change_description: str,
        files: List[str],
        project_path: str = "",
        store_content: bool = True,
        max_content_lines: int = 500,
    ) -> LearningVersion:
        """
        Create a snapshot before making changes.

        Args:
            operation: What we're about to do ("refactor", "modify", "transplant", "create")
            change_description: Why we're making this change
            files: Files being modified
            project_path: Project root for resolving file paths
            store_content: Whether to store file contents
            max_content_lines: Max lines to store per file

        Returns:
            LearningVersion snapshot
        """
        version = LearningVersion(
            version=self.current_version + 1,
            timestamp=datetime.now(),
            operation=operation,
            summary=self.summary,
            purpose=self.purpose,
            key_functions=self.key_functions.copy(),
            gotchas=self.gotchas.copy(),
            change_description=change_description,
            files_hashes={},
            commit_before=git_head(),
        )

        # Store file hashes
        for f in files:
            full_path = os.path.join(project_path, f) if project_path else f
            if os.path.exists(full_path):
                version.files_hashes[f] = hash_file(full_path)

        # Store content for small files
        if store_content:
            version.files_content = {}
            for f in files:
                full_path = os.path.join(project_path, f) if project_path else f
                if os.path.exists(full_path):
                    content = read_file_content(full_path)
                    if content.count('\n') <= max_content_lines:
                        version.files_content[f] = content

        self.versions.append(version)
        return version

    def rollback(self, to_version: Optional[int] = None) -> "StoredLearning":
        """
        Rollback metadata to a previous version.

        NOTE: This only rolls back the learning metadata (summary, purpose, etc).
        To also restore files, use rollback_files().

        Args:
            to_version: Version NUMBER to rollback to (default: previous)

        Returns:
            Self with restored state
        """
        target_version = to_version if to_version is not None else self.current_version - 1

        if target_version < 1:
            raise ValueError(f"Cannot rollback to version {target_version} (versions start at 1)")

        # Find the version by its version number (not index!)
        old = None
        for v in self.versions:
            if v.version == target_version:
                old = v
                break

        if old is None:
            available = [v.version for v in self.versions]
            raise ValueError(
                f"Version {target_version} not found. "
                f"Available versions: {available}"
            )

        self.summary = old.summary
        self.purpose = old.purpose
        self.key_functions = old.key_functions.copy()
        self.gotchas = old.gotchas.copy()
        self.current_version = target_version

        return self

    def rollback_files(
        self,
        project_path: str,
        to_version: Optional[int] = None,
        dry_run: bool = False,
    ) -> "RollbackResult":
        """
        Rollback files to a previous version's snapshot.

        This actually restores file contents from the stored snapshot.
        Also rolls back the learning metadata.

        Args:
            project_path: Project root for resolving file paths
            to_version: Version NUMBER to rollback to (default: previous version)
            dry_run: If True, only report what would be restored without writing

        Returns:
            RollbackResult with details of what was/would be restored

        Raises:
            ValueError: If version not found or no file content stored
        """
        # Default to previous version
        target_version = to_version if to_version is not None else self.current_version - 1

        if target_version < 1:
            raise ValueError(f"Cannot rollback to version {target_version} (versions start at 1)")

        # Find the version by its version number (not index!)
        old = None
        for v in self.versions:
            if v.version == target_version:
                old = v
                break

        if old is None:
            available = [v.version for v in self.versions]
            raise ValueError(
                f"Version {target_version} not found. "
                f"Available versions: {available}"
            )

        result = RollbackResult(
            from_version=self.current_version,
            to_version=target_version,
            module_path=self.module_path,
        )

        # Check if we have file content to restore
        if not old.files_content:
            result.success = False
            result.error = (
                f"Version {target_version} has no stored file content. "
                "Was the snapshot created with store_content=False?"
            )
            return result

        # Restore files
        for file_path, content in old.files_content.items():
            full_path = os.path.join(project_path, file_path)

            # Check current state
            current_content = None
            if os.path.exists(full_path):
                current_content = read_file_content(full_path)
                current_hash = hash_file(full_path)
            else:
                current_hash = None

            # Check if file has changed from what we expect
            expected_hash = old.files_hashes.get(file_path)

            file_result = {
                "path": file_path,
                "had_content": current_content is not None,
                "content_changed": current_hash != expected_hash if expected_hash else False,
            }

            if dry_run:
                file_result["action"] = "would_restore"
                file_result["bytes"] = len(content)
            else:
                try:
                    # Create parent directories if needed
                    Path(full_path).parent.mkdir(parents=True, exist_ok=True)

                    # Write the restored content
                    with open(full_path, 'w') as f:
                        f.write(content)

                    file_result["action"] = "restored"
                    file_result["bytes"] = len(content)
                except Exception as e:
                    file_result["action"] = "failed"
                    file_result["error"] = str(e)
                    result.files_failed.append(file_path)

            result.files_restored.append(file_result)

        # Rollback metadata too (unless dry run)
        if not dry_run:
            self.rollback(target_version)
            result.metadata_restored = True

        result.success = len(result.files_failed) == 0
        return result

    def can_rollback_files(self, to_version: Optional[int] = None) -> bool:
        """Check if file rollback is possible for a version.

        Args:
            to_version: Version NUMBER to check (default: previous)

        Returns:
            True if version exists and has file content
        """
        target_version = to_version if to_version is not None else self.current_version - 1

        if target_version < 1:
            return False

        # Find the version by its version number
        for v in self.versions:
            if v.version == target_version:
                return bool(v.files_content)

        return False

    def get_version(self, version_num: int) -> Optional[LearningVersion]:
        """Get a specific version from history."""
        for v in self.versions:
            if v.version == version_num:
                return v
        return None

    def history_summary(self) -> str:
        """Get a summary of version history."""
        if not self.versions:
            return "No version history"

        lines = [f"Version history ({len(self.versions)} versions):"]
        for v in reversed(self.versions[-5:]):  # Show last 5
            marker = " (current)" if v.version == self.current_version else ""
            lines.append(
                f"  v{v.version}{marker} - {v.timestamp.strftime('%Y-%m-%d %H:%M')} - {v.operation}"
            )
            if v.change_description:
                lines.append(f"    {v.change_description[:60]}...")
        return "\n".join(lines)

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
            # New fields for versioning
            "transplanted_from": self.transplanted_from,
            "transplanted_to_list": self.transplanted_to_list,
            "current_version": self.current_version,
        }
        if self.source_ref:
            d["source_ref"] = self.source_ref.to_dict()
        # Include versions if any exist
        if self.versions:
            d["versions"] = [v.to_dict() for v in self.versions]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StoredLearning":
        source_ref = None
        if "source_ref" in d:
            source_ref = CodeRef.from_dict(d["source_ref"])

        # Load versions if present
        versions = []
        if "versions" in d:
            versions = [LearningVersion.from_dict(v) for v in d["versions"]]

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
            # New fields for versioning
            transplanted_from=d.get("transplanted_from"),
            transplanted_to_list=d.get("transplanted_to_list", []),
            versions=versions,
            current_version=d.get("current_version", 0),
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
class Discussion:
    """A goal clarification discussion.

    Stores questions asked and answers given before generating a spec.
    Keyed by goal hash for multiple discussions per project.
    """
    id: str  # hash of goal
    goal: str
    questions: List[str] = field(default_factory=list)
    answers: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    @staticmethod
    def make_id(goal: str) -> str:
        """Generate discussion ID from goal."""
        import hashlib
        return hashlib.sha256(goal.encode()).hexdigest()[:12]

    @classmethod
    def create(cls, goal: str, questions: List[str]) -> "Discussion":
        """Create a new discussion for a goal."""
        return cls(
            id=cls.make_id(goal),
            goal=goal,
            questions=questions,
        )

    def answer(self, question: str, answer: str) -> None:
        """Record an answer to a question."""
        self.answers[question] = answer

    def unanswered(self) -> List[str]:
        """Get questions that haven't been answered yet."""
        return [q for q in self.questions if q not in self.answers]

    def is_complete(self) -> bool:
        """Check if all questions have been answered."""
        return len(self.unanswered()) == 0

    def resolve(self) -> None:
        """Mark discussion as resolved."""
        self.resolved = True

    def summary(self) -> str:
        """Get a summary of the discussion for enriching goals."""
        lines = [f"Goal: {self.goal}", "Decisions:"]
        for q, a in self.answers.items():
            lines.append(f"  - {q}: {a}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "questions": self.questions,
            "answers": self.answers,
            "resolved": self.resolved,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Discussion":
        return cls(
            id=d["id"],
            goal=d["goal"],
            questions=d.get("questions", []),
            answers=d.get("answers", {}),
            resolved=d.get("resolved", False),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
        )


@dataclass
class KnowledgeStore:
    """Persistent semantic knowledge store.

    Stores learnings, decisions, patterns, discussions, and run history
    independently of the structural graph. Survives reindexing.
    """
    project: str
    version: str = "2.1.0"  # Bumped for discussions support
    learnings: Dict[str, StoredLearning] = field(default_factory=dict)
    decisions: List[StoredDecision] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)
    discussions: Dict[str, Discussion] = field(default_factory=dict)  # keyed by id
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

    def list_modules(self) -> List[str]:
        """List all modules with learnings."""
        return list(self.learnings.keys())

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

    # CRUD for discussions

    def add_discussion(self, discussion: Discussion) -> None:
        """Add or update a discussion."""
        self.discussions[discussion.id] = discussion

    def get_discussion(self, discussion_id: str) -> Optional[Discussion]:
        """Get a discussion by ID."""
        return self.discussions.get(discussion_id)

    def get_discussion_by_goal(self, goal: str) -> Optional[Discussion]:
        """Get a discussion by goal text."""
        disc_id = Discussion.make_id(goal)
        return self.discussions.get(disc_id)

    def remove_discussion(self, discussion_id: str) -> bool:
        """Remove a discussion. Returns True if it existed."""
        if discussion_id in self.discussions:
            del self.discussions[discussion_id]
            return True
        return False

    def clear_discussions(self) -> int:
        """Clear all discussions. Returns count removed."""
        count = len(self.discussions)
        self.discussions.clear()
        return count

    def list_discussions(self) -> List[Discussion]:
        """List all discussions, most recent first."""
        return sorted(
            self.discussions.values(),
            key=lambda d: d.created_at,
            reverse=True,
        )

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
            "discussions": len(self.discussions),
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
            "discussions": {k: v.to_dict() for k, v in self.discussions.items()},
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
            version=data.get("version", "2.1.0"),
            learnings={
                k: StoredLearning.from_dict(v)
                for k, v in data.get("learnings", {}).items()
            },
            decisions=[
                StoredDecision.from_dict(d)
                for d in data.get("decisions", [])
            ],
            patterns=data.get("patterns", {}),
            discussions={
                k: Discussion.from_dict(v)
                for k, v in data.get("discussions", {}).items()
            },
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


# ============================================================================
# Operation-Aware Learning Updates
# ============================================================================

class LearningUpdatePolicy:
    """How to update learnings based on operation type."""
    REFACTOR = "replace"      # Old learning replaced with new
    TRANSPLANT = "duplicate"  # Source keeps learning, target gets new one
    MODIFY = "append"         # Add new info, keep existing
    NEW = "create"            # Fresh learning for new code


def update_learning_with_operation(
    store: KnowledgeStore,
    module_path: str,
    operation: str,
    new_understanding: dict,
    project_path: str = "",
    source_learning: Optional[StoredLearning] = None,
    change_description: str = "",
) -> StoredLearning:
    """
    Update learning based on operation type.

    Different operations handle learnings differently:
    - refactor: Replace understanding, preserve gotchas
    - transplant: Duplicate learning to target, link to source
    - modify: Append new info to existing
    - new: Create fresh learning

    Args:
        store: KnowledgeStore to update
        module_path: Module path
        operation: "refactor" | "transplant" | "modify" | "new"
        new_understanding: Dict with summary, purpose, key_functions, gotchas
        project_path: Project root for file path resolution
        source_learning: For transplants, the source learning
        change_description: What changed and why

    Returns:
        Updated or new StoredLearning
    """
    existing = store.get_learning(module_path)

    if operation == "new" or (operation == "transplant" and not existing):
        # Create fresh learning
        learning = StoredLearning(
            module_path=module_path,
            learned_at=datetime.now(),
            summary=new_understanding.get('summary', ''),
            purpose=new_understanding.get('purpose', ''),
            key_functions=new_understanding.get('key_functions', {}),
            gotchas=new_understanding.get('gotchas', []),
            current_version=1,
        )

        if source_learning:
            learning.transplanted_from = f"{source_learning.module_path}"
            # Update source to track where it was transplanted
            source_learning.transplanted_to_list.append(module_path)

        # Create initial version snapshot
        learning.snapshot(
            operation="create",
            change_description=change_description or "Initial learning",
            files=[module_path],
            project_path=project_path,
        )
        learning.current_version = 1

        store.add_learning(learning)
        return learning

    elif operation == "refactor":
        # Replace understanding, preserve gotchas unless explicitly changed
        existing.snapshot(
            operation=operation,
            change_description=change_description,
            files=[module_path],
            project_path=project_path,
        )

        existing.summary = new_understanding.get('summary', existing.summary)
        existing.purpose = new_understanding.get('purpose', existing.purpose)
        existing.key_functions = new_understanding.get('key_functions', existing.key_functions)

        # Merge gotchas - don't lose hard-won knowledge
        new_gotchas = new_understanding.get('gotchas', [])
        for gotcha in new_gotchas:
            if gotcha not in existing.gotchas:
                existing.gotchas.append(gotcha)

        existing.current_version += 1
        existing.learned_at = datetime.now()

        store.add_learning(existing)
        return existing

    elif operation == "modify":
        # Append new info, preserve existing
        existing.snapshot(
            operation=operation,
            change_description=change_description,
            files=[module_path],
            project_path=project_path,
        )

        # Append to summary if new info provided
        new_summary = new_understanding.get('summary', '')
        if new_summary and new_summary not in existing.summary:
            existing.summary += f"\n\n[Modified]: {new_summary}"

        # Append to purpose if new info provided
        new_purpose = new_understanding.get('purpose', '')
        if new_purpose and new_purpose not in existing.purpose:
            existing.purpose += f"\n\n[Modified]: {new_purpose}"

        # Merge key functions
        for name, desc in new_understanding.get('key_functions', {}).items():
            existing.key_functions[name] = desc

        # Append gotchas
        for gotcha in new_understanding.get('gotchas', []):
            if gotcha not in existing.gotchas:
                existing.gotchas.append(gotcha)

        existing.current_version += 1
        existing.learned_at = datetime.now()

        store.add_learning(existing)
        return existing

    elif operation == "transplant" and existing:
        # Target already has a learning - update it with source info
        existing.snapshot(
            operation=operation,
            change_description=change_description,
            files=[module_path],
            project_path=project_path,
        )

        # Merge with source learning info
        if source_learning:
            existing.transplanted_from = source_learning.module_path

            # Merge gotchas from source
            for gotcha in source_learning.gotchas:
                if gotcha not in existing.gotchas:
                    existing.gotchas.append(gotcha)

        # Update with new understanding
        if new_understanding.get('summary'):
            existing.summary = new_understanding['summary']
        if new_understanding.get('purpose'):
            existing.purpose = new_understanding['purpose']
        if new_understanding.get('key_functions'):
            existing.key_functions.update(new_understanding['key_functions'])

        existing.current_version += 1
        existing.learned_at = datetime.now()

        store.add_learning(existing)
        return existing

    else:
        raise ValueError(f"Unknown operation: {operation}")
