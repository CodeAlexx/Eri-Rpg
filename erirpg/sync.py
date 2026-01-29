"""
Knowledge synchronization for EriRPG.

Scans codebase files and synchronizes with knowledge.json:
- Detects unknown files (not in knowledge)
- Detects stale files (knowledge outdated)
- Detects deleted files (in knowledge but missing)
- Optionally auto-learns unknown/stale files

Usage:
    erirpg sync [project]           # Show sync status
    erirpg sync [project] --learn   # Auto-learn unknown/stale files
"""

import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from erirpg.refs import CodeRef
from erirpg.memory import (
    StoredLearning, KnowledgeStore,
    load_knowledge, save_knowledge, get_knowledge_path
)
from erirpg.parsers import get_parser_for_file, detect_language


# Exclude patterns (unified from indexer.py)
EXCLUDE_DIRS = {
    # Common
    ".git", ".eri-rpg", "node_modules", ".vscode", ".idea",
    # Python
    "__pycache__", "venv", ".venv", "env", "build", "dist",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    # Rust
    "target",
    # C/C++
    "cmake-build-debug", "cmake-build-release", "third_party", "vendor", "deps",
    # Mojo
    ".magic",
}

# Supported extensions by language
EXTENSIONS = {
    "python": {".py"},
    "c": {".c", ".h", ".cpp", ".hpp", ".cc", ".hh"},
    "rust": {".rs"},
    "mojo": {".mojo", "\U0001F525"},  # Fire emoji
    "dart": {".dart"},
}


@dataclass
class FileStatus:
    """Status of a single file."""
    path: str  # Relative path
    status: str  # "known", "stale", "unknown", "deleted"
    current_hash: Optional[str] = None
    stored_hash: Optional[str] = None
    learning: Optional[StoredLearning] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    project_path: str
    project_name: str

    # File counts by status
    known: List[FileStatus] = field(default_factory=list)
    stale: List[FileStatus] = field(default_factory=list)
    unknown: List[FileStatus] = field(default_factory=list)
    deleted: List[FileStatus] = field(default_factory=list)

    # Learning results (if --learn was used)
    learned: List[str] = field(default_factory=list)
    learn_errors: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.known) + len(self.stale) + len(self.unknown)

    @property
    def needs_attention(self) -> int:
        return len(self.stale) + len(self.unknown) + len(self.deleted)

    def summary(self) -> str:
        """Generate summary string."""
        lines = [
            f"{'=' * 50}",
            f" SYNC STATUS: {self.project_name}",
            f"{'=' * 50}",
            f"",
            f"  Files scanned: {self.total_files}",
            f"",
            f"  ✓ Known:   {len(self.known):4d}  (up to date)",
            f"  ⚠ Stale:   {len(self.stale):4d}  (source changed)",
            f"  ✗ Unknown: {len(self.unknown):4d}  (needs learning)",
            f"  † Deleted: {len(self.deleted):4d}  (file removed)",
        ]

        if self.learned:
            lines.append(f"")
            lines.append(f"  📚 Learned: {len(self.learned)} files")

        if self.learn_errors:
            lines.append(f"")
            lines.append(f"  ❌ Errors:  {len(self.learn_errors)} files")

        lines.append(f"")
        if self.needs_attention == 0:
            lines.append("✅ Knowledge is fully synchronized!")
        else:
            lines.append(f"⚠️  {self.needs_attention} items need attention")
            if not self.learned:
                lines.append("   Run with --learn to auto-populate knowledge")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "known": [f.path for f in self.known],
            "stale": [f.path for f in self.stale],
            "unknown": [f.path for f in self.unknown],
            "deleted": [f.path for f in self.deleted],
            "learned": self.learned,
            "learn_errors": self.learn_errors,
            "timestamp": datetime.now().isoformat(),
        }


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of file content.

    Uses the same algorithm as CodeRef._compute_hash_static.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_source_files(
    root: str,
    language: Optional[str] = None,
) -> List[str]:
    """Find all source files in a directory tree.

    Args:
        root: Root directory to scan
        language: Specific language to scan for (None = all supported)

    Returns:
        List of relative paths to source files
    """
    # Determine which extensions to look for
    if language and language in EXTENSIONS:
        target_extensions = EXTENSIONS[language]
    else:
        # All supported extensions
        target_extensions = set()
        for exts in EXTENSIONS.values():
            target_extensions.update(exts)

    source_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories (in-place modification)
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS
            and not d.endswith(".egg-info")
            and not d.startswith(".")  # Skip hidden dirs
        ]

        for filename in filenames:
            # Check extension
            ext = os.path.splitext(filename)[1]
            if ext in target_extensions:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root)
                source_files.append(rel_path)
            # Handle fire emoji extension for Mojo
            elif filename.endswith("\U0001F525"):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root)
                source_files.append(rel_path)

    return sorted(source_files)


