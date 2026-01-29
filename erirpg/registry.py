"""
Project registry for managing registered projects.

Stores project metadata in ~/.eri-rpg/registry.json
Each project has a name, path, language, and index status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path
import os


def detect_project_language(path: str) -> str:
    """Auto-detect project language from files in the project root.

    Checks for common language indicators:
    - Cargo.toml -> rust
    - pyproject.toml / setup.py / *.py -> python
    - mojoproject.toml / *.mojo -> mojo
    - *.c, *.h, Makefile, CMakeLists.txt -> c

    Returns:
        Language string: 'python', 'c', 'rust', 'mojo', or 'unknown'

    Note: Only languages with indexer support are returned.
    """
    path = os.path.abspath(os.path.expanduser(path))

    # Check for language-specific files
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        return "rust"

    if os.path.exists(os.path.join(path, "mojoproject.toml")):
        return "mojo"

    if os.path.exists(os.path.join(path, "pyproject.toml")) or \
       os.path.exists(os.path.join(path, "setup.py")):
        return "python"

    # Count files to determine majority language
    py_count = 0
    c_count = 0
    rs_count = 0
    mojo_count = 0

    # Fire emoji for .🔥 extension
    fire_emoji = "\U0001F525"

    for root, dirs, files in os.walk(path):
        # Skip hidden and build dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("target", "build", "node_modules", "__pycache__")]

        for f in files:
            if f.endswith(".py"):
                py_count += 1
            elif f.endswith((".c", ".h", ".cpp", ".hpp")):
                c_count += 1
            elif f.endswith(".rs"):
                rs_count += 1
            elif f.endswith(".mojo") or f.endswith(fire_emoji):
                mojo_count += 1

        # Early exit if we've sampled enough
        if py_count + c_count + rs_count + mojo_count > 10:
            break

    # Determine by majority
    counts = {"c": c_count, "rust": rs_count, "python": py_count, "mojo": mojo_count}
    max_count = max(counts.values())

    if max_count == 0:
        return "unknown"

    # Return first language with max count (priority: mojo > rust > python > c)
    for lang in ["mojo", "rust", "python", "c"]:
        if counts[lang] == max_count:
            return lang

    return "unknown"


@dataclass
class Project:
    """A registered project."""
    name: str
    path: str  # Absolute path to project root
    lang: str  # "python" | "rust" | "c" | "mojo"
    indexed_at: Optional[datetime] = None
    graph_path: str = ""  # Path to graph.json

    # Project metadata
    description: str = ""
    todos: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        if not self.graph_path:
            self.graph_path = os.path.join(self.path, ".eri-rpg", "graph.json")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "lang": self.lang,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "graph_path": self.graph_path,
            "description": self.description,
            "todos": self.todos,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        indexed_at = None
        if d.get("indexed_at"):
            indexed_at = datetime.fromisoformat(d["indexed_at"])
        return cls(
            name=d["name"],
            path=d["path"],
            lang=d["lang"],
            indexed_at=indexed_at,
            graph_path=d.get("graph_path", ""),
            description=d.get("description", ""),
            todos=d.get("todos", []),
            notes=d.get("notes", ""),
        )

    def is_indexed(self) -> bool:
        """Check if project has been indexed."""
        return self.indexed_at is not None and os.path.exists(self.graph_path)

    def index_age_days(self) -> Optional[float]:
        """Days since last index, or None if never indexed."""
        if not self.indexed_at:
            return None
        delta = datetime.now() - self.indexed_at
        return delta.total_seconds() / 86400


@dataclass
class Registry:
    """Registry of all known projects."""
    projects: Dict[str, Project] = field(default_factory=dict)
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.eri-rpg"))

    def __post_init__(self):
        self._registry_path = os.path.join(self.config_dir, "registry.json")

    def add(self, name: str, path: str, lang: str) -> Project:
        """Add a new project to the registry.

        Args:
            name: Unique project name
            path: Path to project root
            lang: Programming language

        Returns:
            The created Project

        Raises:
            ValueError: If project with name already exists
            FileNotFoundError: If path doesn't exist
        """
        if name in self.projects:
            raise ValueError(f"Project '{name}' already exists")

        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(abs_path):
            raise FileNotFoundError(f"Path does not exist: {abs_path}")

        project = Project(name=name, path=abs_path, lang=lang)
        self.projects[name] = project
        self.save()
        return project

    def remove(self, name: str) -> bool:
        """Remove a project from the registry.

        Args:
            name: Project name to remove

        Returns:
            True if removed, False if not found
        """
        if name not in self.projects:
            return False

        del self.projects[name]
        self.save()
        return True

    def get(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.projects.get(name)

    def list(self) -> List[Project]:
        """List all registered projects."""
        return list(self.projects.values())

    def save(self) -> None:
        """Save registry to disk."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        data = {
            "version": "0.55.0-alpha",
            "projects": {k: v.to_dict() for k, v in self.projects.items()},
        }

        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        """Load registry from disk."""
        if not os.path.exists(self._registry_path):
            self.projects = {}
            return

        with open(self._registry_path, "r") as f:
            data = json.load(f)

        self.projects = {
            k: Project.from_dict(v)
            for k, v in data.get("projects", {}).items()
        }

    def update_indexed(self, name: str) -> None:
        """Mark a project as indexed now."""
        if name in self.projects:
            self.projects[name].indexed_at = datetime.now()
            self.save()

    @classmethod
    def get_instance(cls) -> "Registry":
        """Get or create the global registry instance."""
        registry = cls()
        registry.load()
        return registry
