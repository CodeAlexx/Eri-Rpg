"""
Caching system for EriRPG.

Provides file-based caching for parsed files and incremental indexing
to improve performance on repeated runs.

Usage:
    cache = IndexCache(project_path)
    if cache.is_stale(file_path):
        result = parse_file(file_path)
        cache.store(file_path, result)
    else:
        result = cache.get(file_path)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import json
import os


@dataclass
class CacheEntry:
    """A cached parsing result for a single file."""
    path: str
    mtime: float
    size: int
    content_hash: str
    parse_result: Dict[str, Any]
    cached_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": self.path,
            "mtime": self.mtime,
            "size": self.size,
            "content_hash": self.content_hash,
            "parse_result": self.parse_result,
            "cached_at": self.cached_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            mtime=data["mtime"],
            size=data["size"],
            content_hash=data["content_hash"],
            parse_result=data["parse_result"],
            cached_at=datetime.fromisoformat(data["cached_at"]) if "cached_at" in data else datetime.now(),
        )


@dataclass
class CacheStats:
    """Statistics about cache usage."""
    hits: int = 0
    misses: int = 0
    total_files: int = 0
    cached_files: int = 0
    stale_files: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def format_summary(self) -> str:
        """Format stats as readable summary."""
        return (
            f"Cache Stats:\n"
            f"  Total files: {self.total_files}\n"
            f"  Cached: {self.cached_files}\n"
            f"  Stale: {self.stale_files}\n"
            f"  Hits: {self.hits}\n"
            f"  Misses: {self.misses}\n"
            f"  Hit rate: {self.hit_rate:.1%}"
        )


class IndexCache:
    """Cache for parsed file results to enable incremental indexing."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.cache_dir = os.path.join(project_path, ".eri-rpg", "cache")
        self.cache_file = os.path.join(self.cache_dir, "parse_cache.json")
        self._entries: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._load()

    def _load(self) -> None:
        """Load cache from disk."""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)

            for entry_data in data.get("entries", []):
                entry = CacheEntry.from_dict(entry_data)
                self._entries[entry.path] = entry

            self._stats.cached_files = len(self._entries)

        except (json.JSONDecodeError, KeyError, TypeError):
            # Invalid cache, start fresh
            self._entries = {}

    def save(self) -> None:
        """Save cache to disk."""
        os.makedirs(self.cache_dir, exist_ok=True)

        data = {
            "version": 1,
            "entries": [e.to_dict() for e in self._entries.values()],
            "saved_at": datetime.now().isoformat(),
        }

        with open(self.cache_file, "w") as f:
            json.dump(data, f)

    def _get_file_info(self, file_path: str) -> tuple:
        """Get mtime, size, and hash for a file."""
        stat = os.stat(file_path)
        mtime = stat.st_mtime
        size = stat.st_size

        # Only compute hash if file is reasonably small
        if size < 1024 * 1024:  # 1MB
            with open(file_path, "rb") as f:
                content_hash = hashlib.md5(f.read()).hexdigest()
        else:
            # For large files, use mtime+size as proxy
            content_hash = f"{mtime}:{size}"

        return mtime, size, content_hash

    def is_stale(self, file_path: str) -> bool:
        """Check if a file's cache entry is stale.

        Args:
            file_path: Absolute or relative path to file

        Returns:
            True if file needs to be re-parsed
        """
        rel_path = self._normalize_path(file_path)
        self._stats.total_files += 1

        if rel_path not in self._entries:
            self._stats.misses += 1
            return True

        entry = self._entries[rel_path]
        full_path = os.path.join(self.project_path, rel_path)

        if not os.path.exists(full_path):
            # File was deleted
            del self._entries[rel_path]
            self._stats.stale_files += 1
            self._stats.misses += 1
            return True

        # Quick check: mtime
        try:
            current_mtime = os.path.getmtime(full_path)
            if current_mtime == entry.mtime:
                self._stats.hits += 1
                return False
        except OSError:
            self._stats.misses += 1
            return True

        # mtime changed - verify with size and optionally hash
        try:
            current_size = os.path.getsize(full_path)
            if current_size != entry.size:
                self._stats.stale_files += 1
                self._stats.misses += 1
                return True

            # Size same, check hash if available
            _, _, current_hash = self._get_file_info(full_path)
            if current_hash != entry.content_hash:
                self._stats.stale_files += 1
                self._stats.misses += 1
                return True

            # Content unchanged despite mtime change - update mtime in cache
            entry.mtime = current_mtime
            self._stats.hits += 1
            return False

        except OSError:
            self._stats.misses += 1
            return True

    def get(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached parse result for a file.

        Args:
            file_path: Path to file

        Returns:
            Parse result dict or None if not cached
        """
        rel_path = self._normalize_path(file_path)

        if rel_path not in self._entries:
            return None

        return self._entries[rel_path].parse_result

    def store(self, file_path: str, parse_result: Dict[str, Any]) -> None:
        """Store parse result in cache.

        Args:
            file_path: Path to file
            parse_result: Parsed file data
        """
        rel_path = self._normalize_path(file_path)
        full_path = os.path.join(self.project_path, rel_path)

        try:
            mtime, size, content_hash = self._get_file_info(full_path)
        except OSError:
            return  # Can't cache if we can't read file info

        self._entries[rel_path] = CacheEntry(
            path=rel_path,
            mtime=mtime,
            size=size,
            content_hash=content_hash,
            parse_result=parse_result,
        )

    def invalidate(self, file_path: str) -> None:
        """Invalidate cache for a specific file.

        Args:
            file_path: Path to file
        """
        rel_path = self._normalize_path(file_path)
        if rel_path in self._entries:
            del self._entries[rel_path]

    def invalidate_all(self) -> None:
        """Clear all cache entries."""
        self._entries = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def _normalize_path(self, file_path: str) -> str:
        """Convert path to relative form for cache key."""
        if os.path.isabs(file_path):
            return os.path.relpath(file_path, self.project_path)
        return file_path

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def cleanup_deleted_files(self, existing_files: List[str]) -> int:
        """Remove cache entries for files that no longer exist.

        Args:
            existing_files: List of currently existing file paths

        Returns:
            Number of entries removed
        """
        existing_set = {self._normalize_path(f) for f in existing_files}
        to_remove = [p for p in self._entries if p not in existing_set]

        for path in to_remove:
            del self._entries[path]

        return len(to_remove)


# =============================================================================
# Helper Functions
# =============================================================================

def get_index_cache(project_path: str) -> IndexCache:
    """Get or create an IndexCache for a project.

    Args:
        project_path: Path to the project

    Returns:
        IndexCache instance
    """
    return IndexCache(project_path)


def clear_cache(project_path: str) -> bool:
    """Clear all caches for a project.

    Args:
        project_path: Path to the project

    Returns:
        True if cache was cleared
    """
    cache = IndexCache(project_path)
    cache.invalidate_all()
    return True


def get_cache_stats(project_path: str) -> Optional[CacheStats]:
    """Get cache statistics for a project.

    Args:
        project_path: Path to the project

    Returns:
        CacheStats or None if no cache exists
    """
    cache = IndexCache(project_path)
    return cache.get_stats()
