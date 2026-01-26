"""
Code references for EriRPG.

References point to code locations without storing full content.
They track file identity via hash and mtime for staleness detection,
and can hydrate (load fresh content) on demand.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import hashlib
import os

if TYPE_CHECKING:
    pass


@dataclass
class CodeRef:
    """Reference to a code location without storing full content.

    Attributes:
        path: Relative path from project root
        content_hash: SHA256 hash of file content at creation time
        mtime: File modification time at creation time
        line_start: Starting line number (1-indexed, inclusive)
        line_end: Ending line number (1-indexed, inclusive), None for whole file
    """
    path: str
    content_hash: str
    mtime: float
    line_start: int = 1
    line_end: Optional[int] = None

    def is_stale(self, project_path: str) -> bool:
        """Check if the referenced file has changed.

        Uses a two-phase check:
        1. Fast path: check mtime (if unchanged, file unchanged)
        2. Slow path: if mtime changed, verify with hash

        Args:
            project_path: Root path of the project

        Returns:
            True if file has been deleted or modified, False otherwise
        """
        full_path = os.path.join(project_path, self.path)

        if not os.path.exists(full_path):
            return True  # File deleted

        current_mtime = os.path.getmtime(full_path)
        if current_mtime == self.mtime:
            return False  # Quick path: unchanged

        # mtime changed - verify with hash
        current_hash = self._compute_hash(full_path)
        return current_hash != self.content_hash

    def hydrate(self, project_path: str) -> str:
        """Load fresh content from the referenced location.

        Args:
            project_path: Root path of the project

        Returns:
            File content (or line range if line_start/line_end specified)

        Raises:
            FileNotFoundError: If the file no longer exists
        """
        full_path = os.path.join(project_path, self.path)

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            if self.line_end is None and self.line_start == 1:
                # Whole file
                return f.read()
            else:
                # Specific line range
                lines = f.readlines()
                start_idx = self.line_start - 1  # 0-indexed
                end_idx = self.line_end if self.line_end else len(lines)
                return "".join(lines[start_idx:end_idx])

    @classmethod
    def from_file(
        cls,
        project_path: str,
        relative_path: str,
        line_start: int = 1,
        line_end: Optional[int] = None
    ) -> "CodeRef":
        """Create a CodeRef from current file state.

        Args:
            project_path: Root path of the project
            relative_path: Path relative to project root
            line_start: Starting line (1-indexed)
            line_end: Ending line (1-indexed), None for whole file

        Returns:
            CodeRef capturing current file state

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = os.path.join(project_path, relative_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")

        mtime = os.path.getmtime(full_path)
        content_hash = cls._compute_hash_static(full_path)

        return cls(
            path=relative_path,
            content_hash=content_hash,
            mtime=mtime,
            line_start=line_start,
            line_end=line_end,
        )

    def _compute_hash(self, full_path: str) -> str:
        """Compute SHA256 hash of file content."""
        return self._compute_hash_static(full_path)

    @staticmethod
    def _compute_hash_static(full_path: str) -> str:
        """Compute SHA256 hash of file content (static version)."""
        hasher = hashlib.sha256()
        with open(full_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "mtime": self.mtime,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CodeRef":
        """Deserialize from dictionary."""
        return cls(
            path=d["path"],
            content_hash=d["content_hash"],
            mtime=d["mtime"],
            line_start=d.get("line_start", 1),
            line_end=d.get("line_end"),
        )

    def __repr__(self) -> str:
        lines = f":{self.line_start}-{self.line_end}" if self.line_end else ""
        return f"CodeRef({self.path}{lines})"
