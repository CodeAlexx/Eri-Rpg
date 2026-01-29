"""
STATUS.md generator for project-wide status.

Generates a markdown file summarizing the project's overall status,
including recent sessions, decisions, and blockers across all sessions.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from erirpg import storage


def generate_status_md(
    project_name: str,
    output_path: Optional[str] = None,
    include_resolved: bool = False,
) -> str:
    """Generate STATUS.md from project data.

    Args:
        project_name: Name of the project
        output_path: Path to write file, or None to return content only
        include_resolved: Include resolved blockers

    Returns:
        Generated markdown content
    """
    # Gather data
    latest = storage.get_latest_session(project_name)
    recent_decisions = storage.get_recent_decisions(project_name, limit=10)
    unresolved_blockers = storage.get_unresolved_blockers(project_name)
    pending_actions = storage.get_pending_actions(project_name)

    content = _generate_status_content(
        project_name,
        latest,
        recent_decisions,
        unresolved_blockers,
        pending_actions,
        include_resolved,
    )

    if output_path:
        Path(output_path).write_text(content)

    return content


def _generate_status_content(
    project_name: str,
    latest_session: Optional[storage.Session],
    recent_decisions: list,
    unresolved_blockers: list,
    pending_actions: list,
    include_resolved: bool = False,
) -> str:
    """Generate the STATUS.md content."""
    lines = []

    # Header
    lines.append(f"# Status: {project_name}")
    lines.append("")
    lines.append(f"_Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    # Current position
    lines.append("## Current Position")
    lines.append("")

    if latest_session:
        if latest_session.phase:
            lines.append(f"- **Phase**: {latest_session.phase}")
        if latest_session.step:
            lines.append(f"- **Step**: {latest_session.step}")
        if latest_session.progress_pct:
            lines.append(f"- **Progress**: {latest_session.progress_pct}%")
        if latest_session.ended_at:
            lines.append(f"- **Last active**: {latest_session.ended_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            lines.append(f"- **Started**: {latest_session.started_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        lines.append("_No session history_")
    lines.append("")

    # Blockers (high priority section)
    if unresolved_blockers:
        lines.append("## Blockers")
        lines.append("")
        # Group by severity
        critical = [b for b in unresolved_blockers if b.severity == "CRITICAL"]
        high = [b for b in unresolved_blockers if b.severity == "HIGH"]
        medium = [b for b in unresolved_blockers if b.severity == "MEDIUM"]
        low = [b for b in unresolved_blockers if b.severity == "LOW"]

        if critical:
            lines.append("### CRITICAL")
            for b in critical:
                lines.append(f"- {b.description}")
            lines.append("")

        if high:
            lines.append("### HIGH")
            for b in high:
                lines.append(f"- {b.description}")
            lines.append("")

        if medium:
            lines.append("### MEDIUM")
            for b in medium:
                lines.append(f"- {b.description}")
            lines.append("")

        if low:
            lines.append("### LOW")
            for b in low:
                lines.append(f"- {b.description}")
            lines.append("")

    # Next actions
    if pending_actions:
        lines.append("## Next Actions")
        lines.append("")
        # Sort by priority
        sorted_actions = sorted(pending_actions, key=lambda a: a.priority, reverse=True)
        for i, action in enumerate(sorted_actions[:10], 1):
            priority_marker = "!" if action.priority >= 5 else ""
            lines.append(f"{i}. {priority_marker}{action.action}")
        if len(pending_actions) > 10:
            lines.append(f"_...and {len(pending_actions) - 10} more_")
        lines.append("")

    # Recent decisions
    if recent_decisions:
        lines.append("## Recent Decisions")
        lines.append("")
        for d in recent_decisions[:5]:
            date_str = d.timestamp.strftime("%m/%d")
            lines.append(f"- **{date_str}**: {d.context}")
            lines.append(f"  - {d.decision}")
            if d.rationale:
                lines.append(f"  - _Why: {d.rationale}_")
        if len(recent_decisions) > 5:
            lines.append(f"_...and {len(recent_decisions) - 5} more_")
        lines.append("")

    # Quick resume section
    lines.append("## Resume Commands")
    lines.append("")
    lines.append("```bash")
    lines.append(f"/eri:status --full     # Full context")
    lines.append(f"/eri:recall decisions  # List all decisions")
    lines.append(f"/eri:recall blockers   # List all blockers")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def get_status_path(project_path: str) -> str:
    """Get the path to STATUS.md for a project."""
    eri_dir = Path(project_path) / ".eri-rpg"
    eri_dir.mkdir(parents=True, exist_ok=True)
    return str(eri_dir / "STATUS.md")


def regenerate_status(project_name: str, project_path: str) -> str:
    """Regenerate STATUS.md for a project.

    Returns the path to the generated file.
    """
    output_path = get_status_path(project_path)
    generate_status_md(project_name, output_path)
    return output_path
