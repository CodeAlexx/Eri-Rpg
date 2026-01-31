"""
Documentation generation for coder workflow.

Commands:
- handoff: Generate handoff documentation
- template: Save/load file templates
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import get_planning_dir, load_state, load_roadmap, load_config, ensure_planning_dir, timestamp
from .knowledge import load_knowledge, export_knowledge
from .metrics import get_metrics_summary


def generate_handoff(
    audience: str = "human",
    phase: Optional[int] = None,
    brief: bool = False,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate handoff documentation.

    Args:
        audience: "human" or "ai"
        phase: Optional specific phase
        brief: Generate brief summary only
        project_path: Project path

    Returns:
        Dict with generated content and paths
    """
    planning_dir = get_planning_dir(project_path)

    # Gather context
    context = _gather_handoff_context(project_path)

    if audience == "ai":
        content = _generate_ai_handoff(context, phase, brief)
        filename = "HANDOFF-AI.md"
    else:
        content = _generate_human_handoff(context, phase, brief)
        filename = "HANDOFF.md"

    # Save to file
    output_path = planning_dir / filename
    output_path.write_text(content)

    return {
        "path": str(output_path),
        "audience": audience,
        "brief": brief,
        "content_length": len(content),
    }


def _gather_handoff_context(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Gather all context for handoff generation."""
    planning_dir = get_planning_dir(project_path)
    cwd = project_path or Path.cwd()

    context = {
        "project_name": cwd.name,
        "timestamp": timestamp(),
        "state": load_state(project_path),
        "roadmap": load_roadmap(project_path),
        "config": load_config(project_path),
        "knowledge": load_knowledge(project_path),
        "metrics": get_metrics_summary(project_path),
    }

    # Load PROJECT.md if exists
    project_md = planning_dir / "PROJECT.md"
    if project_md.exists():
        context["project_md"] = project_md.read_text()

    # Load REQUIREMENTS.md if exists
    req_md = planning_dir / "REQUIREMENTS.md"
    if req_md.exists():
        context["requirements_md"] = req_md.read_text()

    # Analyze codebase structure
    context["codebase"] = _analyze_codebase_structure(cwd)

    return context


def _analyze_codebase_structure(project_path: Path) -> Dict[str, Any]:
    """Analyze codebase structure for handoff."""
    structure = {
        "directories": [],
        "key_files": [],
        "tech_stack": [],
    }

    # Find important directories
    important_dirs = ["src", "lib", "app", "components", "api", "tests", "docs"]
    for d in important_dirs:
        dir_path = project_path / d
        if dir_path.exists():
            structure["directories"].append(d)

    # Find key files
    key_patterns = [
        "package.json", "pyproject.toml", "Cargo.toml",
        "README.md", "Dockerfile", "docker-compose.yml",
        ".env.example", "tsconfig.json", "vite.config.*",
    ]
    for pattern in key_patterns:
        matches = list(project_path.glob(pattern))
        for m in matches[:3]:  # Limit
            structure["key_files"].append(m.name)

    # Detect tech stack
    if (project_path / "package.json").exists():
        try:
            pkg = json.loads((project_path / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                structure["tech_stack"].append("Next.js")
            if "react" in deps:
                structure["tech_stack"].append("React")
            if "vue" in deps:
                structure["tech_stack"].append("Vue")
            if "typescript" in deps:
                structure["tech_stack"].append("TypeScript")
            if "prisma" in deps:
                structure["tech_stack"].append("Prisma")
        except:
            pass

    if (project_path / "pyproject.toml").exists():
        structure["tech_stack"].append("Python")

    if (project_path / "Cargo.toml").exists():
        structure["tech_stack"].append("Rust")

    return structure


def _generate_human_handoff(
    context: Dict[str, Any],
    phase: Optional[int],
    brief: bool,
) -> str:
    """Generate human-readable handoff document."""
    output = f"# Project Handoff: {context['project_name']}\n\n"
    output += f"**Generated:** {context['timestamp']}\n"
    output += "**Author:** Claude (eri-coder)\n"
    output += "**Audience:** Human developers\n\n"
    output += "---\n\n"

    if brief:
        # Brief summary
        output += "## Executive Summary\n\n"
        roadmap = context.get("roadmap", {})
        phases = roadmap.get("phases", [])
        completed = sum(1 for p in phases if p.get("status") == "complete")
        total = len(phases)
        percent = int(completed / total * 100) if total else 0

        output += f"**Progress:** {completed}/{total} phases complete ({percent}%)\n\n"

        state = context.get("state", {})
        if state.get("current_focus"):
            output += f"**Current Focus:** {state['current_focus']}\n\n"

        output += "**Next Action:** "
        if completed < total:
            output += f"`/coder:execute-phase {completed + 1}`\n"
        else:
            output += "`/coder:complete-milestone`\n"

        return output

    # Full handoff
    output += "## Executive Summary\n\n"

    # Project overview
    if context.get("project_md"):
        # Extract first section
        lines = context["project_md"].split("\n")[:20]
        output += "\n".join(lines) + "\n\n"

    # Tech stack
    codebase = context.get("codebase", {})
    if codebase.get("tech_stack"):
        output += "### Tech Stack\n\n"
        output += "| Technology | Purpose |\n"
        output += "|------------|----------|\n"
        for tech in codebase["tech_stack"]:
            output += f"| {tech} | - |\n"
        output += "\n"

    # Current state
    output += "---\n\n## Current State\n\n"
    roadmap = context.get("roadmap", {})
    phases = roadmap.get("phases", [])
    completed = sum(1 for p in phases if p.get("status") == "complete")
    total = len(phases)

    output += f"### Progress\n\n"
    output += f"Phase {completed} of {total} complete\n\n"

    output += "### What's Done\n\n"
    for p in phases:
        if p.get("status") == "complete":
            output += f"- ✅ Phase {p.get('number')}: {p.get('name')}\n"

    output += "\n### What's Pending\n\n"
    for p in phases:
        if p.get("status") != "complete":
            output += f"- ⏳ Phase {p.get('number')}: {p.get('name')}\n"

    # Key decisions
    knowledge = context.get("knowledge", {})
    if knowledge.get("decisions"):
        output += "\n---\n\n## Key Decisions\n\n"
        for d in knowledge["decisions"][:5]:
            output += f"### {d.get('title', 'Decision')}\n\n"
            output += f"**Chose:** {d.get('choice')}\n\n"
            output += f"**Why:** {d.get('rationale')}\n\n"

    # Getting started
    output += "---\n\n## Getting Started\n\n"
    output += "### Prerequisites\n\n"
    if "Node.js" in str(codebase.get("tech_stack", [])) or "Next.js" in str(codebase.get("tech_stack", [])):
        output += "- Node.js 18+\n"
        output += "- npm/pnpm\n"
    if "Python" in str(codebase.get("tech_stack", [])):
        output += "- Python 3.10+\n"

    output += "\n### Setup\n\n```bash\n"
    output += "# Clone and install\n"
    output += f"cd {context['project_name']}\n"
    if "Node.js" in str(codebase.get("tech_stack", [])):
        output += "npm install  # or pnpm install\n"
    if "Python" in str(codebase.get("tech_stack", [])):
        output += "pip install -e .\n"
    output += "```\n"

    return output


def _generate_ai_handoff(
    context: Dict[str, Any],
    phase: Optional[int],
    brief: bool,
) -> str:
    """Generate AI-optimized handoff document."""
    output = f"# AI Handoff: {context['project_name']}\n\n"
    output += "**Context Type:** eri-coder project handoff\n"
    output += f"**Generated:** {context['timestamp']}\n"
    output += "**Source Session:** Continue with /coder:resume\n\n"
    output += "---\n\n"

    # Project context
    output += "## Project Context\n\n"
    output += "```yaml\n"
    output += f"name: {context['project_name']}\n"
    codebase = context.get("codebase", {})
    if codebase.get("tech_stack"):
        output += f"stack: {codebase['tech_stack']}\n"
    output += "```\n\n"

    # Planning location
    output += "### Planning Location\n\n```\n"
    output += ".planning/\n"
    output += "├── PROJECT.md\n"
    output += "├── ROADMAP.md\n"
    output += "├── STATE.md\n"
    output += "├── REQUIREMENTS.md\n"
    output += "└── phases/\n```\n\n"

    # Current position
    output += "---\n\n## Current Position\n\n"
    roadmap = context.get("roadmap", {})
    phases = roadmap.get("phases", [])
    completed = sum(1 for p in phases if p.get("status") == "complete")
    total = len(phases)
    current = completed + 1 if completed < total else total

    output += "```yaml\n"
    output += f"phase: {current}\n"
    if current <= len(phases):
        output += f"phase_name: {phases[current-1].get('name', 'Unknown')}\n"
    output += f"total_phases: {total}\n"
    output += f"completion: {int(completed/total*100) if total else 0}%\n"
    output += "```\n\n"

    # Resume command
    output += "### Resume Command\n\n"
    if completed < total:
        output += f"```\n/coder:execute-phase {current}\n```\n\n"
    else:
        output += "```\n/coder:complete-milestone\n```\n\n"

    # Constraints
    output += "---\n\n## Constraints\n\n"
    output += "### Must Follow\n\n"
    output += "1. Use existing patterns from codebase\n"
    output += "2. Follow project conventions\n"
    output += "3. Maintain existing file structure\n\n"

    # Context to load
    output += "---\n\n## Context to Load\n\n```\n"
    output += "@.planning/PROJECT.md\n"
    output += "@.planning/ROADMAP.md\n"
    output += "@.planning/STATE.md\n"
    output += "```\n"

    return output


# Template management

def get_templates_dir(project_path: Optional[Path] = None) -> Path:
    """Get templates directory."""
    return get_planning_dir(project_path) / "templates"


def save_template(
    name: str,
    content: str,
    description: Optional[str] = None,
    variables: Optional[List[str]] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Save a file as a template.

    Args:
        name: Template name (e.g., "api-route")
        content: Template content with {{variable}} placeholders
        description: Template description
        variables: List of variable names used in template
        project_path: Project path

    Returns:
        Dict with template info
    """
    templates_dir = get_templates_dir(project_path)
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect variables
    import re
    detected_vars = set(re.findall(r'\{\{(\w+)\}\}', content))
    all_vars = list(detected_vars | set(variables or []))

    # Save template
    template_path = templates_dir / f"{name}.template"
    template_path.write_text(content)

    # Save metadata
    metadata = {
        "name": name,
        "description": description,
        "variables": all_vars,
        "created_at": timestamp(),
    }

    meta_path = templates_dir / f"{name}.meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    return {
        "path": str(template_path),
        "name": name,
        "variables": all_vars,
    }


