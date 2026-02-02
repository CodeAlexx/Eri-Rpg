"""
Knowledge and learning for coder workflow.

Commands:
- learn: Store patterns to knowledge graph
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import get_planning_dir, ensure_planning_dir


def get_knowledge_path(project_path: Optional[Path] = None) -> Path:
    """Get path to knowledge.json."""
    return get_planning_dir(project_path) / "knowledge.json"


def load_knowledge(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load knowledge from .planning/knowledge.json."""
    knowledge_path = get_knowledge_path(project_path)
    if knowledge_path.exists():
        return json.loads(knowledge_path.read_text())
    return {
        "patterns": [],
        "decisions": [],
        "gotchas": [],
        "conventions": [],
    }


def save_knowledge(knowledge: Dict[str, Any], project_path: Optional[Path] = None) -> None:
    """Save knowledge to .planning/knowledge.json."""
    ensure_planning_dir(project_path)
    knowledge_path = get_knowledge_path(project_path)
    knowledge_path.write_text(json.dumps(knowledge, indent=2))


def add_pattern(
    name: str,
    description: str,
    code_example: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source_file: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a pattern to the knowledge base.

    Args:
        name: Pattern name (e.g., "Repository Pattern")
        description: What the pattern does and when to use it
        code_example: Optional code example
        tags: Optional tags for categorization
        source_file: Optional source file where pattern is implemented
        project_path: Project path

    Returns:
        The created pattern entry
    """
    knowledge = load_knowledge(project_path)

    pattern = {
        "id": len(knowledge["patterns"]) + 1,
        "name": name,
        "description": description,
        "code_example": code_example,
        "tags": tags or [],
        "source_file": source_file,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    knowledge["patterns"].append(pattern)
    save_knowledge(knowledge, project_path)

    return pattern


def add_decision(
    title: str,
    choice: str,
    rationale: str,
    alternatives: Optional[List[Dict[str, str]]] = None,
    context: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a decision to the knowledge base.

    Args:
        title: Decision title (e.g., "Database Choice")
        choice: What was chosen
        rationale: Why this choice was made
        alternatives: List of alternatives considered
        context: Additional context
        project_path: Project path

    Returns:
        The created decision entry
    """
    knowledge = load_knowledge(project_path)

    decision = {
        "id": len(knowledge["decisions"]) + 1,
        "title": title,
        "choice": choice,
        "rationale": rationale,
        "alternatives": alternatives or [],
        "context": context,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    knowledge["decisions"].append(decision)
    save_knowledge(knowledge, project_path)

    return decision


def add_gotcha(
    title: str,
    description: str,
    solution: Optional[str] = None,
    affected_files: Optional[List[str]] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a gotcha/pitfall to the knowledge base.

    Args:
        title: Gotcha title (e.g., "JWT Token Expiry")
        description: What the gotcha is
        solution: How to handle/avoid it
        affected_files: Files where this gotcha applies
        project_path: Project path

    Returns:
        The created gotcha entry
    """
    knowledge = load_knowledge(project_path)

    gotcha = {
        "id": len(knowledge["gotchas"]) + 1,
        "title": title,
        "description": description,
        "solution": solution,
        "affected_files": affected_files or [],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    knowledge["gotchas"].append(gotcha)
    save_knowledge(knowledge, project_path)

    return gotcha


def add_convention(
    name: str,
    description: str,
    examples: Optional[List[str]] = None,
    scope: str = "project",
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a coding convention to the knowledge base.

    Args:
        name: Convention name (e.g., "File Naming")
        description: What the convention is
        examples: Example usages
        scope: Scope of convention (project, module, file)
        project_path: Project path

    Returns:
        The created convention entry
    """
    knowledge = load_knowledge(project_path)

    convention = {
        "id": len(knowledge["conventions"]) + 1,
        "name": name,
        "description": description,
        "examples": examples or [],
        "scope": scope,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    knowledge["conventions"].append(convention)
    save_knowledge(knowledge, project_path)

    return convention


def search_knowledge(
    query: str,
    category: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, List[Dict]]:
    """Search the knowledge base.

    Args:
        query: Search query
        category: Optional category filter (patterns, decisions, gotchas, conventions)
        project_path: Project path

    Returns:
        Dict with matching entries by category
    """
    knowledge = load_knowledge(project_path)
    query_lower = query.lower()

    results = {}
    categories = [category] if category else ["patterns", "decisions", "gotchas", "conventions"]

    for cat in categories:
        if cat in knowledge:
            matches = []
            for item in knowledge[cat]:
                # Search in relevant fields
                searchable = []
                if "name" in item:
                    searchable.append(item["name"])
                if "title" in item:
                    searchable.append(item["title"])
                if "description" in item:
                    searchable.append(item["description"])
                if "tags" in item:
                    searchable.extend(item["tags"])
                if "choice" in item:
                    searchable.append(item["choice"])

                if any(query_lower in s.lower() for s in searchable):
                    matches.append(item)

            if matches:
                results[cat] = matches

    return results


def get_knowledge_summary(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get a summary of the knowledge base."""
    knowledge = load_knowledge(project_path)

    return {
        "patterns": len(knowledge.get("patterns", [])),
        "decisions": len(knowledge.get("decisions", [])),
        "gotchas": len(knowledge.get("gotchas", [])),
        "conventions": len(knowledge.get("conventions", [])),
        "total": sum(len(v) for v in knowledge.values() if isinstance(v, list)),
    }


def export_knowledge(
    output_format: str = "markdown",
    project_path: Optional[Path] = None,
) -> str:
    """Export knowledge base to specified format.

    Args:
        output_format: "markdown" or "json"
        project_path: Project path

    Returns:
        Exported content as string
    """
    knowledge = load_knowledge(project_path)

    if output_format == "json":
        return json.dumps(knowledge, indent=2)

    # Markdown format
    output = "# Project Knowledge Base\n\n"
    output += f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"

    # Patterns
    if knowledge.get("patterns"):
        output += "## Patterns\n\n"
        for p in knowledge["patterns"]:
            output += f"### {p['name']}\n\n"
            output += f"{p['description']}\n\n"
            if p.get("code_example"):
                output += f"```\n{p['code_example']}\n```\n\n"
            if p.get("tags"):
                output += f"Tags: {', '.join(p['tags'])}\n\n"

    # Decisions
    if knowledge.get("decisions"):
        output += "## Decisions\n\n"
        for d in knowledge["decisions"]:
            output += f"### {d['title']}\n\n"
            output += f"**Choice:** {d['choice']}\n\n"
            output += f"**Rationale:** {d['rationale']}\n\n"
            if d.get("alternatives"):
                output += "**Alternatives considered:**\n"
                for alt in d["alternatives"]:
                    output += f"- {alt.get('name', 'Unknown')}: {alt.get('reason', '')}\n"
                output += "\n"

    # Gotchas
    if knowledge.get("gotchas"):
        output += "## Gotchas & Pitfalls\n\n"
        for g in knowledge["gotchas"]:
            output += f"### {g['title']}\n\n"
            output += f"{g['description']}\n\n"
            if g.get("solution"):
                output += f"**Solution:** {g['solution']}\n\n"

    # Conventions
    if knowledge.get("conventions"):
        output += "## Conventions\n\n"
        for c in knowledge["conventions"]:
            output += f"### {c['name']}\n\n"
            output += f"{c['description']}\n\n"
            if c.get("examples"):
                output += "**Examples:**\n"
                for ex in c["examples"]:
                    output += f"- {ex}\n"
                output += "\n"

    return output


def import_from_phase(
    phase: int,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Import knowledge from a completed phase.

    Extracts patterns, decisions, and gotchas from SUMMARY.md files.
    """
    from .planning import list_phase_plans

    planning_dir = get_planning_dir(project_path)
    imported = {"patterns": 0, "decisions": 0, "gotchas": 0}

    # Find phase directory
    phases_dir = planning_dir / "phases"
    for d in phases_dir.iterdir() if phases_dir.exists() else []:
        if d.name.startswith(f"{phase:02d}-"):
            # Process summary files (handle both naming conventions)
            summary_files = list(d.glob("SUMMARY-*.md")) + list(d.glob("*-SUMMARY.md"))
            for summary_file in summary_files:
                content = summary_file.read_text()

                # Extract decisions
                if "## Decisions Made" in content:
                    section = content.split("## Decisions Made")[1]
                    section = section.split("##")[0] if "##" in section else section
                    for line in section.split("\n"):
                        line = line.strip()
                        if line.startswith("-") or line.startswith("*"):
                            # This looks like a decision
                            add_decision(
                                title=f"Phase {phase} Decision",
                                choice=line[1:].strip(),
                                rationale="Extracted from phase summary",
                                project_path=project_path,
                            )
                            imported["decisions"] += 1

                # Extract deviations as gotchas
                if "## Deviations from Plan" in content:
                    section = content.split("## Deviations from Plan")[1]
                    section = section.split("##")[0] if "##" in section else section
                    if "None" not in section:
                        for line in section.split("\n"):
                            line = line.strip()
                            if line.startswith("-") or line.startswith("*"):
                                add_gotcha(
                                    title=f"Phase {phase} Deviation",
                                    description=line[1:].strip(),
                                    project_path=project_path,
                                )
                                imported["gotchas"] += 1

    return imported
