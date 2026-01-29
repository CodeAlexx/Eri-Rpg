"""
Goal Commands - Spec-driven execution commands.

Commands (full tier):
- goal-plan: Generate a spec from a goal
- goal-run: Execute a spec for a project
- goal-status: Show spec execution status for a project
"""

import json
import os
import sys
from datetime import datetime

import click

from erirpg.cli_commands.guards import tier_required


def _parse_research_for_phases(research_content: str, goal: str):
    """
    Parse research content to extract phases, files, and structure.
    Returns a list of phases with files and success criteria.
    """
    phases = []
    files_needed = []

    # Detect stack from research
    has_backend = any(k in research_content.lower() for k in ["fastapi", "flask", "backend", "main.py", "server"])
    has_frontend = any(k in research_content.lower() for k in ["html", "frontend", "index.html", "xterm", "ui"])
    has_docker = any(k in research_content.lower() for k in ["dockerfile", "docker", "container"])
    has_websocket = any(k in research_content.lower() for k in ["websocket", "ws://", "wss://"])
    has_pty = any(k in research_content.lower() for k in ["pty", "terminal", "tty"])

    # Phase 1: Setup (always first)
    setup_files = []
    if "requirements.txt" in research_content or has_backend:
        setup_files.append(("requirements.txt", "Python dependencies"))
    if "package.json" in research_content:
        setup_files.append(("package.json", "Node dependencies"))
    phases.append({
        "name": "Setup",
        "files": setup_files,
        "success_criteria": ["Dependencies installed", "Project structure created"],
        "deliverables": [f[0] for f in setup_files],
    })

    # Phase 2: Backend (if detected)
    if has_backend:
        backend_files = [("main.py", "Backend server with API endpoints")]
        if has_websocket:
            backend_files[0] = ("main.py", "Backend server with WebSocket support")
        if has_pty:
            backend_files[0] = ("main.py", "Backend with PTY wrapper and WebSocket streaming")
        phases.append({
            "name": "Backend",
            "files": backend_files,
            "success_criteria": ["Server starts without errors", "API endpoints respond", "WebSocket connects" if has_websocket else None],
            "deliverables": [f[0] for f in backend_files],
        })
        files_needed.extend(backend_files)

    # Phase 3: Frontend (if detected)
    if has_frontend:
        frontend_files = [("static/index.html", "Frontend UI")]
        if has_websocket:
            frontend_files[0] = ("static/index.html", "Frontend with WebSocket terminal")
        phases.append({
            "name": "Frontend",
            "files": frontend_files,
            "success_criteria": ["Page loads in browser", "UI is responsive", "Terminal connects" if has_websocket else None],
            "deliverables": [f[0] for f in frontend_files],
        })
        files_needed.extend(frontend_files)

    # Phase 4: Integration
    phases.append({
        "name": "Integration",
        "files": [],
        "success_criteria": ["Frontend connects to backend", "Full workflow works end-to-end"],
        "deliverables": ["Verified integration"],
    })

    # Phase 5: Testing
    phases.append({
        "name": "Testing",
        "files": [],
        "success_criteria": ["Manual testing complete", "Edge cases verified"],
        "deliverables": ["Test results documented"],
    })

    # Phase 6: Deployment (if Docker detected)
    if has_docker:
        deploy_files = [("Dockerfile", "Container definition"), ("docker-compose.yml", "Orchestration")]
        phases.append({
            "name": "Deployment",
            "files": deploy_files,
            "success_criteria": ["Container builds", "App runs in container"],
            "deliverables": [f[0] for f in deploy_files],
        })
        files_needed.extend(deploy_files)

    return phases, files_needed


def _is_modification_task(spec) -> bool:
    """Detect modification task vs greenfield project."""
    if not spec or not getattr(spec, 'steps', None):
        return False
    modification_actions = {"learn", "modify", "refactor", "delete", "verify"}
    return any(s.action in modification_actions for s in spec.steps)


def _build_phase(name: str, steps: list) -> dict:
    """Build phase dict from spec steps."""
    files = [(t, s.description[:50]) for s in steps for t in s.targets]
    return {
        "name": name,
        "files": files,
        "success_criteria": [s.verification for s in steps if s.verification],
        "deliverables": list(dict.fromkeys(t for s in steps for t in s.targets)),
        "steps": steps,
        "step_ids": [s.id for s in steps],
        "is_complete": all(s.status == "completed" for s in steps),
    }


