"""
CONTEXT.md generator for session-specific context.

Generates a markdown file summarizing the current session's context,
including decisions, blockers, and next actions from SQLite.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from erirpg import storage


def generate_context_md(
    project_name: str,
    session_id: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate CONTEXT.md from session data.

    Args:
        project_name: Name of the project
        session_id: Specific session ID, or None for latest session
        output_path: Path to write file, or None to return content only

    Returns:
        Generated markdown content
    """
    # Get session context
    if session_id:
        ctx = storage.get_session_context(session_id)
    else:
        latest = storage.get_latest_session(project_name)
        if latest:
            ctx = storage.get_session_context(latest.id)
        else:
            ctx = {}

    if not ctx or not ctx.get("session"):
        content = _generate_empty_context(project_name)
    else:
        content = _generate_context_content(project_name, ctx)

    if output_path:
        Path(output_path).write_text(content)

    return content


def _generate_empty_context(project_name: str) -> str:
    """Generate empty context when no session data exists."""
    return f"""# Context: {project_name}

_No session context available._

Use `/eri:work` or `/eri:new` to start a session.
"""


def _generate_context_content(project_name: str, ctx: dict) -> str:
    """Generate context content from session data."""
    session = ctx["session"]
    decisions = ctx.get("decisions", [])
    blockers = ctx.get("blockers", [])
    next_actions = ctx.get("next_actions", [])
    learnings = ctx.get("learnings", [])

    lines = []

    # Header
    lines.append(f"# Context: {project_name}")
    lines.append("")
    lines.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    # Session status
    lines.append("## Session Status")
    lines.append("")
    if session.get("phase"):
        lines.append(f"- **Phase**: {session['phase']}")
    if session.get("step"):
        lines.append(f"- **Step**: {session['step']}")
    if session.get("progress_pct"):
        lines.append(f"- **Progress**: {session['progress_pct']}%")
    if session.get("started_at"):
        lines.append(f"- **Started**: {session['started_at']}")
    if session.get("files_modified"):
        lines.append(f"- **Files modified**: {len(session['files_modified'])}")
    lines.append("")

    # Decisions
    if decisions:
        lines.append("## Decisions")
        lines.append("")
        for i, d in enumerate(decisions, 1):
            lines.append(f"### {i}. {d['context']}")
            lines.append("")
            lines.append(f"**Decision**: {d['decision']}")
            if d.get("rationale"):
                lines.append(f"**Rationale**: {d['rationale']}")
            lines.append("")

    # Blockers
    unresolved = [b for b in blockers if not b.get("resolved")]
    resolved = [b for b in blockers if b.get("resolved")]

    if unresolved:
        lines.append("## Blockers")
        lines.append("")
        for b in unresolved:
            severity = b.get("severity", "MEDIUM")
            marker = "!" if severity in ("HIGH", "CRITICAL") else "-"
            lines.append(f"{marker} **[{severity}]** {b['description']}")
        lines.append("")

    if resolved:
        lines.append("## Resolved Blockers")
        lines.append("")
        for b in resolved:
            lines.append(f"- ~~{b['description']}~~ - {b.get('resolution', 'resolved')}")
        lines.append("")

    # Next actions
    pending = [a for a in next_actions if not a.get("completed")]
    if pending:
        lines.append("## Next Actions")
        lines.append("")
        # Sort by priority (higher first)
        pending.sort(key=lambda a: a.get("priority", 0), reverse=True)
        for i, a in enumerate(pending, 1):
            priority = a.get("priority", 0)
            marker = "!" if priority >= 5 else str(i) + "."
            lines.append(f"{marker} {a['action']}")
        lines.append("")

    # Learnings
    if learnings:
        lines.append("## Session Learnings")
        lines.append("")
        for l in learnings:
            lines.append(f"### {l['topic']}")
            lines.append("")
            lines.append(l["content"])
            lines.append("")

    # Files modified
    if session.get("files_modified"):
        lines.append("## Files Modified")
        lines.append("")
        lines.append("```")
        for f in session["files_modified"]:
            lines.append(f)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def generate_compact_summary(project_name: str) -> str:
    """Generate a compact one-line summary for SessionStart hook.

    Format: EriRPG: {project} | Phase: {phase} | Step: {step}
            Last session: {time} | Decisions: {n} | Blockers: {n} {severity}
    """
    summary = storage.get_project_context_summary(project_name)

    if not summary.get("has_context"):
        return f"EriRPG: {project_name} | No prior session context"

    last = summary["last_session"]
    hours = last.get("hours_ago", 0)

    if hours < 1:
        time_str = "just now"
    elif hours < 24:
        time_str = f"{int(hours)}h ago"
    else:
        days = int(hours / 24)
        time_str = f"{days}d ago"

    parts = [f"EriRPG: {project_name}"]

    if last.get("phase"):
        parts.append(f"Phase: {last['phase']}")
    if last.get("step"):
        parts.append(f"Step: {last['step']}")

    line1 = " | ".join(parts)

    parts2 = [f"Last session: {time_str}"]

    if summary.get("decisions_count"):
        parts2.append(f"Decisions: {summary['decisions_count']}")

    if summary.get("blockers_count"):
        blocker_str = f"Blockers: {summary['blockers_count']}"
        if summary.get("blockers_high"):
            blocker_str += f" ({summary['blockers_high']} HIGH)"
        parts2.append(blocker_str)

    if summary.get("pending_actions"):
        parts2.append(f"Actions: {summary['pending_actions']}")

    line2 = " | ".join(parts2)

    return f"{line1}\n{line2}\nResume: /eri:status --full for details"
