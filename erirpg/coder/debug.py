"""
Debug workflow support for coder.

Commands:
- debug: Systematic debugging with hypothesis tracking
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import get_planning_dir, ensure_planning_dir, timestamp


def get_debug_dir(project_path: Optional[Path] = None) -> Path:
    """Get debug sessions directory."""
    return get_planning_dir(project_path) / "debug"


def init_debug_session(
    trigger: str,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Initialize a new debug session.

    Args:
        trigger: User's description of the issue
        project_path: Project path

    Returns:
        Session info
    """
    debug_dir = get_debug_dir(project_path)
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Create session file
    session_path = debug_dir / "active-session.md"

    # Generate slug from trigger
    slug = trigger.lower()[:30].replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    content = f"""---
status: gathering
trigger: "{trigger}"
created: {timestamp()}
updated: {timestamp()}
slug: {slug}
---

# Debug Session: {slug}

## Trigger
> {trigger}

## Current Focus
hypothesis: [To be determined]
test: [To be determined]
next_action: Gather symptoms

## Symptoms
expected: [What should happen]
actual: [What actually happens]
reproducible: [always | sometimes | once]

## Environment
- OS: [if relevant]
- Version: [app version]
- Last working: [if known]

## Hypotheses
[To be added]

## Eliminated
[Hypotheses proven wrong will go here]

## Evidence
[What was checked and found]

## Resolution
root_cause: [when found]
fix: [when applied]
commit: [fix commit hash]
"""

    session_path.write_text(content)

    return {
        "path": str(session_path),
        "slug": slug,
        "status": "gathering",
    }


