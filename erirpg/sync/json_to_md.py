"""
Generate Markdown files from JSON data.

For imports: when you have JSON and need to generate the MD source of truth.
"""

import json
import os
from datetime import datetime
from typing import Optional

from erirpg.models.roadmap import Roadmap, Phase, PhaseGoal, Milestone
from erirpg.models.state import State


def roadmap_to_md(roadmap: Roadmap) -> str:
    """Convert a Roadmap object to Markdown.

    Args:
        roadmap: Roadmap object

    Returns:
        ROADMAP.md content
    """
    lines = [
        f"# {roadmap.project_name} Roadmap",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]

    # Group phases by milestone
    milestone_phases = {}
    for milestone in roadmap.milestones:
        milestone_phases[milestone.version] = []

    for phase in roadmap.phases:
        # Find which milestone this phase belongs to
        for milestone in roadmap.milestones:
            if milestone.start_phase <= phase.number <= milestone.end_phase:
                milestone_phases[milestone.version].append(phase)
                break
        else:
            # Phase doesn't belong to any milestone
            if "unassigned" not in milestone_phases:
                milestone_phases["unassigned"] = []
            milestone_phases["unassigned"].append(phase)

    # Write milestones and their phases
    for milestone in roadmap.milestones:
        lines.extend([
            f"## Milestone: {milestone.version} - {milestone.name}",
            "",
        ])

        if milestone.description:
            lines.extend([milestone.description, ""])

        for phase in milestone_phases.get(milestone.version, []):
            lines.extend(_phase_to_md(phase))

    # Write unassigned phases
    if milestone_phases.get("unassigned"):
        lines.extend([
            "## Unassigned Phases",
            "",
        ])
        for phase in milestone_phases["unassigned"]:
            lines.extend(_phase_to_md(phase))

    # Write phases if no milestones
    if not roadmap.milestones:
        for phase in roadmap.phases:
            lines.extend(_phase_to_md(phase))

    return "\n".join(lines)


def _phase_to_md(phase: Phase) -> list:
    """Convert a Phase to Markdown lines."""
    lines = [
        f"### Phase {phase.number}: {phase.title}",
        "",
    ]

    if phase.description:
        lines.extend([phase.description, ""])

    # Status
    status_icon = {
        "completed": "✅",
        "in_progress": "🔄",
        "pending": "⏳",
        "blocked": "🚫",
    }.get(phase.status, "")
    lines.append(f"- Status: {status_icon} {phase.status}")

    # Dependencies
    if phase.depends_on:
        deps = ", ".join(str(d) for d in phase.depends_on)
        lines.append(f"- Dependencies: Phase {deps}")
    else:
        lines.append("- Dependencies: none")

    # Goals
    if phase.goals:
        lines.extend(["", "- Goals:"])
        for goal in phase.goals:
            checkbox = "[x]" if goal.completed else "[ ]"
            req_ids = ", ".join(goal.requirement_ids) if goal.requirement_ids else ""
            req_prefix = f"{req_ids}: " if req_ids else ""
            lines.append(f"  - {checkbox} {req_prefix}{goal.description}")

    lines.append("")
    return lines


