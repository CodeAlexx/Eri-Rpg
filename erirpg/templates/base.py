"""
Base template class for project scaffolding.

Templates define the structure and initial files for different
project types/stacks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from erirpg.specs import ProjectSpec


@dataclass
class ScaffoldFile:
    """A file to be created during scaffolding.

    Attributes:
        path: Relative path from project root (e.g., "app/main.py")
        content: File content to write
        phase: Plan phase this belongs to (e.g., "001")
        executable: Whether to make file executable
        description: Human-readable description of file purpose
    """
    path: str
    content: str
    phase: str = "001"
    executable: bool = False
    description: str = ""

    def full_path(self, project_root: str) -> str:
        """Get full path for this file.

        Args:
            project_root: Root directory of project

        Returns:
            Absolute path to file
        """
        import os
        return os.path.join(project_root, self.path)


class BaseTemplate(ABC):
    """Abstract base class for project templates.

    Templates provide the blueprint for scaffolding new projects.
    Each template knows how to generate:
    - Directory structure
    - Initial files with content
    - Configuration files
    - Test stubs
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Template name (e.g., "fastapi-only")."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    @abstractmethod
    def languages(self) -> List[str]:
        """Supported programming languages."""
        ...

    @property
    def default_framework(self) -> str:
        """Default framework for this template."""
        return ""

    @abstractmethod
    def get_directories(self, spec: "ProjectSpec") -> List[str]:
        """Get list of directories to create.

        Args:
            spec: ProjectSpec with project details

        Returns:
            List of relative directory paths
        """
        ...

    @abstractmethod
    def get_files(self, spec: "ProjectSpec") -> List[ScaffoldFile]:
        """Get list of files to create.

        Args:
            spec: ProjectSpec with project details

        Returns:
            List of ScaffoldFile objects
        """
        ...

    def get_dependencies(self, spec: "ProjectSpec") -> List[str]:
        """Get list of dependencies to add.

        Args:
            spec: ProjectSpec with project details

        Returns:
            List of package names
        """
        return []

    def get_dev_dependencies(self, spec: "ProjectSpec") -> List[str]:
        """Get list of dev dependencies to add.

        Args:
            spec: ProjectSpec with project details

        Returns:
            List of dev package names
        """
        return []

    def validate_spec(self, spec: "ProjectSpec") -> List[str]:
        """Validate that spec is compatible with this template.

        Args:
            spec: ProjectSpec to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if spec.language not in self.languages:
            errors.append(
                f"Template '{self.name}' supports {self.languages}, "
                f"not '{spec.language}'"
            )

        return errors

    def _slugify(self, name: str) -> str:
        """Convert name to valid Python/file identifier.

        Args:
            name: Project name

        Returns:
            Slugified name
        """
        import re
        # Replace hyphens and spaces with underscores
        slug = re.sub(r'[-\s]+', '_', name.lower())
        # Remove non-alphanumeric chars except underscore
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        # Ensure doesn't start with number
        if slug and slug[0].isdigit():
            slug = '_' + slug
        return slug or 'project'

    def _format_description(self, spec: "ProjectSpec") -> str:
        """Format description for inclusion in files.

        Args:
            spec: ProjectSpec with description

        Returns:
            Formatted description string
        """
        desc = spec.description or spec.core_feature or f"{spec.name} project"
        return desc.strip()
