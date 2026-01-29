"""
Project Scaffolding System.

Creates project structure and initial files based on templates
and project specifications.

Usage:
    from erirpg.scaffold import scaffold_project, get_available_stacks

    stacks = get_available_stacks()
    result = scaffold_project(plan, spec, output_path, stack="fastapi-only")
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from erirpg.planner import Plan
    from erirpg.specs import ProjectSpec
    from erirpg.templates.base import ScaffoldFile


@dataclass
class ScaffoldResult:
    """Result of a scaffolding operation.

    Attributes:
        success: Whether scaffolding completed successfully
        project_path: Path to the created project
        files_created: List of files that were created
        files_skipped: List of files that already existed
        directories_created: List of directories created
        errors: List of error messages
    """
    success: bool
    project_path: str = ""
    files_created: List[Path] = field(default_factory=list)
    files_skipped: List[Path] = field(default_factory=list)
    directories_created: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def format(self) -> str:
        """Format result for display."""
        lines = []

        if self.success:
            lines.append(f"Project created at: {self.project_path}")
            lines.append("")

        if self.directories_created:
            lines.append(f"Directories ({len(self.directories_created)}):")
            for d in sorted(self.directories_created)[:10]:
                lines.append(f"  + {d}")
            if len(self.directories_created) > 10:
                lines.append(f"  ... and {len(self.directories_created) - 10} more")

        if self.files_created:
            lines.append(f"\nFiles ({len(self.files_created)}):")
            for f in sorted(self.files_created)[:15]:
                lines.append(f"  + {f}")
            if len(self.files_created) > 15:
                lines.append(f"  ... and {len(self.files_created) - 15} more")

        if self.files_skipped:
            lines.append(f"\nSkipped ({len(self.files_skipped)}):")
            for f in self.files_skipped[:5]:
                lines.append(f"  - {f} (exists)")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  ! {e}")

        if not self.success:
            lines.append("\nScaffolding failed.")
        else:
            lines.append("\nScaffolding complete.")

        return "\n".join(lines)


def get_available_stacks() -> Dict[str, str]:
    """Get available stack templates with descriptions.

    Returns:
        Dict mapping stack names to descriptions
    """
    from erirpg.templates import get_available_templates
    return get_available_templates()


def detect_stack(spec: "ProjectSpec") -> Optional[str]:
    """Detect appropriate stack from project spec.

    Args:
        spec: ProjectSpec with framework hints

    Returns:
        Stack name or None if no match
    """
    from erirpg.templates import detect_template_from_spec
    return detect_template_from_spec(spec)


def scaffold_project(
    plan: Optional["Plan"],
    spec: "ProjectSpec",
    output_path: str,
    stack: Optional[str] = None,
    overwrite: bool = False,
) -> ScaffoldResult:
    """Scaffold a new project from a spec and template.

    Creates directory structure and initial files based on the
    chosen stack template.

    Args:
        plan: Optional Plan (used for phase assignment)
        spec: ProjectSpec with project details
        output_path: Where to create the project
        stack: Stack template name (auto-detected if None)
        overwrite: Whether to overwrite existing files

    Returns:
        ScaffoldResult with created files and any errors
    """
    from erirpg.templates import get_template

    result = ScaffoldResult(success=False, project_path=output_path)

    # Determine stack
    if stack is None:
        stack = detect_stack(spec)

    if stack is None:
        # Default to cli-python if no stack specified or detected
        stack = "cli-python"

    # Get template
    template = get_template(stack)
    if template is None:
        result.errors.append(f"Unknown stack template: {stack}")
        return result

    # Validate template compatibility
    errors = template.validate_spec(spec)
    if errors:
        result.errors.extend(errors)
        return result

    # Create output directory
    output_path = os.path.abspath(os.path.expanduser(output_path))
    result.project_path = output_path

    try:
        os.makedirs(output_path, exist_ok=True)
    except OSError as e:
        result.errors.append(f"Failed to create project directory: {e}")
        return result

    # Create directories
    directories = template.get_directories(spec)
    for dir_path in directories:
        full_path = os.path.join(output_path, dir_path)
        try:
            os.makedirs(full_path, exist_ok=True)
            result.directories_created.append(Path(dir_path))
        except OSError as e:
            result.errors.append(f"Failed to create directory {dir_path}: {e}")

    # Create files
    files = template.get_files(spec)
    for scaffold_file in files:
        full_path = os.path.join(output_path, scaffold_file.path)

        # Check if file exists
        if os.path.exists(full_path) and not overwrite:
            result.files_skipped.append(Path(scaffold_file.path))
            continue

        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write file
            with open(full_path, 'w') as f:
                f.write(scaffold_file.content)

            # Make executable if needed
            if scaffold_file.executable:
                os.chmod(full_path, os.stat(full_path).st_mode | 0o111)

            result.files_created.append(Path(scaffold_file.path))

        except OSError as e:
            result.errors.append(f"Failed to create file {scaffold_file.path}: {e}")

    # Success if no critical errors
    result.success = len(result.errors) == 0

    return result


def create_eri_rpg_structure(project_path: str) -> List[Path]:
    """Create .eri-rpg directory structure.

    Args:
        project_path: Path to project root

    Returns:
        List of created paths
    """
    eri_path = Path(project_path) / ".eri-rpg"
    created = []

    # Create directories
    dirs = [
        eri_path,
        eri_path / "specs",
        eri_path / "plans",
        eri_path / "runs",
        eri_path / "sessions",
    ]

    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

    return created


def auto_learn_scaffolds(project_path: str, spec: "ProjectSpec") -> Dict[str, str]:
    """Generate initial learnings for scaffolded files.

    Creates basic learnings for the main files so Claude
    has context when working on the project.

    Args:
        project_path: Path to project root
        spec: ProjectSpec with project details

    Returns:
        Dict mapping file paths to learning summaries
    """
    from erirpg.templates import get_template, detect_template_from_spec

    learnings = {}

    # Detect stack
    stack = detect_template_from_spec(spec)
    if not stack:
        return learnings

    template = get_template(stack)
    if not template:
        return learnings

    # Generate learnings for each file
    files = template.get_files(spec)
    for f in files:
        if f.description:
            learnings[f.path] = f.description

    return learnings