def sync_knowledge(
    project_path: str,
    project_name: str,
    language: Optional[str] = None,
    verbose: bool = False,
) -> SyncResult:
    """Compare codebase files against knowledge.json.

    Args:
        project_path: Root path of the project
        project_name: Name of the project
        language: Specific language to scan (None = all)
        verbose: Print progress

    Returns:
        SyncResult with categorized files
    """
    result = SyncResult(
        project_path=project_path,
        project_name=project_name,
    )

    # Load existing knowledge
    store = load_knowledge(project_path, project_name)
    known_modules = set(store.list_modules())

    if verbose:
        print(f"Loaded {len(known_modules)} existing learnings")

    # Find all source files
    source_files = find_source_files(project_path, language)

    if verbose:
        print(f"Found {len(source_files)} source files")

    # Categorize each file
    seen_modules = set()

    for rel_path in source_files:
        full_path = os.path.join(project_path, rel_path)
        seen_modules.add(rel_path)

        # Compute current hash
        try:
            current_hash = compute_file_hash(full_path)
        except (IOError, OSError) as e:
            if verbose:
                print(f"  Error reading {rel_path}: {e}")
            continue

        # Check against knowledge
        learning = store.get_learning(rel_path)

        if learning is None:
            # Not in knowledge → unknown
            result.unknown.append(FileStatus(
                path=rel_path,
                status="unknown",
                current_hash=current_hash,
            ))
        elif learning.source_ref is None:
            # Has learning but no source_ref → treat as stale
            result.stale.append(FileStatus(
                path=rel_path,
                status="stale",
                current_hash=current_hash,
                learning=learning,
            ))
        elif learning.source_ref.content_hash != current_hash:
            # Hash mismatch → stale
            result.stale.append(FileStatus(
                path=rel_path,
                status="stale",
                current_hash=current_hash,
                stored_hash=learning.source_ref.content_hash,
                learning=learning,
            ))
        else:
            # Hash matches → known
            result.known.append(FileStatus(
                path=rel_path,
                status="known",
                current_hash=current_hash,
                stored_hash=learning.source_ref.content_hash,
                learning=learning,
            ))

    # Find deleted files (in knowledge but not on disk)
    for module_path in known_modules:
        if module_path not in seen_modules:
            full_path = os.path.join(project_path, module_path)
            if not os.path.exists(full_path):
                result.deleted.append(FileStatus(
                    path=module_path,
                    status="deleted",
                    learning=store.get_learning(module_path),
                ))

    return result


def learn_file(
    project_path: str,
    rel_path: str,
    store: KnowledgeStore,
) -> Tuple[bool, str]:
    """Parse a file and create/update its StoredLearning.

    Args:
        project_path: Root path of the project
        rel_path: Relative path to the file
        store: KnowledgeStore to update

    Returns:
        Tuple of (success, error_message)
    """
    full_path = os.path.join(project_path, rel_path)

    # Get appropriate parser
    parser = get_parser_for_file(full_path)
    if parser is None:
        return False, f"No parser for file type: {rel_path}"

    # Parse the file
    try:
        parsed = parser(full_path)
    except Exception as e:
        return False, f"Parse error: {e}"

    # Check for parse errors
    if "error" in parsed:
        return False, f"Parse error: {parsed['error']}"

    # Create CodeRef for staleness tracking
    try:
        source_ref = CodeRef.from_file(project_path, rel_path)
    except FileNotFoundError:
        return False, f"File not found: {rel_path}"

    # Extract information from parsed result
    docstring = parsed.get("docstring", "")
    interfaces = parsed.get("interfaces", [])

    # Build summary from docstring or infer from content
    if docstring:
        summary = docstring
    elif interfaces:
        # Infer from interfaces
        types = [i["type"] for i in interfaces]
        if "class" in types:
            class_names = [i["name"] for i in interfaces if i["type"] == "class"]
            summary = f"Defines {', '.join(class_names[:3])}"
            if len(class_names) > 3:
                summary += f" and {len(class_names) - 3} more"
        elif "function" in types or "async_function" in types:
            func_names = [i["name"] for i in interfaces
                         if i["type"] in ("function", "async_function")]
            summary = f"Contains {', '.join(func_names[:3])}"
            if len(func_names) > 3:
                summary += f" and {len(func_names) - 3} more"
        else:
            summary = f"Contains {len(interfaces)} interface(s)"
    else:
        summary = f"Source file ({parsed.get('lines', 0)} lines)"

    # Build key_functions from interfaces
    key_functions = {}
    for iface in interfaces[:10]:  # Limit to first 10
        name = iface.get("name", "")
        iface_type = iface.get("type", "")
        iface_doc = iface.get("docstring", "")

        if iface_type == "class":
            methods = iface.get("methods", [])
            key_functions[name] = iface_doc or f"Class with {len(methods)} methods"
        elif iface_type in ("function", "async_function"):
            sig = iface.get("signature", "")
            key_functions[name] = iface_doc or sig or f"{iface_type}"
        elif iface_type == "const":
            key_functions[name] = "Module constant"

    # Detect language for purpose
    lang = detect_language(full_path)
    purpose = f"{lang.capitalize()} module"

    # Check if we're updating an existing learning
    existing = store.get_learning(rel_path)

    if existing:
        # Update existing learning
        existing.summary = summary
        existing.source_ref = source_ref
        existing.learned_at = datetime.now()
        # Merge key_functions (keep existing, add new)
        for name, desc in key_functions.items():
            if name not in existing.key_functions:
                existing.key_functions[name] = desc
        store.add_learning(existing)
    else:
        # Create new learning
        learning = StoredLearning(
            module_path=rel_path,
            learned_at=datetime.now(),
            summary=summary,
            purpose=purpose,
            key_functions=key_functions,
            source_ref=source_ref,
            confidence=0.7,  # Parser-generated, lower confidence
        )
        store.add_learning(learning)

    return True, ""