def get_active_session(project_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Get active debug session if one exists."""
    debug_dir = get_debug_dir(project_path)
    session_path = debug_dir / "active-session.md"

    if not session_path.exists():
        return None

    content = session_path.read_text()

    # Parse frontmatter
    frontmatter = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except:
                pass

    return {
        "path": str(session_path),
        "content": content,
        "status": frontmatter.get("status", "unknown"),
        "trigger": frontmatter.get("trigger", ""),
        "slug": frontmatter.get("slug", ""),
        "created": frontmatter.get("created", ""),
    }


def update_session_status(
    status: str,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Update debug session status.

    Args:
        status: New status (gathering, investigating, fixing, verifying, resolved)
        project_path: Project path
    """
    session = get_active_session(project_path)
    if not session:
        return {"error": "No active debug session"}

    valid_statuses = ["gathering", "investigating", "fixing", "verifying", "resolved"]
    if status not in valid_statuses:
        return {"error": f"Invalid status. Must be one of: {valid_statuses}"}

    content = session["content"]

    # Update status in frontmatter
    content = content.replace(
        f"status: {session['status']}",
        f"status: {status}"
    )

    # Update timestamp
    import re
    content = re.sub(
        r"updated: .*",
        f"updated: {timestamp()}",
        content
    )

    session_path = Path(session["path"])
    session_path.write_text(content)

    return {"status": status}


def add_hypothesis(
    hypothesis: str,
    likelihood: str = "medium",
    test: str = "",
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a hypothesis to the active session.

    Args:
        hypothesis: What might be causing the issue
        likelihood: high, medium, or low
        test: How to test this hypothesis
        project_path: Project path
    """
    session = get_active_session(project_path)
    if not session:
        return {"error": "No active debug session"}

    content = session["content"]

    # Find hypotheses section and add
    hypothesis_entry = f"\n| {hypothesis[:50]} | {likelihood} | {test[:50]} |"

    if "## Hypotheses" in content:
        # Check if table exists
        if "|---" in content.split("## Hypotheses")[1].split("##")[0]:
            # Add to existing table
            parts = content.split("## Hypotheses")
            section = parts[1].split("##")[0] if "##" in parts[1] else parts[1]
            # Find last row
            lines = section.split("\n")
            insert_idx = len(lines) - 1
            for i, line in enumerate(lines):
                if line.strip().startswith("|") and not line.strip().startswith("|---"):
                    insert_idx = i + 1
            lines.insert(insert_idx, hypothesis_entry)
            parts[1] = "\n".join(lines) + ("##" + "##".join(parts[1].split("##")[1:]) if "##" in parts[1] else "")
            content = "## Hypotheses".join(parts)
        else:
            # Create table
            table = "\n| # | Hypothesis | Likelihood | Test |\n"
            table += "|---|------------|------------|------|\n"
            table += f"| 1 | {hypothesis[:50]} | {likelihood} | {test[:50]} |\n"
            content = content.replace("## Hypotheses\n[To be added]", "## Hypotheses" + table)

    session_path = Path(session["path"])
    session_path.write_text(content)

    # Update status to investigating if still gathering
    if session["status"] == "gathering":
        update_session_status("investigating", project_path)

    return {"added": hypothesis}


def eliminate_hypothesis(
    hypothesis: str,
    evidence: str,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Mark a hypothesis as eliminated.

    Args:
        hypothesis: Which hypothesis was eliminated
        evidence: What disproved it
        project_path: Project path
    """
    session = get_active_session(project_path)
    if not session:
        return {"error": "No active debug session"}

    content = session["content"]

    # Add to eliminated section
    entry = f"\n- hypothesis: {hypothesis}\n  evidence: {evidence}\n"

    if "## Eliminated" in content:
        parts = content.split("## Eliminated")
        section_end = parts[1].find("##")
        if section_end == -1:
            parts[1] = parts[1].rstrip() + entry + "\n"
        else:
            parts[1] = parts[1][:section_end].rstrip() + entry + "\n" + parts[1][section_end:]
        content = "## Eliminated".join(parts)

    session_path = Path(session["path"])
    session_path.write_text(content)

    return {"eliminated": hypothesis}


def add_evidence(
    checked: str,
    found: str,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add evidence to the debug session.

    Args:
        checked: What was examined
        found: What was discovered
        project_path: Project path
    """
    session = get_active_session(project_path)
    if not session:
        return {"error": "No active debug session"}

    content = session["content"]

    entry = f"\n- checked: {checked}\n  found: {found}\n"

    if "## Evidence" in content:
        parts = content.split("## Evidence")
        section_end = parts[1].find("##")
        if section_end == -1:
            parts[1] = parts[1].rstrip() + entry + "\n"
        else:
            parts[1] = parts[1][:section_end].rstrip() + entry + "\n" + parts[1][section_end:]
        content = "## Evidence".join(parts)

    session_path = Path(session["path"])
    session_path.write_text(content)

    return {"added": checked}


def resolve_session(
    root_cause: str,
    fix: str,
    commit: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Resolve the debug session.

    Args:
        root_cause: What was the actual cause
        fix: What was done to fix it
        commit: Optional commit hash of the fix
        project_path: Project path
    """
    session = get_active_session(project_path)
    if not session:
        return {"error": "No active debug session"}

    content = session["content"]

    # Update resolution section
    resolution = f"""root_cause: {root_cause}
fix: {fix}
commit: {commit or '[not committed]'}"""

    content = content.replace(
        """root_cause: [when found]
fix: [when applied]
commit: [fix commit hash]""",
        resolution
    )

    # Update status
    content = content.replace(
        f"status: {session['status']}",
        "status: resolved"
    )

    # Move to resolved directory
    debug_dir = get_debug_dir(project_path)
    resolved_dir = debug_dir / "resolved"
    resolved_dir.mkdir(exist_ok=True)

    # Archive with timestamp
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = resolved_dir / f"{ts}-{session['slug']}.md"
    archive_path.write_text(content)

    # Remove active session
    session_path = Path(session["path"])
    session_path.unlink()

    return {
        "resolved": True,
        "root_cause": root_cause,
        "fix": fix,
        "archived": str(archive_path),
    }


def list_debug_sessions(
    include_resolved: bool = True,
    limit: int = 10,
    project_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """List debug sessions.

    Args:
        include_resolved: Include resolved sessions
        limit: Maximum sessions to return
        project_path: Project path
    """
    debug_dir = get_debug_dir(project_path)
    sessions = []

    # Check for active session
    active = get_active_session(project_path)
    if active:
        sessions.append({
            "slug": active["slug"],
            "status": active["status"],
            "created": active["created"],
            "active": True,
        })

    # Check resolved sessions
    if include_resolved:
        resolved_dir = debug_dir / "resolved"
        if resolved_dir.exists():
            for session_file in sorted(resolved_dir.glob("*.md"), reverse=True)[:limit]:
                content = session_file.read_text()
                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml
                        try:
                            fm = yaml.safe_load(parts[1]) or {}
                            sessions.append({
                                "slug": fm.get("slug", session_file.stem),
                                "status": "resolved",
                                "created": fm.get("created", ""),
                                "trigger": fm.get("trigger", ""),
                                "active": False,
                            })
                        except:
                            pass

    return sessions[:limit]