def state_to_md(state: State) -> str:
    """Convert a State object to Markdown.

    Args:
        state: State object

    Returns:
        STATE.md content
    """
    lines = [
        f"# {state.project_name} State",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]

    # Current Position
    lines.extend([
        "## Current Position",
        "",
    ])

    pos = state.position
    if pos.current_milestone:
        lines.append(f"- Milestone: {pos.current_milestone}")
    if pos.current_phase:
        lines.append(f"- Phase: {pos.current_phase}")
    if pos.current_plan:
        lines.append(f"- Plan: {pos.current_plan}")
    if pos.current_task:
        lines.append(f"- Task: {pos.current_task}")
    lines.append(f"- Status: {pos.status}")
    lines.append("")

    # Metrics
    metrics = state.metrics
    lines.extend([
        "## Metrics",
        "",
        f"- Plans completed: {metrics.plans_completed}",
        f"- Plans failed: {metrics.plans_failed}",
        f"- Average duration: {metrics.average_plan_duration_minutes:.1f} min",
        f"- Phases completed: {metrics.phases_completed}",
        f"- Tasks completed: {metrics.total_tasks_completed}",
        f"- Total commits: {metrics.total_commits}",
        f"- Verification pass rate: {metrics.verification_pass_rate * 100:.1f}%",
        f"- Gaps found: {metrics.gaps_found}",
        f"- Gaps resolved: {metrics.gaps_resolved}",
        "",
    ])

    # Decisions
    if state.decisions:
        lines.extend([
            "## Decisions",
            "",
        ])
        for d in state.decisions:
            date = d.get("date", "")
            decision = d.get("decision", "")
            rationale = d.get("rationale", "")
            if date:
                lines.append(f"- [{date}] {decision}: {rationale}")
            else:
                lines.append(f"- {decision}: {rationale}")
        lines.append("")

    # Todos
    if state.todos:
        lines.extend([
            "## Todos",
            "",
        ])
        for todo in state.todos:
            lines.append(f"- [ ] {todo}")
        lines.append("")

    # Blockers
    if state.blockers:
        lines.extend([
            "## Blockers",
            "",
        ])
        for blocker in state.blockers:
            lines.append(f"- {blocker}")
        lines.append("")

    # Continuity
    cont = state.continuity
    if cont.last_session or cont.last_action or cont.pending_checkpoint:
        lines.extend([
            "## Continuity",
            "",
        ])
        if cont.last_session:
            lines.append(f"- Last session: {cont.last_session}")
        if cont.last_action:
            lines.append(f"- Last action: {cont.last_action}")
        if cont.stopped_at:
            lines.append(f"- Stopped at: {cont.stopped_at}")
        if cont.pending_checkpoint:
            lines.append(f"- Pending checkpoint: {cont.pending_checkpoint}")
        if cont.handoff_context:
            lines.append(f"- Handoff context: {cont.handoff_context}")
        lines.append("")

    return "\n".join(lines)


def roadmap_json_to_md(project_path: str) -> str:
    """Generate ROADMAP.md from roadmap.json.

    Args:
        project_path: Path to project root

    Returns:
        Path to generated ROADMAP.md
    """
    json_path = os.path.join(project_path, ".eri-rpg", "roadmap.json")
    md_path = os.path.join(project_path, ".eri-rpg", "ROADMAP.md")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"roadmap.json not found at {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    roadmap = Roadmap.from_dict(data)
    content = roadmap_to_md(roadmap)

    with open(md_path, "w") as f:
        f.write(content)

    return md_path


def state_json_to_md(project_path: str) -> str:
    """Generate STATE.md from state.json.

    Args:
        project_path: Path to project root

    Returns:
        Path to generated STATE.md
    """
    json_path = os.path.join(project_path, ".eri-rpg", "state.json")
    md_path = os.path.join(project_path, ".eri-rpg", "STATE.md")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"state.json not found at {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    state = State.from_dict(data)
    content = state_to_md(state)

    with open(md_path, "w") as f:
        f.write(content)

    return md_path


def ensure_both_formats(project_path: str) -> None:
    """Ensure both MD and JSON formats exist for roadmap and state.

    If only one exists, generates the other.

    Args:
        project_path: Path to project root
    """
    eri_dir = os.path.join(project_path, ".eri-rpg")

    # Roadmap
    roadmap_md = os.path.join(eri_dir, "ROADMAP.md")
    roadmap_json = os.path.join(eri_dir, "roadmap.json")

    if os.path.exists(roadmap_md) and not os.path.exists(roadmap_json):
        from erirpg.sync.md_to_json import sync_roadmap
        sync_roadmap(project_path)
    elif os.path.exists(roadmap_json) and not os.path.exists(roadmap_md):
        roadmap_json_to_md(project_path)

    # State
    state_md = os.path.join(eri_dir, "STATE.md")
    state_json = os.path.join(eri_dir, "state.json")

    if os.path.exists(state_md) and not os.path.exists(state_json):
        from erirpg.sync.md_to_json import sync_state
        sync_state(project_path)
    elif os.path.exists(state_json) and not os.path.exists(state_md):
        state_json_to_md(project_path)