def sync_and_learn(
    project_path: str,
    project_name: str,
    language: Optional[str] = None,
    verbose: bool = False,
    update_preflight: bool = True,
) -> SyncResult:
    """Sync knowledge and auto-learn unknown/stale files.

    Args:
        project_path: Root path of the project
        project_name: Name of the project
        language: Specific language to scan (None = all)
        verbose: Print progress
        update_preflight: Update preflight_state.json with learnings_status

    Returns:
        SyncResult with learning results included
    """
    # First, get sync status
    result = sync_knowledge(project_path, project_name, language, verbose)

    # Load knowledge store for updates
    store = load_knowledge(project_path, project_name)

    # Learn unknown files
    for status in result.unknown:
        if verbose:
            print(f"  Learning: {status.path}")

        success, error = learn_file(project_path, status.path, store)

        if success:
            result.learned.append(status.path)
        else:
            result.learn_errors.append((status.path, error))
            if verbose:
                print(f"    Error: {error}")

    # Re-learn stale files
    for status in result.stale:
        if verbose:
            print(f"  Re-learning: {status.path}")

        success, error = learn_file(project_path, status.path, store)

        if success:
            result.learned.append(status.path)
        else:
            result.learn_errors.append((status.path, error))
            if verbose:
                print(f"    Error: {error}")

    # Save updated knowledge
    save_knowledge(project_path, store)

    if verbose:
        print(f"Saved {len(result.learned)} learnings to knowledge.json")

    # Update preflight_state with learnings_status
    if update_preflight:
        _update_preflight_learnings_status(project_path, store)

    return result


def _update_preflight_learnings_status(
    project_path: str,
    store: KnowledgeStore,
) -> None:
    """Update preflight_state.json with learnings_status for instant lookup.

    This allows preflight checks to be instant lookups instead of
    computing staleness for each file.
    """
    import json

    # Build learnings_status map
    learnings_status = {}

    for module_path, learning in store.learnings.items():
        full_path = os.path.join(project_path, module_path)

        if not os.path.exists(full_path):
            learnings_status[module_path] = "deleted"
        elif learning.is_stale(project_path):
            learnings_status[module_path] = "stale"
        else:
            learnings_status[module_path] = "known"

    # Ensure .eri-rpg directory exists
    eri_dir = Path(project_path) / ".eri-rpg"
    eri_dir.mkdir(parents=True, exist_ok=True)

    # Read existing preflight state or create new
    preflight_file = eri_dir / "preflight_state.json"

    if preflight_file.exists():
        with open(preflight_file, "r") as f:
            state = json.load(f)
    else:
        state = {}

    # Update learnings_status
    state["learnings_status"] = learnings_status
    state["learnings_synced_at"] = datetime.now().isoformat()

    # Write back
    with open(preflight_file, "w") as f:
        json.dump(state, f, indent=2)


def get_learnings_status(project_path: str) -> Dict[str, str]:
    """Get cached learnings_status from preflight_state.json.

    Returns empty dict if not available (sync not run yet).
    """
    import json

    preflight_file = Path(project_path) / ".eri-rpg" / "preflight_state.json"

    if not preflight_file.exists():
        return {}

    try:
        with open(preflight_file, "r") as f:
            state = json.load(f)
        return state.get("learnings_status", {})
    except (json.JSONDecodeError, IOError):
        return {}