def load_template(
    name: str,
    project_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Load a template by name."""
    templates_dir = get_templates_dir(project_path)
    template_path = templates_dir / f"{name}.template"
    meta_path = templates_dir / f"{name}.meta.json"

    if not template_path.exists():
        return None

    result = {
        "name": name,
        "content": template_path.read_text(),
        "path": str(template_path),
    }

    if meta_path.exists():
        result["metadata"] = json.loads(meta_path.read_text())
        result["variables"] = result["metadata"].get("variables", [])

    return result


def apply_template(
    name: str,
    variables: Dict[str, str],
    output_path: Optional[Path] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Apply a template with variable substitution.

    Args:
        name: Template name
        variables: Dict of variable_name -> value
        output_path: Where to write the result (optional)
        project_path: Project path

    Returns:
        Dict with applied content and path
    """
    template = load_template(name, project_path)
    if not template:
        return {"error": f"Template '{name}' not found"}

    content = template["content"]

    # Substitute variables
    for var_name, value in variables.items():
        content = content.replace(f"{{{{{var_name}}}}}", value)

    # Check for unsubstituted variables
    import re
    remaining = re.findall(r'\{\{(\w+)\}\}', content)
    if remaining:
        return {
            "error": f"Missing variables: {remaining}",
            "required": remaining,
        }

    result = {
        "content": content,
        "template": name,
        "variables_used": list(variables.keys()),
    }

    if output_path:
        output_path.write_text(content)
        result["output_path"] = str(output_path)

    return result


def list_templates(project_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all available templates."""
    templates_dir = get_templates_dir(project_path)
    if not templates_dir.exists():
        return []

    templates = []
    for template_file in templates_dir.glob("*.template"):
        name = template_file.stem
        template = load_template(name, project_path)
        if template:
            templates.append({
                "name": name,
                "description": template.get("metadata", {}).get("description", ""),
                "variables": template.get("variables", []),
            })

    return templates


def create_template_from_file(
    file_path: Path,
    template_name: str,
    variable_patterns: Optional[Dict[str, str]] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a template from an existing file.

    Args:
        file_path: Path to source file
        template_name: Name for the template
        variable_patterns: Dict of pattern -> variable_name for substitution
        project_path: Project path

    Returns:
        Dict with template info
    """
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    content = file_path.read_text()

    # Apply variable patterns
    if variable_patterns:
        for pattern, var_name in variable_patterns.items():
            content = content.replace(pattern, f"{{{{{var_name}}}}}")

    return save_template(
        name=template_name,
        content=content,
        description=f"Created from {file_path.name}",
        project_path=project_path,
    )
