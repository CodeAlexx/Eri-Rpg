"""
Spec models for EriRPG.

Specs are first-class inputs that describe tasks, projects, and transplants.
They provide a structured way to define work and enable validation,
versioning, and reproducibility.

Spec Types:
- TaskSpec: Describes a task to perform (extract, plan, implement)
- ProjectSpec: Describes a new project to create
- TransplantSpec: Describes a feature transplant between projects
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
import json
import os
import re


# Current spec schema version
SPEC_VERSION = "1.0"


class SpecType(Enum):
    """Types of specs supported."""
    TASK = "task"
    PROJECT = "project"
    TRANSPLANT = "transplant"


class ValidationError(Exception):
    """Raised when spec validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[List[str]] = None):
        self.message = message
        self.field = field
        self.details = details or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = self.message
        if self.field:
            msg = f"{self.field}: {msg}"
        if self.details:
            msg += "\n  - " + "\n  - ".join(self.details)
        return msg


def _generate_spec_id(spec_type: str, name: str) -> str:
    """Generate a deterministic spec ID from type and name.

    Format: {type}-{slug}-{hash[:8]}
    Example: task-extract-feature-a1b2c3d4

    The ID is deterministic - same inputs always produce same output.
    """
    # Create slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:30]

    # Create short hash for uniqueness (deterministic - no timestamp)
    content = f"{spec_type}:{name}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]

    return f"{spec_type}-{slug}-{hash_val}"


def _normalize_path(path: str) -> str:
    """Normalize a path string."""
    if not path:
        return path
    # Expand user, resolve, normalize
    return str(Path(path).expanduser().resolve())


def _normalize_string(value: str) -> str:
    """Normalize a string value (trim whitespace)."""
    return value.strip() if value else ""