def _phases_from_spec(spec) -> tuple:
    """Extract phases from spec steps instead of guessing from research."""
    if not spec or not spec.steps:
        return [], []

    phases = []
    files_needed = []

    action_to_phase = {
        "learn": "Understand",
        "modify": "Implement",
        "refactor": "Refactor",
        "create": "Create",
        "delete": "Cleanup",
        "verify": "Verify",
    }

    # Group consecutive same-action steps
    current_type = None
    current_steps = []

    for step in spec.steps:
        phase_type = action_to_phase.get(step.action, "Execute")

        if phase_type != current_type and current_steps:
            phases.append(_build_phase(current_type, current_steps))
            current_steps = []

        current_type = phase_type
        current_steps.append(step)

        for target in step.targets:
            files_needed.append((target, step.description[:50]))

    if current_steps:
        phases.append(_build_phase(current_type, current_steps))

    return phases, files_needed


def _generate_progress_bar(completed: int, total: int, width: int = 25) -> str:
    """Generate a text progress bar."""
    if total == 0:
        return "[" + "░" * width + "] 0/0"
    filled = int(width * completed / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {completed}/{total}"


def _check_phase_completion(project_path: str, phase: dict) -> tuple[bool, list[str]]:
    """
    Check if a phase's deliverables exist.
    Returns (is_complete, list_of_existing_files).
    """
    existing = []
    for fname, _ in phase.get('files', []):
        fpath = os.path.join(project_path, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
            existing.append(fname)

    # Phase is complete if all files exist (or no files required)
    if not phase.get('files'):
        return False, []  # No files = not auto-complete
    is_complete = len(existing) == len(phase['files'])
    return is_complete, existing


def update_session_files(project_path: str, project_name: str = None, completed_phase: int = None, activity: str = None):
    """
    Update session-persistent files based on current file state.

    Call this when:
    - A deliverable is created
    - A phase is marked complete
    - Work is done on the project

    Args:
        project_path: Path to project root
        project_name: Project name (auto-detected if None)
        completed_phase: Phase number just completed (1-indexed)
        activity: Description of last activity
    """
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    # Auto-detect project name from STATE.md if not provided
    state_path = os.path.join(project_path, "STATE.md")
    if not os.path.exists(state_path):
        print(f"[EriRPG] No STATE.md found at {project_path}", file=sys.stderr)
        return False

    with open(state_path) as f:
        state_content = f.read()

    # Extract current info from STATE.md
    goal = ""
    spec_id = ""
    for line in state_content.split('\n'):
        if line.startswith("**Goal:**"):
            goal = line.replace("**Goal:**", "").strip()
        elif line.startswith("**Project:**"):
            project_name = project_name or line.replace("**Project:**", "").strip()
        elif line.startswith("**Spec ID:**"):
            spec_id = line.replace("**Spec ID:**", "").strip()

    if not project_name or not goal:
        print(f"[EriRPG] Could not parse STATE.md", file=sys.stderr)
        return False

    # Try to load spec for spec-aware phase detection
    spec = None
    spec_dir = os.path.join(project_path, ".eri-rpg", "specs")
    if os.path.exists(spec_dir):
        from erirpg.spec import Spec
        specs = sorted([
            os.path.join(spec_dir, f)
            for f in os.listdir(spec_dir)
            if f.endswith(".yaml")
        ], key=os.path.getmtime, reverse=True)
        if specs:
            try:
                spec = Spec.load(specs[0])
            except Exception:
                pass

    # Use spec-aware phase detection for modification tasks
    if spec and _is_modification_task(spec):
        phases, files_needed = _phases_from_spec(spec)
    else:
        # Fallback for greenfield projects
        research_path = os.path.join(project_path, ".eri-rpg", "research", "RESEARCH.md")
        research_content = ""
        if os.path.exists(research_path):
            with open(research_path) as f:
                research_content = f.read()
        phases, files_needed = _parse_research_for_phases(research_content, goal)

    total_phases = len(phases)

    # Check which phases are complete based on file existence
    completed_phases = 0
    current_phase_idx = 0
    for i, phase in enumerate(phases):
        is_complete, existing_files = _check_phase_completion(project_path, phase)
        phase['is_complete'] = is_complete
        phase['existing_files'] = existing_files
        if is_complete:
            completed_phases += 1
            current_phase_idx = i + 1
        elif current_phase_idx == i:
            break

    # Handle manual phase completion (for phases without file deliverables)
    if completed_phase and completed_phase > completed_phases:
        for i in range(completed_phases, min(completed_phase, total_phases)):
            phases[i]['is_complete'] = True
        completed_phases = completed_phase
        current_phase_idx = completed_phase

    current_phase = phases[current_phase_idx] if current_phase_idx < len(phases) else phases[-1] if phases else {"name": "Complete"}

    # Determine status
    if completed_phases >= total_phases:
        status_text = "Complete"
        current_phase = {"name": "Complete"}
    elif completed_phases > 0:
        status_text = "In Progress"
    else:
        status_text = "Not Started"

    activity = activity or f"Phase {completed_phases} complete" if completed_phases > 0 else "Project initialized"

    # === Update STATE.md ===
    state_lines = [
        "# Project State",
        "",
        "## Project Reference",
        "",
        f"**Goal:** {goal}",
        f"**Project:** {project_name}",
        f"**Spec ID:** {spec_id}",
        f"**Created:** {state_content.split('**Created:**')[1].split(chr(10))[0].strip() if '**Created:**' in state_content else date_str}",
        "",
        "## Current Position",
        "",
        f"Phase: {current_phase_idx + 1 if current_phase_idx < total_phases else total_phases} of {total_phases} - {current_phase['name']}",
        "Plan: 1 of 1",
        f"Status: {status_text}",
        f"Last activity: {date_str} - {activity}",
        "",
        f"Progress: {_generate_progress_bar(completed_phases, total_phases)} phases complete",
        "",
        "## Phase Structure",
        "",
        "| Phase | Name | Status |",
        "|-------|------|--------|",
    ]

    for i, phase in enumerate(phases, 1):
        if phase.get('is_complete'):
            status = "Complete ✅"
        elif i == current_phase_idx + 1:
            status = "**Current**"
        else:
            status = "Not Started"
        state_lines.append(f"| {i} | {phase['name']} | {status} |")

    state_lines.extend([
        "",
        "## Session Continuity",
        "",
        f"Last session: {date_str}",
        f"Stopped at: {activity}",
        f"Resume: `/eri:execute {project_name}`" if status_text != "Complete" else "Resume: N/A - Project complete",
        "",
    ])

    with open(state_path, "w") as f:
        f.write("\n".join(state_lines))

    # === Update ROADMAP.md ===
    roadmap_path = os.path.join(project_path, "ROADMAP.md")
    roadmap_lines = [
        f"# Roadmap: {project_name}",
        "",
        "## Overview",
        "",
        f"**Goal:** {goal}",
        "",
        "---",
        "",
        "## Phases",
        "",
    ]

    for i, phase in enumerate(phases, 1):
        roadmap_lines.append(f"### Phase {i}: {phase['name']}")
        roadmap_lines.append("")

        if phase['files']:
            roadmap_lines.append("**Deliverables:**")
            for fname, desc in phase['files']:
                check = "x" if fname in phase.get('existing_files', []) else " "
                roadmap_lines.append(f"- [{check}] `{fname}` - {desc}")
            roadmap_lines.append("")

        if phase.get('success_criteria'):
            roadmap_lines.append("**Success Criteria:**")
            for criterion in phase['success_criteria']:
                if criterion:
                    check = "✅" if phase.get('is_complete') else ""
                    roadmap_lines.append(f"1. {criterion} {check}")
            roadmap_lines.append("")

        if phase.get('is_complete'):
            roadmap_lines.append("**Status:** Complete ✅")
        elif i == current_phase_idx + 1:
            roadmap_lines.append("**Status:** In Progress")
        else:
            roadmap_lines.append("**Status:** Not Started")
        roadmap_lines.append("")
        roadmap_lines.append("---")
        roadmap_lines.append("")

    roadmap_lines.extend([
        "## Progress",
        "",
        "| Phase | Status | Deliverables |",
        "|-------|--------|--------------|",
    ])

    for i, phase in enumerate(phases, 1):
        deliverables = ", ".join(phase.get('deliverables', [])) if phase.get('deliverables') else "N/A"
        if phase.get('is_complete'):
            status = "Complete ✅"
        elif i == current_phase_idx + 1:
            status = "In Progress"
        else:
            status = "Not Started"
        roadmap_lines.append(f"| {i}. {phase['name']} | {status} | {deliverables} |")

    roadmap_lines.extend([
        "",
        "---",
        "",
        f"*Updated: {date_str}*",
        "",
    ])

    with open(roadmap_path, "w") as f:
        f.write("\n".join(roadmap_lines))

    # === Update TASKS.md ===
    tasks_path = os.path.join(project_path, "TASKS.md")

    # Build completed tasks list
    completed_tasks = []
    for i, phase in enumerate(phases, 1):
        if phase.get('is_complete'):
            completed_tasks.append(f"- [x] **Phase {i}: {phase['name']}**")
            for fname, _ in phase.get('files', []):
                completed_tasks.append(f"  - [x] Created `{fname}`")

    # Build active/backlog tasks
    active_tasks = []
    backlog_tasks = []

    for i, phase in enumerate(phases, 1):
        if phase.get('is_complete'):
            continue
        elif i == current_phase_idx + 1:
            active_tasks.append(f"- [ ] **Phase {i}: {phase['name']}**")
            for fname, desc in phase.get('files', []):
                active_tasks.append(f"  - [ ] Create `{fname}` - {desc}")
        else:
            backlog_tasks.append(f"- [ ] **Phase {i}: {phase['name']}**")
            for fname, desc in phase.get('files', []):
                backlog_tasks.append(f"  - [ ] Create `{fname}` - {desc}")

    tasks_lines = [
        f"# {project_name} Development Tasks",
        "",
        "**Read this file at the start of each session to restore context.**",
        "",
        f"Last updated: {date_str}",
        "",
        "---",
        "",
        "## Active Tasks",
        "",
    ]

    if active_tasks:
        tasks_lines.extend(active_tasks)
    else:
        tasks_lines.append("*None - Project complete*" if status_text == "Complete" else "*None*")

    tasks_lines.extend([
        "",
        "---",
        "",
        "## Backlog",
        "",
    ])

    if backlog_tasks:
        tasks_lines.extend(backlog_tasks)
    else:
        tasks_lines.append("*None*" if status_text == "Complete" else "*None remaining*")

    tasks_lines.extend([
        "",
        "---",
        "",
        "## Completed",
        "",
        f"### {date_str}",
        "",
    ])

    if completed_tasks:
        tasks_lines.extend(completed_tasks)
    else:
        tasks_lines.append("- [x] Project initialized")

    tasks_lines.extend([
        "",
        "---",
        "",
        f"Resume: `/eri:execute {project_name}`" if status_text != "Complete" else "*Project complete*",
        "",
    ])

    with open(tasks_path, "w") as f:
        f.write("\n".join(tasks_lines))

    return True


def _generate_session_files(project_path: str, project_name: str, goal: str, spec, knowledge):
    """
    Generate all session-persistent files for /clear survival.

    Session-persistent structure matching OneTrainer/.planning/:
    - STATE.md - Current position, progress, accumulated context
    - ROADMAP.md - Phases with success criteria and deliverables
    - TASKS.md - Active tasks, backlog, handoff notes
    - CONTEXT.md - Decisions and research summary
    """
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%Y-%m-%d %H:%M')

    # Load research if available
    research_path = os.path.join(project_path, ".eri-rpg", "research", "RESEARCH.md")
    research_content = ""
    if os.path.exists(research_path):
        with open(research_path) as f:
            research_content = f.read()

    # Load discussion if available
    knowledge_path = os.path.join(project_path, ".eri-rpg", "knowledge.json")
    discussions = {}
    decisions = []
    if os.path.exists(knowledge_path):
        with open(knowledge_path) as f:
            kdata = json.load(f)
            discussions = kdata.get("discussions", {})
            decisions = kdata.get("user_decisions", [])

    # Find discussion for this goal
    discussion = None
    for d in discussions.values():
        if goal.lower() in d.get("goal", "").lower():
            discussion = d
            break

    # Use spec-aware phase detection for modification tasks
    if spec and _is_modification_task(spec):
        phases, files_needed = _phases_from_spec(spec)
    else:
        # Fallback for greenfield projects
        phases, files_needed = _parse_research_for_phases(research_content, goal)

    total_phases = len(phases)

    # Check which phases are already complete
    completed_phases = 0
    current_phase_idx = 0
    for i, phase in enumerate(phases):
        is_complete, existing_files = _check_phase_completion(project_path, phase)
        phase['is_complete'] = is_complete
        phase['existing_files'] = existing_files
        if is_complete:
            completed_phases += 1
            current_phase_idx = i + 1  # Move to next phase
        elif current_phase_idx == i:
            # This is the current phase (first incomplete one)
            break

    # === STATE.md ===
    current_phase = phases[current_phase_idx] if current_phase_idx < len(phases) else phases[-1] if phases else {"name": "Setup"}
    status_text = "Complete ✅" if completed_phases == total_phases else "In Progress" if completed_phases > 0 else "Not Started"

    state_lines = [
        "# Project State",
        "",
        "## Project Reference",
        "",
        f"**Goal:** {goal}",
        f"**Project:** {project_name}",
        f"**Spec ID:** {spec.id}",
        f"**Created:** {time_str}",
        "",
        "## Current Position",
        "",
        f"Phase: {current_phase_idx + 1} of {total_phases} - {current_phase['name']}",
        "Plan: 1 of 1",
        f"Status: {status_text}",
        f"Last activity: {date_str} - Project initialized",
        "",
        f"Progress: {_generate_progress_bar(completed_phases, total_phases)} phases complete",
        "",
        "## Performance Metrics",
        "",
        "**Velocity:**",
        "- Plans completed: 0",
        "- Average duration: N/A",
        "",
        "## Accumulated Context",
        "",
        "### Decisions",
        "",
    ]

    if decisions:
        for d in decisions[-10:]:
            state_lines.append(f"- [{d.get('timestamp', date_str)[:10]}]: {d.get('context', 'Unknown')} - {d.get('choice', 'Unknown')}")
    else:
        state_lines.append("_(None yet)_")

    state_lines.extend([
        "",
        "### Key Artifacts",
        "",
        "_(Created during execution)_",
        "",
        "## Phase Structure",
        "",
        "| Phase | Name | Status |",
        "|-------|------|--------|",
    ])

    for i, phase in enumerate(phases, 1):
        if phase.get('is_complete'):
            status = "Complete ✅"
        elif i == current_phase_idx + 1:
            status = "**Current**"
        else:
            status = "Not Started"
        state_lines.append(f"| {i} | {phase['name']} | {status} |")

    # Add Spec Steps table for modification tasks
    if spec and spec.steps:
        state_lines.extend([
            "",
            "## Spec Steps",
            "",
            "| Step | Action | Status | Targets |",
            "|------|--------|--------|---------|",
        ])
        status_icons = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}
        for step in spec.steps:
            icon = status_icons.get(step.status, "?")
            targets = ", ".join(step.targets[:2]) or "-"
            state_lines.append(f"| {step.id} | {step.action} | {icon} | `{targets}` |")

    state_lines.extend([
        "",
        "## Session Continuity",
        "",
        f"Last session: {date_str}",
        "Stopped at: Project initialized",
        f"Resume: `/eri:execute {project_name}`",
        "",
    ])

    with open(os.path.join(project_path, "STATE.md"), "w") as f:
        f.write("\n".join(state_lines))

    # === ROADMAP.md ===
    roadmap_lines = [
        f"# Roadmap: {project_name}",
        "",
        "## Overview",
        "",
        f"**Goal:** {goal}",
        "",
        "---",
        "",
        "## Phases",
        "",
    ]

    for i, phase in enumerate(phases, 1):
        roadmap_lines.append(f"### Phase {i}: {phase['name']}")
        roadmap_lines.append("")

        if phase['files']:
            roadmap_lines.append("**Deliverables:**")
            for fname, desc in phase['files']:
                roadmap_lines.append(f"- [ ] `{fname}` - {desc}")
            roadmap_lines.append("")

        # Show spec steps with verification for modification tasks
        if phase.get("steps"):
            roadmap_lines.append("**Steps:**")
            for step in phase["steps"]:
                check = "x" if step.status == "completed" else " "
                roadmap_lines.append(f"- [{check}] `{step.id}`: {step.description}")
                if step.verification:
                    roadmap_lines.append(f"  - Verify: {step.verification}")
            roadmap_lines.append("")

        if phase.get('success_criteria'):
            roadmap_lines.append("**Success Criteria:**")
            for criterion in phase['success_criteria']:
                if criterion:
                    roadmap_lines.append(f"1. {criterion}")
            roadmap_lines.append("")

        roadmap_lines.append("**Status:** Not Started")
        roadmap_lines.append("")
        roadmap_lines.append("---")
        roadmap_lines.append("")

    roadmap_lines.extend([
        "## Progress",
        "",
        "| Phase | Status | Deliverables |",
        "|-------|--------|--------------|",
    ])

    for i, phase in enumerate(phases, 1):
        deliverables = ", ".join(phase['deliverables']) if phase['deliverables'] else "N/A"
        roadmap_lines.append(f"| {i}. {phase['name']} | Not Started | {deliverables} |")

    roadmap_lines.extend([
        "",
        "---",
        "",
        "## Dependency Graph",
        "",
        "```",
    ])

    for i, phase in enumerate(phases, 1):
        arrow = "    ↓" if i < len(phases) else ""
        roadmap_lines.append(f"Phase {i}: {phase['name']}")
        if arrow:
            roadmap_lines.append(arrow)

    roadmap_lines.extend([
        "```",
        "",
        "---",
        "",
        f"*Generated: {time_str}*",
        "",
    ])

    with open(os.path.join(project_path, "ROADMAP.md"), "w") as f:
        f.write("\n".join(roadmap_lines))

    # === TASKS.md ===
    tasks_lines = [
        f"# {project_name} Development Tasks",
        "",
        "**Read this file at the start of each session to restore context.**",
        "",
        f"Last updated: {date_str}",
        "",
        "---",
        "",
        "## Active Tasks",
        "",
        "*Currently in progress*",
        "",
    ]

    # Derive tasks from spec steps for modification tasks
    active_spec_tasks = []
    backlog_spec_tasks = []
    if spec and spec.steps:
        found_current = False
        for step in spec.steps:
            if step.status == "in_progress":
                active_spec_tasks.append(f"- [ ] **{step.id}**: {step.description}")
                found_current = True
            elif step.status == "pending" and not found_current:
                active_spec_tasks.append(f"- [ ] **{step.id}**: {step.description}")
                found_current = True
            elif step.status == "pending":
                backlog_spec_tasks.append(f"- [ ] **{step.id}**: {step.description}")

    # Create tasks from phases or spec steps
    if active_spec_tasks:
        tasks_lines.extend(active_spec_tasks)
    elif phases:
        first_phase = phases[0]
        if first_phase['files']:
            for fname, desc in first_phase['files']:
                tasks_lines.append(f"- [ ] **Create {fname}** - {desc}")
        else:
            tasks_lines.append(f"- [ ] **Complete Phase 1: {first_phase['name']}**")
    else:
        tasks_lines.append("_(None yet)_")

    tasks_lines.extend([
        "",
        "---",
        "",
        "## Backlog",
        "",
        "### High Priority",
        "",
    ])

    # Add backlog from spec steps or phases
    if backlog_spec_tasks:
        tasks_lines.extend(backlog_spec_tasks)
    else:
        # Add remaining phases as backlog
        for i, phase in enumerate(phases[1:], 2):
            tasks_lines.append(f"- [ ] **Phase {i}: {phase['name']}**")
            for fname, desc in phase.get('files', []):
                tasks_lines.append(f"  - [ ] Create `{fname}` - {desc}")

    tasks_lines.extend([
        "",
        "### Medium Priority",
        "",
        "- [ ] Add error handling",
        "- [ ] Add logging",
        "",
        "### Low Priority",
        "",
        "- [ ] Documentation",
        "- [ ] Performance optimization",
        "",
        "---",
        "",
        "## Completed",
        "",
        f"### {date_str}",
        "",
        "- [x] Project initialized",
        "- [x] Research completed",
        "- [x] Roadmap generated",
        "",
        "---",
        "",
        "## Session Handoff Notes",
        "",
        "*Context for the next session:*",
        "",
        f"- **Goal:** {goal}",
        f"- **Current Phase:** 1 - {phases[0]['name'] if phases else 'Setup'}",
        "- **Next Action:** Start implementing first deliverable",
        "",
        "### Key Files",
        "",
    ])

    for fname, desc in files_needed[:5]:
        tasks_lines.append(f"- `{fname}` - {desc}")

    tasks_lines.extend([
        "",
        "---",
        "",
        "## How to Use This File",
        "",
        "1. **Start of session**: Read this file to see what's in progress",
        "2. **During work**: Move tasks from Backlog → Active as you start them",
        "3. **End of session**: Update completed items, add handoff notes",
        f"4. **Resume command**: `/eri:execute {project_name}`",
        "",
    ])

    with open(os.path.join(project_path, "TASKS.md"), "w") as f:
        f.write("\n".join(tasks_lines))

    # === CONTEXT.md (enhanced) ===
    context_lines = [
        f"# {project_name} - Context",
        "",
        f"**Goal:** {goal}",
        f"**Generated:** {time_str}",
        "",
        "---",
        "",
        "## Discussion Decisions",
        "",
    ]

    if discussion and discussion.get("answers"):
        for q, a in discussion["answers"].items():
            context_lines.append(f"### {q}")
            context_lines.append(f"{a}")
            context_lines.append("")
    else:
        context_lines.append("_(No discussion recorded)_")
        context_lines.append("")

    if decisions:
        context_lines.extend([
            "---",
            "",
            "## Logged Decisions",
            "",
            "| Date | Context | Choice | Rationale |",
            "|------|---------|--------|-----------|",
        ])
        for d in decisions[-10:]:
            date = d.get('timestamp', '')[:10] if d.get('timestamp') else date_str
            ctx = d.get('context', 'Unknown')
            choice = d.get('choice', 'Unknown')
            rationale = d.get('rationale', '-')
            context_lines.append(f"| {date} | {ctx} | {choice} | {rationale} |")
        context_lines.append("")

    context_lines.extend([
        "---",
        "",
        "## Research Summary",
        "",
    ])

    if os.path.exists(research_path):
        context_lines.append(f"Full research: `.eri-rpg/research/RESEARCH.md`")
        context_lines.append("")
        # Extract key points from research - try multiple headers
        stack_headers = ["## Stack Recommendations", "## Recommended Stack", "## Stack"]
        for header in stack_headers:
            if header in research_content:
                stack_start = research_content.find(header)
                stack_end = research_content.find("\n## ", stack_start + len(header))
                if stack_end == -1:
                    stack_end = research_content.find("\n---", stack_start)
                if stack_end == -1:
                    stack_end = len(research_content)
                stack_section = research_content[stack_start:stack_end].strip()
                context_lines.append("### Stack (from research)")
                context_lines.append("")
                for line in stack_section.split("\n")[1:15]:  # First 15 lines after header
                    if line.strip() and line.strip() != "---":  # Skip separator lines
                        context_lines.append(line)
                context_lines.append("")
                break
    else:
        context_lines.append("No research conducted")
        context_lines.append("")

    context_lines.extend([
        "---",
        "",
        f"*Resume: `/eri:execute {project_name}`*",
        "",
    ])

    with open(os.path.join(project_path, "CONTEXT.md"), "w") as f:
        f.write("\n".join(context_lines))


def register(cli):
    """Register goal commands with CLI."""
    from erirpg.registry import Registry
    from erirpg.indexer import get_or_load_graph
    from erirpg.memory import load_knowledge

    @cli.command("goal-plan")
    @click.argument("project")
    @click.argument("goal")
    @click.option("-o", "--output", default=None, help="Output spec file path")
    @tier_required("full")
    def goal_plan(project: str, goal: str, output: str):
        """Generate a spec from a goal.

        Creates a structured spec with ordered steps from a natural language goal.
        This is the entry point for spec-driven execution.

        \b
        Example:
            eri-rpg goal-plan eritrainer "add logging to config.py"
            eri-rpg goal-plan myproject "refactor auth module" -o spec.yaml
        """
        from erirpg.spec import Spec
        from erirpg.planner import Planner

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            click.echo(f"\nAdd it first: eri-rpg add {project} /path/to/project")
            sys.exit(1)

        # Load graph and knowledge for intelligent planning
        graph = None
        knowledge = None
        try:
            graph = get_or_load_graph(proj)
        except Exception as e:
            pass

        try:
            knowledge = load_knowledge(proj.path, project)
        except Exception as e:
            pass

        # Generate spec
        planner = Planner(project, graph, knowledge)
        spec = planner.plan(goal)

        # Save spec
        if output:
            spec_path = output
        else:
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            os.makedirs(spec_dir, exist_ok=True)
            spec_path = os.path.join(spec_dir, f"{spec.id}.yaml")

        spec.save(spec_path)

        # Generate all session-persistent files
        _generate_session_files(proj.path, project, goal, spec, knowledge)

        click.echo(f"Generated:")
        click.echo(f"  - {spec_path}")
        click.echo(f"  - STATE.md (current position, progress)")
        click.echo(f"  - ROADMAP.md (phases with deliverables)")
        click.echo(f"  - TASKS.md (active tasks, backlog)")
        click.echo(f"  - CONTEXT.md (decisions, research)")
        click.echo("")
        click.echo(spec.format_status())
        click.echo("")
        click.echo(f"Execute with: eri-rpg goal-run {project}")

    @cli.command("goal-run")
    @click.argument("project")
    @click.option("--spec", "spec_path", default=None, help="Specific spec file to run")
    @click.option("--resume", "resume_run", is_flag=True, help="Resume incomplete run")
    def goal_run(project: str, spec_path: str, resume_run: bool):
        """Execute a spec for a project.

        Runs the latest spec (or specified spec) step by step.
        Agent refuses to proceed if verification fails.

        \b
        Example:
            eri-rpg goal-run eritrainer
            eri-rpg goal-run myproject --spec ./spec.yaml
            eri-rpg goal-run myproject --resume
        """
        from erirpg.spec import Spec
        from erirpg.agent import Agent

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check for resume
        if resume_run:
            agent = Agent.resume(proj.path)
            if agent:
                click.echo(f"Resumed run: {agent._run.id if agent._run else 'unknown'}")
                click.echo("")
                click.echo(agent.get_spec_status())
                return
            else:
                click.echo("No incomplete run to resume.")

        # Load spec
        if spec_path:
            spec = Spec.load(spec_path)
        else:
            # Find latest spec
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            if not os.path.exists(spec_dir):
                click.echo("No specs found.")
                click.echo(f"\nGenerate one: eri-rpg goal-plan {project} \"<goal>\"")
                sys.exit(1)

            specs = sorted([
                os.path.join(spec_dir, f)
                for f in os.listdir(spec_dir)
                if f.endswith(".yaml")
            ], key=os.path.getmtime, reverse=True)

            if not specs:
                click.echo("No specs found.")
                click.echo(f"\nGenerate one: eri-rpg goal-plan {project} \"<goal>\"")
                sys.exit(1)

            spec = Spec.load(specs[0])
            click.echo(f"Using latest spec: {specs[0]}")
            click.echo("")

        # Create agent from spec
        agent = Agent.from_new_spec(spec, proj.path)

        click.echo(f"Started run: {agent._run.id if agent._run else 'new'}")
        click.echo("")
        click.echo(agent.get_spec_status())
        click.echo("")
        click.echo("Use the Agent API in Claude Code:")
        click.echo("  agent = Agent.resume(project_path)")
        click.echo("  step = agent.next_step()")
        click.echo("  # Execute step")
        click.echo("  if agent.verify_step():")
        click.echo("      agent.complete_step()")

    @cli.command("goal-update")
    @click.argument("project")
    @click.option("--phase", type=int, default=None, help="Mark phase N as complete")
    @click.option("--activity", default=None, help="Description of last activity")
    def goal_update(project: str, phase: int, activity: str):
        """Update session files based on current state.

        Auto-detects completed phases from existing files.
        Use --phase to manually mark a phase complete (for phases without file deliverables).

        \b
        Example:
            eri-rpg goal-update myproject
            eri-rpg goal-update myproject --phase 4 --activity "Integration tested"
        """
        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        if update_session_files(proj.path, project, phase, activity):
            click.echo(f"Updated: STATE.md, ROADMAP.md, TASKS.md")

            # Show current status
            state_path = os.path.join(proj.path, "STATE.md")
            if os.path.exists(state_path):
                with open(state_path) as f:
                    for line in f:
                        if "Progress:" in line or "Phase:" in line or "Status:" in line:
                            click.echo(line.strip())
        else:
            click.echo("Failed to update session files", err=True)
            sys.exit(1)

    @cli.command("goal-status")
    @click.argument("project")
    def goal_status(project: str):
        """Show spec execution status for a project.

        Displays progress, current step, and any blockers.

        \b
        Example:
            eri-rpg goal-status eritrainer
        """
        from erirpg.agent import Agent

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Try to resume existing run
        agent = Agent.resume(proj.path)

        if not agent:
            click.echo(f"No active run for {project}.")
            click.echo("")

            # Check for specs
            spec_dir = os.path.join(proj.path, ".eri-rpg", "specs")
            if os.path.exists(spec_dir):
                specs = [f for f in os.listdir(spec_dir) if f.endswith(".yaml")]
                if specs:
                    click.echo(f"Found {len(specs)} spec(s).")
                    click.echo(f"Start with: eri-rpg goal-run {project}")
                else:
                    click.echo(f"Generate a spec: eri-rpg goal-plan {project} \"<goal>\"")
            else:
                click.echo(f"Generate a spec: eri-rpg goal-plan {project} \"<goal>\"")
            return

        click.echo(agent.get_spec_status())
