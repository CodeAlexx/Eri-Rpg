"""
Parse Markdown files → generate JSON files.

ROADMAP.md and STATE.md are sources of truth.
This module parses them and generates roadmap.json and state.json.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from erirpg.models.roadmap import Roadmap, Phase, PhaseGoal, Milestone
from erirpg.models.state import State, StatePosition, StateMetrics, StateContinuity


def parse_roadmap_md(content: str, project_name: str = "") -> Roadmap:
    """Parse ROADMAP.md content into a Roadmap object.

    Expected format:
    ```
    # Project Roadmap

    ## Milestone: v1 - MVP

    ### Phase 1: Project Setup
    - Goals:
      - [x] REQ-001: Initialize project structure
      - [ ] REQ-002: Set up CI/CD
    - Dependencies: none
    - Status: completed

    ### Phase 2: Authentication
    ...
    ```

    Args:
        content: ROADMAP.md content
        project_name: Project name (optional, extracted from content if not provided)

    Returns:
        Roadmap object
    """
    roadmap = Roadmap(project_name=project_name)

    lines = content.split("\n")
    current_milestone: Optional[Milestone] = None
    current_phase: Optional[Phase] = None
    current_section = ""  # "goals", "dependencies", etc.

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Project title
        if line.startswith("# ") and not project_name:
            title = line[2:].strip()
            if "Roadmap" in title:
                roadmap.project_name = title.replace("Roadmap", "").strip()

        # Milestone header: ## Milestone: v1 - MVP
        elif line.startswith("## Milestone:") or line.startswith("## v"):
            milestone_text = line.replace("## Milestone:", "").replace("##", "").strip()
            # Parse "v1 - MVP" or "v1: MVP"
            match = re.match(r"(v\d+)\s*[-:]\s*(.+)", milestone_text)
            if match:
                version, name = match.groups()
            else:
                version = milestone_text.split()[0] if milestone_text else "v1"
                name = milestone_text

            current_milestone = Milestone(
                version=version.strip(),
                name=name.strip(),
            )
            roadmap.milestones.append(current_milestone)

        # Phase header: ### Phase 1: Project Setup
        elif line.startswith("### Phase ") or re.match(r"^###\s+\d+\.", line):
            phase_match = re.match(r"###\s+Phase\s+(\d+)[:\s]+(.+)", line)
            if not phase_match:
                phase_match = re.match(r"###\s+(\d+)\.\s*(.+)", line)

            if phase_match:
                number = int(phase_match.group(1))
                title = phase_match.group(2).strip()

                current_phase = Phase(
                    number=number,
                    name="",  # Will be generated from title
                    title=title,
                )

                # Update milestone phase range
                if current_milestone:
                    if current_milestone.start_phase == 0:
                        current_milestone.start_phase = number
                    current_milestone.end_phase = number

                roadmap.phases.append(current_phase)
                current_section = ""

        # Goals section
        elif line.lower().startswith("- goals:") or line.lower() == "goals:":
            current_section = "goals"

        # Dependencies section
        elif line.lower().startswith("- dependencies:") or line.lower().startswith("dependencies:"):
            current_section = "dependencies"
            deps_text = line.split(":", 1)[1].strip() if ":" in line else ""
            if current_phase and deps_text and deps_text.lower() != "none":
                # Parse comma-separated phase numbers
                dep_matches = re.findall(r"\d+", deps_text)
                current_phase.depends_on = [int(d) for d in dep_matches]

        # Status section
        elif line.lower().startswith("- status:") or line.lower().startswith("status:"):
            current_section = "status"
            status_text = line.split(":", 1)[1].strip() if ":" in line else ""
            if current_phase and status_text:
                current_phase.status = status_text.lower()

        # Description section
        elif line.lower().startswith("- description:") or line.lower().startswith("description:"):
            current_section = "description"
            desc_text = line.split(":", 1)[1].strip() if ":" in line else ""
            if current_phase and desc_text:
                current_phase.description = desc_text

        # Goal list items
        elif current_section == "goals" and current_phase:
            # Match: - [x] REQ-001: Description or - [ ] Description
            goal_match = re.match(r"\s*-\s*\[([ xX])\]\s*(REQ-\d+)?:?\s*(.+)", line)
            if goal_match:
                completed = goal_match.group(1).lower() == "x"
                req_id = goal_match.group(2) or ""
                description = goal_match.group(3).strip()

                goal = PhaseGoal(
                    id=req_id or f"GOAL-{len(current_phase.goals) + 1}",
                    description=description,
                    requirement_ids=[req_id] if req_id else [],
                    completed=completed,
                )
                current_phase.goals.append(goal)

            # Simple list item: - Description
            elif line.startswith("  -") or line.startswith("    -"):
                description = line.strip().lstrip("-").strip()
                if description:
                    goal = PhaseGoal(
                        id=f"GOAL-{len(current_phase.goals) + 1}",
                        description=description,
                    )
                    current_phase.goals.append(goal)

        # Continuation of description
        elif current_section == "description" and current_phase and line and not line.startswith("-"):
            current_phase.description += " " + line

        i += 1

    return roadmap


def parse_state_md(content: str, project_name: str = "") -> State:
    """Parse STATE.md content into a State object.

    Expected format:
    ```
    # Project State

    ## Current Position
    - Milestone: v1
    - Phase: 02-authentication
    - Plan: 01
    - Status: executing

    ## Metrics
    - Plans completed: 5
    - Average duration: 12.5 min
    ...

    ## Decisions
    - [2024-01-15] Chose JWT over sessions: Better for API

    ## Todos
    - [ ] Add rate limiting
    - [ ] Improve error messages

    ## Blockers
    - Waiting for API key from vendor
    ```

    Args:
        content: STATE.md content
        project_name: Project name

    Returns:
        State object
    """
    state = State(project_name=project_name)

    lines = content.split("\n")
    current_section = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Project title
        if line.startswith("# ") and not project_name:
            title = line[2:].strip()
            if "State" in title:
                state.project_name = title.replace("State", "").strip()

        # Section headers
        elif line.startswith("## Current Position") or line.startswith("## Position"):
            current_section = "position"

        elif line.startswith("## Metrics") or line.startswith("## Performance"):
            current_section = "metrics"

        elif line.startswith("## Decisions"):
            current_section = "decisions"

        elif line.startswith("## Todos") or line.startswith("## TODO"):
            current_section = "todos"

        elif line.startswith("## Blockers"):
            current_section = "blockers"

        elif line.startswith("## Continuity") or line.startswith("## Session"):
            current_section = "continuity"

        # Parse position items
        elif current_section == "position" and line.startswith("-"):
            key_value = line[1:].strip()
            if ":" in key_value:
                key, value = key_value.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if "milestone" in key:
                    state.position.current_milestone = value
                elif "phase" in key:
                    state.position.current_phase = value
                elif "plan" in key:
                    state.position.current_plan = value
                elif "task" in key:
                    state.position.current_task = value
                elif "status" in key:
                    state.position.status = value

        # Parse metrics items
        elif current_section == "metrics" and line.startswith("-"):
            key_value = line[1:].strip()
            if ":" in key_value:
                key, value = key_value.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                try:
                    if "plans completed" in key:
                        state.metrics.plans_completed = int(value)
                    elif "plans failed" in key:
                        state.metrics.plans_failed = int(value)
                    elif "average" in key and "duration" in key:
                        state.metrics.average_plan_duration_minutes = float(value.replace("min", "").strip())
                    elif "phases completed" in key:
                        state.metrics.phases_completed = int(value)
                    elif "tasks completed" in key:
                        state.metrics.total_tasks_completed = int(value)
                    elif "commits" in key:
                        state.metrics.total_commits = int(value)
                    elif "pass rate" in key:
                        state.metrics.verification_pass_rate = float(value.replace("%", "").strip()) / 100
                    elif "gaps found" in key:
                        state.metrics.gaps_found = int(value)
                    elif "gaps resolved" in key:
                        state.metrics.gaps_resolved = int(value)
                except ValueError:
                    pass  # Skip invalid numbers

        # Parse decisions
        elif current_section == "decisions" and line.startswith("-"):
            decision_text = line[1:].strip()
            # Match: [2024-01-15] Decision: Rationale
            match = re.match(r"\[([^\]]+)\]\s*(.+?):\s*(.+)", decision_text)
            if match:
                date, decision, rationale = match.groups()
                state.decisions.append({
                    "decision": decision.strip(),
                    "rationale": rationale.strip(),
                    "date": date.strip(),
                })
            else:
                # Just add as decision without structure
                state.decisions.append({
                    "decision": decision_text,
                    "rationale": "",
                    "date": "",
                })

        # Parse todos
        elif current_section == "todos" and line.startswith("-"):
            todo_match = re.match(r"-\s*\[[ ]\]\s*(.+)", line)
            if todo_match:
                state.todos.append(todo_match.group(1).strip())
            elif not re.match(r"-\s*\[[xX]\]", line):  # Not completed
                todo_text = line[1:].strip()
                if todo_text:
                    state.todos.append(todo_text)

        # Parse blockers
        elif current_section == "blockers" and line.startswith("-"):
            blocker_text = line[1:].strip()
            if blocker_text:
                state.blockers.append(blocker_text)

        # Parse continuity
        elif current_section == "continuity" and line.startswith("-"):
            key_value = line[1:].strip()
            if ":" in key_value:
                key, value = key_value.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if "last session" in key:
                    state.continuity.last_session = value
                elif "last action" in key:
                    state.continuity.last_action = value
                elif "stopped at" in key:
                    state.continuity.stopped_at = value
                elif "checkpoint" in key:
                    state.continuity.pending_checkpoint = value if value.lower() != "none" else None
                elif "handoff" in key:
                    state.continuity.handoff_context = value

        i += 1

    return state


def sync_roadmap(project_path: str) -> str:
    """Sync ROADMAP.md → roadmap.json.

    Reads ROADMAP.md and generates roadmap.json.

    Args:
        project_path: Path to project root

    Returns:
        Path to generated roadmap.json
    """
    md_path = os.path.join(project_path, ".eri-rpg", "ROADMAP.md")
    json_path = os.path.join(project_path, ".eri-rpg", "roadmap.json")

    if not os.path.exists(md_path):
        raise FileNotFoundError(f"ROADMAP.md not found at {md_path}")

    with open(md_path, "r") as f:
        content = f.read()

    # Get project name from existing JSON if available
    project_name = ""
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            existing = json.load(f)
            project_name = existing.get("project_name", "")

    roadmap = parse_roadmap_md(content, project_name)

    with open(json_path, "w") as f:
        json.dump(roadmap.to_dict(), f, indent=2)

    return json_path


def sync_state(project_path: str) -> str:
    """Sync STATE.md → state.json.

    Reads STATE.md and generates state.json.

    Args:
        project_path: Path to project root

    Returns:
        Path to generated state.json
    """
    md_path = os.path.join(project_path, ".eri-rpg", "STATE.md")
    json_path = os.path.join(project_path, ".eri-rpg", "state.json")

    if not os.path.exists(md_path):
        raise FileNotFoundError(f"STATE.md not found at {md_path}")

    with open(md_path, "r") as f:
        content = f.read()

    # Get project name from existing JSON if available
    project_name = ""
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            existing = json.load(f)
            project_name = existing.get("project_name", "")

    state = parse_state_md(content, project_name)

    with open(json_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    return json_path


def sync_all(project_path: str) -> Tuple[str, str]:
    """Sync both ROADMAP.md and STATE.md to JSON.

    Args:
        project_path: Path to project root

    Returns:
        Tuple of (roadmap.json path, state.json path)
    """
    roadmap_path = None
    state_path = None

    try:
        roadmap_path = sync_roadmap(project_path)
    except FileNotFoundError:
        pass

    try:
        state_path = sync_state(project_path)
    except FileNotFoundError:
        pass

    return roadmap_path, state_path
