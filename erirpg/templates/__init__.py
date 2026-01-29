"""
EriRPG Templates - Stack templates for project scaffolding.

Provides templates for generating project structures based on
detected or specified technology stacks.

Available Templates:
- fastapi-only: FastAPI backend with standard Python structure
- cli-python: Python CLI application with Click

Usage:
    from erirpg.templates import TEMPLATES, get_template

    template = get_template("fastapi-only")
    files = template.get_files(spec)
"""

from typing import Dict, Optional

from erirpg.templates.base import BaseTemplate, ScaffoldFile
from erirpg.templates.fastapi_only import FastAPIOnlyTemplate
from erirpg.templates.cli_python import CLIPythonTemplate


# Template registry
TEMPLATES: Dict[str, BaseTemplate] = {
    "fastapi-only": FastAPIOnlyTemplate(),
    "cli-python": CLIPythonTemplate(),
}


def get_template(name: str) -> Optional[BaseTemplate]:
    """Get a template by name.

    Args:
        name: Template name (e.g., "fastapi-only")

    Returns:
        Template instance or None if not found
    """
    return TEMPLATES.get(name)


def get_available_templates() -> Dict[str, str]:
    """Get dictionary of available templates with descriptions.

    Returns:
        Dict mapping template names to descriptions
    """
    return {name: t.description for name, t in TEMPLATES.items()}


def detect_template_from_spec(spec) -> Optional[str]:
    """Detect best template based on project spec.

    Args:
        spec: ProjectSpec with framework hints

    Returns:
        Template name or None if no match
    """
    framework = getattr(spec, "framework", "").lower()
    core_feature = getattr(spec, "core_feature", "").lower()

    # Check framework hints
    if "fastapi" in framework or "api" in framework:
        return "fastapi-only"
    if "cli" in framework or "command" in framework:
        return "cli-python"

    # Check core feature hints
    if "api" in core_feature or "rest" in core_feature or "endpoint" in core_feature:
        return "fastapi-only"
    if "cli" in core_feature or "command" in core_feature or "terminal" in core_feature:
        return "cli-python"

    return None


__all__ = [
    "TEMPLATES",
    "BaseTemplate",
    "ScaffoldFile",
    "get_template",
    "get_available_templates",
    "detect_template_from_spec",
]