@dataclass
class BaseSpec:
    """Base class for all specs."""
    id: str = ""
    version: str = SPEC_VERSION
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def validate(self) -> List[str]:
        """Validate the spec. Returns list of error messages."""
        errors = []
        if not self.id:
            errors.append("id is required")
        if not self.version:
            errors.append("version is required")
        return errors

    def normalize(self) -> None:
        """Normalize fields in place."""
        self.notes = _normalize_string(self.notes)
        self.tags = [t.strip().lower() for t in self.tags if t.strip()]
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseSpec":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            version=data.get("version", SPEC_VERSION),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )

    def save(self, path: str) -> None:
        """Save spec to JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "BaseSpec":
        """Load spec from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class TaskSpec(BaseSpec):
    """Spec for a task to perform.

    Tasks describe work like extracting features, planning transplants,
    or implementing changes.
    """
    spec_type: str = "task"
    name: str = ""
    description: str = ""
    task_type: str = ""  # "extract" | "plan" | "implement" | "validate"
    source_project: str = ""
    target_project: str = ""
    query: str = ""  # For extract: what to find
    feature_file: str = ""  # Reference to extracted feature
    plan_file: str = ""  # Reference to transplant plan
    priority: str = "normal"  # "low" | "normal" | "high" | "critical"
    status: str = "pending"  # "pending" | "in_progress" | "completed" | "blocked"
    blocked_by: List[str] = field(default_factory=list)  # IDs of blocking tasks

    def validate(self) -> List[str]:
        """Validate task spec."""
        errors = super().validate()

        if not self.name:
            errors.append("name is required")

        valid_types = {"extract", "plan", "implement", "validate", ""}
        if self.task_type and self.task_type not in valid_types:
            errors.append(f"task_type must be one of: {', '.join(valid_types - {''})}")

        valid_priorities = {"low", "normal", "high", "critical"}
        if self.priority not in valid_priorities:
            errors.append(f"priority must be one of: {', '.join(valid_priorities)}")

        valid_statuses = {"pending", "in_progress", "completed", "blocked"}
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        # Type-specific validation
        if self.task_type == "extract":
            if not self.source_project:
                errors.append("source_project required for extract task")
            if not self.query:
                errors.append("query required for extract task")

        if self.task_type == "plan":
            if not self.feature_file:
                errors.append("feature_file required for plan task")
            if not self.target_project:
                errors.append("target_project required for plan task")

        return errors

    def normalize(self) -> None:
        """Normalize task spec fields."""
        super().normalize()
        self.name = _normalize_string(self.name)
        self.description = _normalize_string(self.description)
        self.query = _normalize_string(self.query)
        self.task_type = self.task_type.lower().strip()
        self.priority = self.priority.lower().strip()
        self.status = self.status.lower().strip()

        if self.feature_file:
            self.feature_file = _normalize_path(self.feature_file)
        if self.plan_file:
            self.plan_file = _normalize_path(self.plan_file)

        # Generate ID if not set
        if not self.id and self.name:
            self.id = _generate_spec_id("task", self.name)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = super().to_dict()
        data.update({
            "spec_type": self.spec_type,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "query": self.query,
            "feature_file": self.feature_file,
            "plan_file": self.plan_file,
            "priority": self.priority,
            "status": self.status,
            "blocked_by": self.blocked_by,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpec":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            version=data.get("version", SPEC_VERSION),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            task_type=data.get("task_type", ""),
            source_project=data.get("source_project", ""),
            target_project=data.get("target_project", ""),
            query=data.get("query", ""),
            feature_file=data.get("feature_file", ""),
            plan_file=data.get("plan_file", ""),
            priority=data.get("priority", "normal"),
            status=data.get("status", "pending"),
            blocked_by=data.get("blocked_by", []),
        )


@dataclass
class ProjectSpec(BaseSpec):
    """Spec for a new project to create.

    Describes the structure and initial setup for a new project.
    """
    spec_type: str = "project"
    name: str = ""
    description: str = ""
    language: str = "python"
    framework: str = ""
    core_feature: str = ""
    directories: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    output_path: str = ""

    def validate(self) -> List[str]:
        """Validate project spec."""
        errors = super().validate()

        if not self.name:
            errors.append("name is required")

        valid_languages = {"python", "rust", "c"}
        if self.language not in valid_languages:
            errors.append(f"language must be one of: {', '.join(valid_languages)}")

        if not self.core_feature:
            errors.append("core_feature is required - what does this project do?")

        return errors

    def normalize(self) -> None:
        """Normalize project spec fields."""
        super().normalize()
        self.name = _normalize_string(self.name)
        self.description = _normalize_string(self.description)
        self.core_feature = _normalize_string(self.core_feature)
        self.language = self.language.lower().strip()
        self.framework = self.framework.lower().strip()

        if self.output_path:
            self.output_path = _normalize_path(self.output_path)

        # Generate ID if not set
        if not self.id and self.name:
            self.id = _generate_spec_id("project", self.name)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = super().to_dict()
        data.update({
            "spec_type": self.spec_type,
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "framework": self.framework,
            "core_feature": self.core_feature,
            "directories": self.directories,
            "files": self.files,
            "dependencies": self.dependencies,
            "output_path": self.output_path,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectSpec":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            version=data.get("version", SPEC_VERSION),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            language=data.get("language", "python"),
            framework=data.get("framework", ""),
            core_feature=data.get("core_feature", ""),
            directories=data.get("directories", []),
            files=data.get("files", []),
            dependencies=data.get("dependencies", []),
            output_path=data.get("output_path", ""),
        )


@dataclass
class TransplantSpec(BaseSpec):
    """Spec for a feature transplant between projects.

    Describes the source feature, target project, and mapping strategy.
    """
    spec_type: str = "transplant"
    name: str = ""
    description: str = ""
    source_project: str = ""
    target_project: str = ""
    feature_name: str = ""
    feature_file: str = ""  # Path to extracted feature JSON
    components: List[str] = field(default_factory=list)
    mappings: List[Dict[str, str]] = field(default_factory=list)  # [{source, target, action}]
    wiring: List[str] = field(default_factory=list)  # Wiring tasks
    generation_order: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate transplant spec."""
        errors = super().validate()

        if not self.name:
            errors.append("name is required")

        if not self.source_project:
            errors.append("source_project is required")

        if not self.target_project:
            errors.append("target_project is required")

        if not self.feature_name and not self.feature_file:
            errors.append("feature_name or feature_file is required")

        return errors

    def normalize(self) -> None:
        """Normalize transplant spec fields."""
        super().normalize()
        self.name = _normalize_string(self.name)
        self.description = _normalize_string(self.description)
        self.feature_name = _normalize_string(self.feature_name)

        if self.feature_file:
            self.feature_file = _normalize_path(self.feature_file)

        # Generate ID if not set
        if not self.id and self.name:
            self.id = _generate_spec_id("transplant", self.name)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = super().to_dict()
        data.update({
            "spec_type": self.spec_type,
            "name": self.name,
            "description": self.description,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "feature_name": self.feature_name,
            "feature_file": self.feature_file,
            "components": self.components,
            "mappings": self.mappings,
            "wiring": self.wiring,
            "generation_order": self.generation_order,
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransplantSpec":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            version=data.get("version", SPEC_VERSION),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            source_project=data.get("source_project", ""),
            target_project=data.get("target_project", ""),
            feature_name=data.get("feature_name", ""),
            feature_file=data.get("feature_file", ""),
            components=data.get("components", []),
            mappings=data.get("mappings", []),
            wiring=data.get("wiring", []),
            generation_order=data.get("generation_order", []),
        )


# =============================================================================
# Spec Factory and Utilities
# =============================================================================

def create_spec(spec_type: str, **kwargs) -> BaseSpec:
    """Factory function to create a spec by type.

    Args:
        spec_type: One of "task", "project", "transplant"
        **kwargs: Fields for the spec

    Returns:
        The appropriate spec instance
    """
    spec_classes = {
        "task": TaskSpec,
        "project": ProjectSpec,
        "transplant": TransplantSpec,
    }

    if spec_type not in spec_classes:
        raise ValueError(f"Unknown spec type: {spec_type}. Must be one of: {', '.join(spec_classes.keys())}")

    spec = spec_classes[spec_type](**kwargs)
    spec.normalize()
    return spec


def load_spec(path: str) -> BaseSpec:
    """Load a spec from file, auto-detecting type.

    Args:
        path: Path to spec JSON file

    Returns:
        The appropriate spec instance
    """
    with open(path, "r") as f:
        data = json.load(f)

    spec_type = data.get("spec_type", "task")

    spec_classes = {
        "task": TaskSpec,
        "project": ProjectSpec,
        "transplant": TransplantSpec,
    }

    if spec_type not in spec_classes:
        raise ValueError(f"Unknown spec type in file: {spec_type}")

    return spec_classes[spec_type].from_dict(data)


def validate_spec(spec: BaseSpec) -> Tuple[bool, List[str]]:
    """Validate a spec and return result.

    Args:
        spec: The spec to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = spec.validate()
    return len(errors) == 0, errors


def get_spec_template(spec_type: str) -> Dict[str, Any]:
    """Get a template for a spec type.

    Args:
        spec_type: One of "task", "project", "transplant"

    Returns:
        Template dictionary with example values
    """
    templates = {
        "task": {
            "spec_type": "task",
            "version": SPEC_VERSION,
            "name": "My Task",
            "description": "Description of what this task does",
            "task_type": "extract",  # or "plan", "implement", "validate"
            "source_project": "source-project-name",
            "target_project": "target-project-name",
            "query": "feature name or description to find",
            "priority": "normal",
            "status": "pending",
            "tags": ["feature", "priority"],
            "notes": "Additional notes about this task",
        },
        "project": {
            "spec_type": "project",
            "version": SPEC_VERSION,
            "name": "my-project",
            "description": "A new project",
            "language": "python",
            "framework": "",
            "core_feature": "The ONE core feature this project provides",
            "directories": ["src", "tests"],
            "files": ["src/__init__.py", "src/main.py"],
            "dependencies": [],
            "output_path": "./my-project",
            "tags": ["new"],
            "notes": "",
        },
        "transplant": {
            "spec_type": "transplant",
            "version": SPEC_VERSION,
            "name": "transplant-feature-x",
            "description": "Transplant feature X from A to B",
            "source_project": "project-a",
            "target_project": "project-b",
            "feature_name": "feature-x",
            "feature_file": "",
            "components": [],
            "mappings": [],
            "wiring": [],
            "generation_order": [],
            "tags": ["transplant"],
            "notes": "",
        },
    }

    if spec_type not in templates:
        raise ValueError(f"Unknown spec type: {spec_type}")

    return templates[spec_type]


# =============================================================================
# Spec Storage
# =============================================================================

def get_specs_dir(project_path: str) -> str:
    """Get the specs directory for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Path to specs directory (.eri-rpg/specs/)
    """
    return os.path.join(project_path, ".eri-rpg", "specs")


def list_specs(project_path: str, spec_type: Optional[str] = None) -> List[str]:
    """List all specs in a project.

    Args:
        project_path: Root path of the project
        spec_type: Optional filter by type ("task", "project", "transplant")

    Returns:
        List of spec file paths
    """
    specs_dir = get_specs_dir(project_path)
    if not os.path.exists(specs_dir):
        return []

    specs = []
    for filename in os.listdir(specs_dir):
        if filename.endswith(".json"):
            path = os.path.join(specs_dir, filename)
            if spec_type:
                try:
                    spec = load_spec(path)
                    if getattr(spec, "spec_type", None) == spec_type:
                        specs.append(path)
                except Exception as e:
                    import sys; print(f"[EriRPG] {e}", file=sys.stderr)
            else:
                specs.append(path)

    return sorted(specs)


def save_spec_to_project(spec: BaseSpec, project_path: str) -> str:
    """Save a spec to the project's specs directory.

    Args:
        spec: The spec to save
        project_path: Root path of the project

    Returns:
        Path where spec was saved
    """
    specs_dir = get_specs_dir(project_path)
    os.makedirs(specs_dir, exist_ok=True)

    # Use spec ID as filename
    filename = f"{spec.id}.json"
    path = os.path.join(specs_dir, filename)

    spec.save(path)
    return path
