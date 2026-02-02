"""
Coder Commands - CLI operations for /coder:* skills.

These commands provide the backend logic for eri-coder workflow.
The .md skill files tell Claude Code the workflow; these .py modules
do the actual git ops, file ops, token counting, and state tracking.

Commands:
- coder-resume: Restore from last session
- coder-progress: Show current position and metrics
- coder-quick: Ad-hoc task management
- coder-debug: Debug session management
- coder-settings: Configure workflow preferences
- coder-help: Command reference
- coder-add-todo: Capture ideas for later
- coder-list-phase-assumptions: Show planning assumptions
- coder-plan-milestone-gaps: Create phases for gaps
- coder-rollback: Undo execution via git
- coder-diff: Show changes since checkpoint
- coder-cost: Estimate tokens and cost
- coder-metrics: Track execution metrics
- coder-history: Execution history
- coder-split: Break plan into smaller plans
- coder-merge: Combine plans
- coder-replay: Re-run phase/plan
- coder-compare: Compare approaches/branches
- coder-learn: Pattern extraction to knowledge
- coder-template: File scaffolding
- coder-handoff: Generate context documentation
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click


# ============================================================================
# Utilities
# ============================================================================

def is_coder_planning_dir(path: Path) -> bool:
    """Check if a .planning directory has coder workflow artifacts."""
    if not path.is_dir():
        return False
    # Coder workflow has phases/, STATE.md, or ROADMAP.md
    return (
        (path / "phases").is_dir() or
        (path / "STATE.md").exists() or
        (path / "ROADMAP.md").exists()
    )


def get_planning_dir() -> Path:
    """Get the .planning directory for current project.

    Search order:
    1. Check cwd for coder .planning/ (with phases/STATE.md/ROADMAP.md)
    2. Walk UP from cwd looking for coder .planning/
    3. Walk DOWN one level from cwd looking for coder .planning/
    4. Check registered project path from ~/.eri-rpg/state.json
    5. Fallback: any .planning/ in cwd or parents
    """
    cwd = Path.cwd()

    # 1. Check cwd directly for coder workflow
    if is_coder_planning_dir(cwd / ".planning"):
        return cwd / ".planning"

    # 2. Walk up looking for coder .planning/
    check = cwd
    while check != check.parent:  # Stop at filesystem root
        if is_coder_planning_dir(check / ".planning"):
            return check / ".planning"
        check = check.parent

    # 3. Walk down one level from cwd
    if cwd.is_dir():
        for subdir in cwd.iterdir():
            if subdir.is_dir() and is_coder_planning_dir(subdir / ".planning"):
                return subdir / ".planning"

    # 4. Check registered project from state
    state_path = Path.home() / ".eri-rpg" / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            active = state.get("active_project")
            if active:
                registry_path = Path.home() / ".eri-rpg" / "registry.json"
                if registry_path.exists():
                    registry = json.loads(registry_path.read_text())
                    projects = registry.get("projects", {})
                    if active in projects:
                        proj_path = Path(projects[active].get("path", ""))
                        if proj_path.exists():
                            # Check project root
                            if is_coder_planning_dir(proj_path / ".planning"):
                                return proj_path / ".planning"
                            # Check one level down (e.g., serenity/desktop)
                            for subdir in proj_path.iterdir():
                                if subdir.is_dir() and is_coder_planning_dir(subdir / ".planning"):
                                    return subdir / ".planning"
        except (json.JSONDecodeError, KeyError):
            pass

    # 5. Fallback - any .planning/ in cwd
    if (cwd / ".planning").is_dir():
        return cwd / ".planning"

    return cwd / ".planning"


def ensure_planning_dir() -> Path:
    """Ensure .planning directory exists."""
    planning = get_planning_dir()
    planning.mkdir(parents=True, exist_ok=True)
    return planning


def load_json_file(path: Path, default: dict = None) -> dict:
    """Load JSON file or return default."""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return default or {}


def save_json_file(path: Path, data: dict) -> None:
    """Save data to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_md_frontmatter(path: Path) -> dict:
    """Load YAML frontmatter from markdown file."""
    if not path.exists():
        return {}
    content = path.read_text()
    if not content.startswith("---"):
        return {}
    try:
        import re
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            # Simple YAML parsing for frontmatter
            frontmatter = {}
            for line in match.group(1).split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"\'')
            return frontmatter
    except Exception:
        pass
    return {}


def run_git_command(args: list[str], capture: bool = True) -> tuple[int, str]:
    """Run a git command and return (returncode, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=capture,
            text=True,
            cwd=Path.cwd()
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def get_git_status() -> dict:
    """Get current git status."""
    code, output = run_git_command(["status", "--porcelain"])
    dirty = bool(output.strip()) if code == 0 else True

    code, branch = run_git_command(["branch", "--show-current"])
    branch = branch.strip() if code == 0 else "unknown"

    code, commit = run_git_command(["rev-parse", "--short", "HEAD"])
    commit = commit.strip() if code == 0 else "unknown"

    return {
        "dirty": dirty,
        "branch": branch,
        "commit": commit,
        "changes": output.strip().split('\n') if output.strip() else []
    }


def count_files_in_dir(directory: Path, pattern: str = "*") -> int:
    """Count files matching pattern in directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


# ============================================================================
# Command: coder-resume
# ============================================================================

def get_resume_state() -> dict:
    """Get resume state from various sources."""
    planning = get_planning_dir()

    # Check for RESUME.md
    resume_path = planning / "RESUME.md"
    if resume_path.exists():
        fm = load_md_frontmatter(resume_path)
        return {
            "source": "RESUME.md",
            "exists": True,
            "paused_at": fm.get("paused_at"),
            "phase": fm.get("phase"),
            "plan": fm.get("plan"),
            "task": fm.get("task"),
            "reason": fm.get("reason"),
            "content": resume_path.read_text()
        }

    # Check for STATE.md
    state_path = planning / "STATE.md"
    if state_path.exists():
        fm = load_md_frontmatter(state_path)
        return {
            "source": "STATE.md",
            "exists": True,
            "phase": fm.get("current_phase"),
            "status": fm.get("status"),
            "content": state_path.read_text()
        }

    # Check for checkpoints
    phases_dir = planning / "phases"
    if phases_dir.exists():
        for phase_dir in sorted(phases_dir.iterdir()):
            if phase_dir.is_dir():
                checkpoint = phase_dir / "CHECKPOINT.md"
                if checkpoint.exists():
                    fm = load_md_frontmatter(checkpoint)
                    return {
                        "source": "CHECKPOINT.md",
                        "exists": True,
                        "phase": phase_dir.name,
                        "checkpoint_type": fm.get("type"),
                        "content": checkpoint.read_text()
                    }

    return {"source": None, "exists": False}


# ============================================================================
# Command: coder-progress
# ============================================================================

def get_progress_metrics() -> dict:
    """Calculate progress metrics from project state."""
    planning = get_planning_dir()

    # Load roadmap
    roadmap_path = planning / "ROADMAP.md"
    roadmap_content = roadmap_path.read_text() if roadmap_path.exists() else ""

    # Count phases (look for ## Phase N patterns)
    import re
    phase_matches = re.findall(r'## Phase (\d+)', roadmap_content)
    total_phases = len(phase_matches)

    # Count completed phases (look for status: complete)
    completed_phases = roadmap_content.lower().count("status: complete")

    # Count plans in phases directory
    phases_dir = planning / "phases"
    total_plans = 0
    completed_plans = 0
    current_phase = None
    current_phase_plans = 0
    current_phase_completed = 0

    if phases_dir.exists():
        for phase_dir in sorted(phases_dir.iterdir()):
            if phase_dir.is_dir():
                plan_count = count_files_in_dir(phase_dir, "*-PLAN.md")
                summary_count = count_files_in_dir(phase_dir, "*-SUMMARY.md")
                total_plans += plan_count
                completed_plans += summary_count

                # Determine current phase (first incomplete)
                if plan_count > summary_count and current_phase is None:
                    current_phase = phase_dir.name
                    current_phase_plans = plan_count
                    current_phase_completed = summary_count

    # Load requirements
    reqs_path = planning / "REQUIREMENTS.md"
    total_reqs = 0
    completed_reqs = 0
    if reqs_path.exists():
        reqs_content = reqs_path.read_text()
        # Count REQ-XXX patterns
        total_reqs = len(re.findall(r'REQ-\d+', reqs_content))
        # Count completed (marked with [x])
        completed_reqs = len(re.findall(r'\[x\].*REQ-\d+', reqs_content, re.IGNORECASE))

    # Load state
    state_path = planning / "STATE.md"
    state_fm = load_md_frontmatter(state_path) if state_path.exists() else {}

    return {
        "total_phases": total_phases,
        "completed_phases": completed_phases,
        "total_plans": total_plans,
        "completed_plans": completed_plans,
        "total_reqs": total_reqs,
        "completed_reqs": completed_reqs,
        "current_phase": current_phase,
        "current_phase_plans": current_phase_plans,
        "current_phase_completed": current_phase_completed,
        "status": state_fm.get("status", "unknown"),
        "phase_percent": round((completed_phases / total_phases * 100) if total_phases > 0 else 0),
        "plan_percent": round((completed_plans / total_plans * 100) if total_plans > 0 else 0),
        "req_percent": round((completed_reqs / total_reqs * 100) if total_reqs > 0 else 0),
    }


# ============================================================================
# Command: coder-settings
# ============================================================================

DEFAULT_SETTINGS = {
    "mode": "interactive",
    "depth": "standard",
    "parallelization": True,
    "commit_tracking": True,
    "model_profile": "balanced",
    "workflow": {
        "research": True,
        "plan_check": True,
        "verifier": True
    },
    "notifications": {
        "checkpoint_sound": False,
        "phase_complete": True
    }
}


def get_settings() -> dict:
    """Get current settings with defaults."""
    planning = get_planning_dir()
    config_path = planning / "config.json"
    settings = load_json_file(config_path, DEFAULT_SETTINGS.copy())

    # Merge with defaults for any missing keys
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if subkey not in settings.get(key, {}):
                    settings.setdefault(key, {})[subkey] = subvalue

    return settings


def set_setting(key: str, value: str) -> dict:
    """Set a single setting."""
    planning = ensure_planning_dir()
    config_path = planning / "config.json"
    settings = get_settings()

    # Type conversion
    if value.lower() in ("true", "false"):
        value = value.lower() == "true"

    # Handle nested keys
    if "." in key:
        parts = key.split(".")
        target = settings
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        old_value = target.get(parts[-1])
        target[parts[-1]] = value
    else:
        old_value = settings.get(key)
        settings[key] = value

    save_json_file(config_path, settings)

    return {
        "key": key,
        "old_value": old_value,
        "new_value": value,
        "saved": True
    }


# ============================================================================
# Command: coder-rollback
# ============================================================================

def find_phase_commits(phase: str) -> list[dict]:
    """Find all commits belonging to a phase."""
    code, output = run_git_command([
        "log", "--oneline", "--grep", f"({phase})",
        "--format=%H|%s|%an|%ad"
    ])
    if code != 0:
        return []

    commits = []
    for line in output.strip().split('\n'):
        if line and '|' in line:
            parts = line.split('|')
            commits.append({
                "hash": parts[0][:7],
                "full_hash": parts[0],
                "message": parts[1] if len(parts) > 1 else "",
                "author": parts[2] if len(parts) > 2 else "",
                "date": parts[3] if len(parts) > 3 else ""
            })
    return commits


def find_plan_commits(plan: str) -> list[dict]:
    """Find all commits belonging to a specific plan."""
    code, output = run_git_command([
        "log", "--oneline", "--grep", f"({plan})",
        "--format=%H|%s"
    ])
    if code != 0:
        return []

    commits = []
    for line in output.strip().split('\n'):
        if line and '|' in line:
            hash_val, message = line.split('|', 1)
            commits.append({
                "hash": hash_val[:7],
                "full_hash": hash_val,
                "message": message
            })
    return commits


def get_rollback_preview(scope: str, identifier: str = None) -> dict:
    """Preview what would be rolled back."""
    if scope == "phase":
        commits = find_phase_commits(identifier)
    elif scope == "plan":
        commits = find_plan_commits(identifier)
    else:
        # Last plan - find most recent commit with plan reference
        code, output = run_git_command([
            "log", "-1", "--oneline",
            "--grep", "\\d+-\\d+",
            "--format=%H|%s"
        ])
        if code == 0 and output.strip():
            # Extract plan ID from commit message
            import re
            match = re.search(r'(\d+-\d+)', output)
            if match:
                identifier = match.group(1)
                commits = find_plan_commits(identifier)
            else:
                commits = []
        else:
            commits = []

    # Get files affected
    affected_files = set()
    for commit in commits:
        code, files = run_git_command([
            "diff-tree", "--no-commit-id", "--name-only", "-r",
            commit["full_hash"]
        ])
        if code == 0:
            affected_files.update(f.strip() for f in files.split('\n') if f.strip())

    return {
        "scope": scope,
        "identifier": identifier,
        "commits": commits,
        "commit_count": len(commits),
        "files_affected": sorted(affected_files),
        "file_count": len(affected_files),
        "git_status": get_git_status()
    }


# ============================================================================
# Command: coder-diff
# ============================================================================

def get_diff_stats(ref: str = "HEAD~1") -> dict:
    """Get diff statistics since reference point."""
    # Get commit list
    code, commits_output = run_git_command([
        "log", "--oneline", f"{ref}..HEAD"
    ])
    commits = [line for line in commits_output.strip().split('\n') if line]

    # Get diff stats
    code, stat_output = run_git_command([
        "diff", "--stat", f"{ref}..HEAD"
    ])

    # Get file list with status
    code, files_output = run_git_command([
        "diff", "--name-status", f"{ref}..HEAD"
    ])

    files = []
    for line in files_output.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                filename = parts[1]
                status_map = {'A': 'created', 'M': 'modified', 'D': 'deleted', 'R': 'renamed'}
                files.append({
                    "file": filename,
                    "status": status_map.get(status[0], status)
                })

    # Parse stats
    insertions = 0
    deletions = 0
    import re
    stats_match = re.search(r'(\d+) insertions?\(\+\)', stat_output)
    if stats_match:
        insertions = int(stats_match.group(1))
    stats_match = re.search(r'(\d+) deletions?\(-\)', stat_output)
    if stats_match:
        deletions = int(stats_match.group(1))

    return {
        "reference": ref,
        "commits": commits,
        "commit_count": len(commits),
        "files": files,
        "file_count": len(files),
        "insertions": insertions,
        "deletions": deletions,
        "net_change": insertions - deletions,
        "stat_output": stat_output
    }


# ============================================================================
# Command: coder-cost
# ============================================================================

TOKEN_ESTIMATES = {
    "new-project": {
        "base": 50000,
        "per_question": 2000,
        "research": 40000,
        "roadmap": 15000,
    },
    "plan-phase": {
        "base": 8000,
        "per_plan": 5000,
        "plan_check": 4000,
    },
    "execute-phase": {
        "base": 5000,
        "per_task": 3000,
        "per_file": 500,
        "verification": 6000,
    },
    "verify-work": {
        "base": 4000,
        "per_check": 1000,
        "debug": 8000,
    }
}

MODEL_PRICING = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.25, "output": 1.25},
}


def estimate_cost(operation: str, context: dict = None) -> dict:
    """Estimate token usage and cost for an operation."""
    context = context or {}
    estimates = TOKEN_ESTIMATES.get(operation, {"base": 10000})

    tokens = estimates.get("base", 10000)

    # Add context-dependent tokens
    if operation == "execute-phase":
        phase_num = context.get("phase")
        if phase_num:
            planning = get_planning_dir()
            phases_dir = planning / "phases"
            if phases_dir.exists():
                # Find matching phase directory
                for phase_dir in phases_dir.iterdir():
                    if phase_dir.is_dir() and phase_dir.name.startswith(f"{phase_num:02d}"):
                        plan_count = count_files_in_dir(phase_dir, "*-PLAN.md")
                        tokens += plan_count * estimates.get("per_task", 3000)
                        # Estimate files per plan
                        tokens += plan_count * 3 * estimates.get("per_file", 500)
                        break
        tokens += estimates.get("verification", 6000)

    elif operation == "plan-phase":
        # Estimate based on phase complexity
        tokens += estimates.get("per_plan", 5000) * 3  # Assume 3 plans
        tokens += estimates.get("plan_check", 4000)

    model = context.get("model_profile", "sonnet")
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["sonnet"])

    input_tokens = int(tokens * 0.6)
    output_tokens = int(tokens * 0.4)

    input_cost = input_tokens / 1_000_000 * pricing["input"]
    output_cost = output_tokens / 1_000_000 * pricing["output"]

    return {
        "operation": operation,
        "tokens": tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": model,
        "cost_usd": round(input_cost + output_cost, 4),
        "cost_breakdown": {
            "input": round(input_cost, 4),
            "output": round(output_cost, 4)
        },
        "comparison": {
            model: round(input_cost + output_cost, 4)
            for model, pricing in MODEL_PRICING.items()
            for input_cost, output_cost in [(
                input_tokens / 1_000_000 * pricing["input"],
                output_tokens / 1_000_000 * pricing["output"]
            )]
        }
    }


# ============================================================================
# Command: coder-metrics
# ============================================================================

def get_metrics_path() -> Path:
    """Get path to metrics file."""
    planning = ensure_planning_dir()
    return planning / "metrics.json"


def load_metrics() -> dict:
    """Load execution metrics."""
    return load_json_file(get_metrics_path(), {
        "sessions": [],
        "phases": [],
        "plans": [],
        "costs": [],
        "totals": {
            "sessions": 0,
            "phases_completed": 0,
            "plans_executed": 0,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "total_duration_minutes": 0
        }
    })


def record_metric(metric_type: str, data: dict) -> dict:
    """Record a new metric entry."""
    metrics = load_metrics()
    data["timestamp"] = datetime.now().isoformat()

    if metric_type == "session":
        metrics["sessions"].append(data)
        metrics["totals"]["sessions"] += 1
    elif metric_type == "phase":
        metrics["phases"].append(data)
        metrics["totals"]["phases_completed"] += 1
        if "duration_minutes" in data:
            metrics["totals"]["total_duration_minutes"] += data["duration_minutes"]
    elif metric_type == "plan":
        metrics["plans"].append(data)
        metrics["totals"]["plans_executed"] += 1
    elif metric_type == "cost":
        metrics["costs"].append(data)
        if "tokens" in data:
            metrics["totals"]["total_tokens"] += data["tokens"]
        if "cost_usd" in data:
            metrics["totals"]["total_cost_usd"] += data["cost_usd"]

    save_json_file(get_metrics_path(), metrics)
    return {"recorded": True, "type": metric_type, "data": data}


# ============================================================================
# Command: coder-history
# ============================================================================

def get_execution_history(limit: int = 20) -> list[dict]:
    """Get execution history from various sources."""
    history = []

    # From metrics
    metrics = load_metrics()
    for phase in metrics.get("phases", [])[-limit:]:
        history.append({
            "type": "phase",
            "timestamp": phase.get("timestamp"),
            "description": f"Phase {phase.get('phase_num')}: {phase.get('name', 'Unknown')}",
            "status": phase.get("status", "unknown"),
            "duration": phase.get("duration_minutes")
        })

    # From git commits
    code, output = run_git_command([
        "log", f"-{limit}", "--oneline",
        "--grep", "feat\\|fix\\|chore",
        "--format=%H|%s|%ad", "--date=short"
    ])
    if code == 0:
        for line in output.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|')
                history.append({
                    "type": "commit",
                    "timestamp": parts[2] if len(parts) > 2 else "",
                    "description": parts[1] if len(parts) > 1 else "",
                    "commit": parts[0][:7]
                })

    # Sort by timestamp
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return history[:limit]


# ============================================================================
# Command: coder-quick
# ============================================================================

def get_quick_tasks() -> list[dict]:
    """List all quick tasks."""
    planning = get_planning_dir()
    quick_dir = planning / "quick"

    if not quick_dir.exists():
        return []

    tasks = []
    for task_dir in sorted(quick_dir.iterdir()):
        if task_dir.is_dir():
            plan_path = task_dir / "PLAN.md"
            summary_path = task_dir / "SUMMARY.md"

            task = {
                "id": task_dir.name.split("-")[0] if "-" in task_dir.name else task_dir.name,
                "slug": task_dir.name,
                "has_plan": plan_path.exists(),
                "has_summary": summary_path.exists(),
                "status": "complete" if summary_path.exists() else "in_progress"
            }

            if plan_path.exists():
                fm = load_md_frontmatter(plan_path)
                task["description"] = fm.get("description", task_dir.name)
                task["created"] = fm.get("created")

            if summary_path.exists():
                fm = load_md_frontmatter(summary_path)
                task["commit"] = fm.get("commit")
                task["completed"] = fm.get("completed")

            tasks.append(task)

    return tasks


def init_quick_task(description: str, scope: str = None) -> dict:
    """Initialize a new quick task."""
    planning = ensure_planning_dir()
    quick_dir = planning / "quick"
    quick_dir.mkdir(exist_ok=True)

    # Generate ID
    existing = list(quick_dir.iterdir()) if quick_dir.exists() else []
    next_id = 1
    for d in existing:
        if d.is_dir() and d.name[0].isdigit():
            try:
                num = int(d.name.split("-")[0])
                next_id = max(next_id, num + 1)
            except ValueError:
                pass

    # Create slug
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', description.lower())[:30].strip('-')

    task_dir = quick_dir / f"{next_id:03d}-{slug}"
    task_dir.mkdir(exist_ok=True)

    return {
        "id": f"{next_id:03d}",
        "slug": slug,
        "dir": str(task_dir),
        "description": description,
        "scope": scope,
        "status": "initialized"
    }


# ============================================================================
# Command: coder-debug
# ============================================================================

def get_debug_session() -> dict:
    """Get current debug session state."""
    planning = get_planning_dir()
    debug_dir = planning / "debug"
    active_session = debug_dir / "active-session.md"

    if not active_session.exists():
        return {"active": False}

    fm = load_md_frontmatter(active_session)
    return {
        "active": True,
        "status": fm.get("status", "unknown"),
        "trigger": fm.get("trigger"),
        "created": fm.get("created"),
        "content": active_session.read_text()
    }


def init_debug_session(description: str) -> dict:
    """Initialize a new debug session."""
    planning = ensure_planning_dir()
    debug_dir = planning / "debug"
    debug_dir.mkdir(exist_ok=True)

    active_session = debug_dir / "active-session.md"

    # Create slug
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', description.lower())[:40].strip('-')

    content = f"""---
status: gathering
trigger: "{description}"
created: {datetime.now().isoformat()}
updated: {datetime.now().isoformat()}
---

# Debug Session: {slug}

## Trigger
> {description}

## Current Focus
hypothesis: [pending investigation]
test: [pending]
next_action: [gather symptoms]

## Symptoms
expected: [TBD]
actual: [TBD]
reproducible: [TBD]

## Environment
- OS: [if relevant]
- Version: [TBD]

## Eliminated
[None yet]

## Evidence
[Gathering...]

## Resolution
root_cause: [pending]
fix: [pending]
commit: [pending]
"""

    active_session.write_text(content)

    return {
        "initialized": True,
        "path": str(active_session),
        "slug": slug,
        "description": description
    }


def list_debug_sessions(include_resolved: bool = True) -> dict:
    """List debug sessions."""
    planning = get_planning_dir()
    debug_dir = planning / "debug"

    result = {"active": None, "resolved": []}

    if not debug_dir.exists():
        return result

    # Check active
    active_session = debug_dir / "active-session.md"
    if active_session.exists():
        fm = load_md_frontmatter(active_session)
        result["active"] = {
            "trigger": fm.get("trigger"),
            "status": fm.get("status"),
            "created": fm.get("created")
        }

    # Check resolved
    if include_resolved:
        resolved_dir = debug_dir / "resolved"
        if resolved_dir.exists():
            for f in sorted(resolved_dir.iterdir(), reverse=True)[:10]:
                if f.suffix == ".md":
                    fm = load_md_frontmatter(f)
                    result["resolved"].append({
                        "file": f.name,
                        "trigger": fm.get("trigger"),
                        "resolved": fm.get("resolved"),
                        "root_cause": fm.get("root_cause")
                    })

    return result


# ============================================================================
# Command: coder-learn
# ============================================================================

def extract_patterns(project_path: Path = None) -> list[dict]:
    """Extract patterns from project."""
    project_path = project_path or Path.cwd()
    planning = project_path / ".planning"
    patterns = []

    # Extract from SUMMARY files
    phases_dir = planning / "phases"
    if phases_dir.exists():
        for phase_dir in phases_dir.iterdir():
            if phase_dir.is_dir():
                for summary in phase_dir.glob("*-SUMMARY.md"):
                    fm = load_md_frontmatter(summary)
                    if fm.get("patterns"):
                        patterns.extend([
                            {"name": p, "source": str(summary), "phase": phase_dir.name}
                            for p in fm.get("patterns", "").split(",")
                        ])
                    if fm.get("tech-stack"):
                        patterns.append({
                            "name": f"tech-{fm.get('subsystem', 'unknown')}",
                            "category": "tech",
                            "source": str(summary),
                            "tech_stack": fm.get("tech-stack")
                        })

    # Extract from decisions
    decisions_path = planning / "decisions.json"
    if decisions_path.exists():
        decisions = load_json_file(decisions_path, [])
        for decision in decisions:
            patterns.append({
                "name": f"decision-{decision.get('id', 'unknown')}",
                "category": "decision",
                "choice": decision.get("choice"),
                "rationale": decision.get("rationale")
            })

    return patterns


def save_pattern(name: str, category: str, data: dict) -> dict:
    """Save a pattern to the pattern library."""
    patterns_dir = Path.home() / ".eri-rpg" / "patterns"
    patterns_dir.mkdir(parents=True, exist_ok=True)

    # Create pattern file
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
    pattern_file = patterns_dir / f"{slug}.json"

    pattern_data = {
        "name": name,
        "category": category,
        "created": datetime.now().isoformat(),
        "source_project": Path.cwd().name,
        **data
    }

    save_json_file(pattern_file, pattern_data)

    # Update index
    index_file = patterns_dir / "index.json"
    index = load_json_file(index_file, {"patterns": []})
    index["patterns"].append({
        "name": name,
        "category": category,
        "file": pattern_file.name
    })
    save_json_file(index_file, index)

    return {"saved": True, "path": str(pattern_file), "pattern": pattern_data}


# ============================================================================
# Command: coder-handoff
# ============================================================================

def generate_handoff(target: str = "human") -> dict:
    """Generate handoff documentation."""
    planning = get_planning_dir()

    # Gather context
    context = {
        "project": {},
        "state": {},
        "roadmap": {},
        "progress": get_progress_metrics(),
        "git": get_git_status()
    }

    # Load project info
    project_path = planning / "PROJECT.md"
    if project_path.exists():
        context["project"]["content"] = project_path.read_text()
        context["project"]["frontmatter"] = load_md_frontmatter(project_path)

    # Load state
    state_path = planning / "STATE.md"
    if state_path.exists():
        context["state"]["content"] = state_path.read_text()
        context["state"]["frontmatter"] = load_md_frontmatter(state_path)

    # Load roadmap
    roadmap_path = planning / "ROADMAP.md"
    if roadmap_path.exists():
        context["roadmap"]["content"] = roadmap_path.read_text()

    # Determine output filename
    filename = "HANDOFF-AI.md" if target == "ai" else "HANDOFF.md"
    output_path = planning / filename

    return {
        "target": target,
        "output_path": str(output_path),
        "context": context,
        "generated": datetime.now().isoformat()
    }


# ============================================================================
# Command: coder-add-todo
# ============================================================================

def add_todo(description: str, priority: str = "normal") -> dict:
    """Add a todo item."""
    planning = ensure_planning_dir()
    todos_path = planning / "todos.json"

    todos = load_json_file(todos_path, {"items": []})

    # Generate ID
    next_id = max([t.get("id", 0) for t in todos["items"]], default=0) + 1

    todo = {
        "id": next_id,
        "description": description,
        "priority": priority,
        "created": datetime.now().isoformat(),
        "status": "pending"
    }

    todos["items"].append(todo)
    save_json_file(todos_path, todos)

    return {"added": True, "todo": todo}


def list_todos(include_done: bool = False) -> list[dict]:
    """List todos."""
    planning = get_planning_dir()
    todos_path = planning / "todos.json"
    todos = load_json_file(todos_path, {"items": []})

    items = todos.get("items", [])
    if not include_done:
        items = [t for t in items if t.get("status") != "done"]

    return items


# ============================================================================
# Command: coder-template
# ============================================================================

def list_templates() -> list[dict]:
    """List available templates."""
    templates_dir = Path.home() / ".eri-rpg" / "templates"

    templates = []
    if templates_dir.exists():
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir():
                config_path = template_dir / "template.yaml"
                config = {}
                if config_path.exists():
                    # Simple YAML parsing
                    content = config_path.read_text()
                    for line in content.split('\n'):
                        if ':' in line and not line.startswith(' '):
                            key, value = line.split(':', 1)
                            config[key.strip()] = value.strip()

                templates.append({
                    "name": template_dir.name,
                    "path": str(template_dir),
                    "description": config.get("description", "No description"),
                    "category": config.get("category", "general")
                })

    return templates


# ============================================================================
# Command: coder-compare
# ============================================================================

def compare_branches(branch1: str, branch2: str = None) -> dict:
    """Compare two branches."""
    branch2 = branch2 or "HEAD"

    # Get diff stats
    code, stat = run_git_command(["diff", "--stat", f"{branch1}...{branch2}"])

    # Get commit difference
    code, commits_ahead = run_git_command([
        "rev-list", "--count", f"{branch1}..{branch2}"
    ])
    code, commits_behind = run_git_command([
        "rev-list", "--count", f"{branch2}..{branch1}"
    ])

    # Get file list
    code, files = run_git_command([
        "diff", "--name-only", f"{branch1}...{branch2}"
    ])

    return {
        "branch1": branch1,
        "branch2": branch2,
        "commits_ahead": int(commits_ahead.strip()) if commits_ahead.strip().isdigit() else 0,
        "commits_behind": int(commits_behind.strip()) if commits_behind.strip().isdigit() else 0,
        "files_changed": [f for f in files.strip().split('\n') if f],
        "stat": stat
    }


# ============================================================================
# Command: coder-split
# ============================================================================

def analyze_plan_for_split(plan_path: str) -> dict:
    """Analyze a plan to suggest how to split it."""
    path = Path(plan_path)
    if not path.exists():
        return {"error": f"Plan not found: {plan_path}"}

    content = path.read_text()

    # Count tasks
    import re
    tasks = re.findall(r'### Task \d+', content)

    # Estimate complexity
    lines = len(content.split('\n'))
    files_mentioned = len(re.findall(r'`[^`]+\.(ts|js|py|tsx|jsx)`', content))

    return {
        "path": str(path),
        "tasks": len(tasks),
        "lines": lines,
        "files_mentioned": files_mentioned,
        "suggest_split": len(tasks) > 3 or lines > 200,
        "suggested_parts": max(2, len(tasks) // 2) if len(tasks) > 3 else 1
    }


# ============================================================================
# Command: coder-merge
# ============================================================================

def analyze_plans_for_merge(plan_paths: list[str]) -> dict:
    """Analyze plans to see if they can be merged."""
    plans = []
    total_tasks = 0
    total_lines = 0

    for plan_path in plan_paths:
        path = Path(plan_path)
        if path.exists():
            content = path.read_text()
            import re
            tasks = len(re.findall(r'### Task \d+', content))
            total_tasks += tasks
            total_lines += len(content.split('\n'))
            plans.append({
                "path": str(path),
                "tasks": tasks,
                "lines": len(content.split('\n'))
            })

    return {
        "plans": plans,
        "total_tasks": total_tasks,
        "total_lines": total_lines,
        "can_merge": total_tasks <= 5 and total_lines <= 300,
        "merge_warning": "May be too complex" if total_tasks > 5 else None
    }


# ============================================================================
# Command: coder-replay
# ============================================================================

def get_replay_context(phase: int, plan: int = None) -> dict:
    """Get context needed to replay a phase or plan."""
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    # Find phase directory
    phase_dir = None
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase:02d}"):
                phase_dir = d
                break

    if not phase_dir:
        return {"error": f"Phase {phase} not found"}

    result = {
        "phase": phase,
        "phase_dir": str(phase_dir),
        "plans": [],
        "summaries": []
    }

    # Get plans
    for plan_file in sorted(phase_dir.glob("*-PLAN.md")):
        result["plans"].append({
            "path": str(plan_file),
            "name": plan_file.stem
        })

    # Get summaries
    for summary_file in sorted(phase_dir.glob("*-SUMMARY.md")):
        result["summaries"].append({
            "path": str(summary_file),
            "name": summary_file.stem
        })

    if plan:
        # Filter to specific plan
        result["plans"] = [p for p in result["plans"] if f"-{plan:02d}" in p["path"]]
        result["summaries"] = [s for s in result["summaries"] if f"-{plan:02d}" in s["path"]]

    return result


# ============================================================================
# Command: coder-pause
# ============================================================================

def get_pause_state() -> dict:
    """Get current state for pause/handoff."""
    planning = get_planning_dir()

    # Get current phase/plan info
    state = {}
    state_path = planning / "STATE.md"
    if state_path.exists():
        fm = load_md_frontmatter(state_path)
        state["current_phase"] = fm.get("current_phase")
        state["current_plan"] = fm.get("current_plan")
        state["status"] = fm.get("status")

    state["git"] = get_git_status()
    state["progress"] = get_progress_metrics()

    return state


def create_pause_file(reason: str = None) -> dict:
    """Create pause/handoff file."""
    planning = ensure_planning_dir()
    pause_path = planning / ".continue-here.md"

    state = get_pause_state()

    content = f"""---
paused: {datetime.now().isoformat()}
reason: {reason or "Session end"}
phase: {state.get("current_phase", "unknown")}
status: {state.get("status", "unknown")}
---

# Continue Here

## Last Position
**Phase:** {state.get("current_phase", "unknown")}
**Status:** {state.get("status", "unknown")}
**Git Status:** {"dirty" if state["git"]["dirty"] else "clean"}

## Uncommitted Changes
{chr(10).join(state["git"]["changes"][:10]) if state["git"]["changes"] else "None"}

## Resume Command
```
/coder:resume
```
"""

    pause_path.write_text(content)

    return {
        "created": True,
        "path": str(pause_path),
        "state": state,
        "reason": reason
    }


# ============================================================================
# Command: coder-new-project
# ============================================================================

def check_project_exists() -> dict:
    """Check if a project already exists."""
    planning = get_planning_dir()

    result = {
        "planning_exists": planning.exists(),
        "has_project_md": (planning / "PROJECT.md").exists(),
        "has_roadmap": (planning / "ROADMAP.md").exists(),
        "has_state": (planning / "STATE.md").exists(),
    }

    # Check for existing code (brownfield detection)
    cwd = Path.cwd()
    code_indicators = [
        "src", "lib", "app", "components", "pages",
        "package.json", "Cargo.toml", "pyproject.toml", "go.mod"
    ]
    result["existing_code"] = any((cwd / ind).exists() for ind in code_indicators)

    # Check for git
    code, _ = run_git_command(["status"])
    result["has_git"] = code == 0

    return result


def init_new_project(name: str, description: str = None) -> dict:
    """Initialize a new project structure."""
    planning = ensure_planning_dir()

    # Create directories
    (planning / "phases").mkdir(exist_ok=True)
    (planning / "research").mkdir(exist_ok=True)

    # Initialize git if needed
    code, _ = run_git_command(["status"])
    if code != 0:
        run_git_command(["init"])

    return {
        "initialized": True,
        "name": name,
        "description": description,
        "planning_dir": str(planning),
        "project_check": check_project_exists()
    }


# ============================================================================
# Command: coder-add-phase
# ============================================================================

def get_roadmap_phases() -> list[dict]:
    """Get all phases from roadmap."""
    planning = get_planning_dir()
    roadmap_path = planning / "ROADMAP.md"

    if not roadmap_path.exists():
        return []

    content = roadmap_path.read_text()

    import re
    phases = []
    pattern = r'## Phase (\d+)[:\s]+([^\n]+)'
    for match in re.finditer(pattern, content):
        phases.append({
            "number": int(match.group(1)),
            "name": match.group(2).strip()
        })

    return phases


def get_unassigned_requirements() -> list[dict]:
    """Get requirements not yet assigned to phases."""
    planning = get_planning_dir()
    reqs_path = planning / "REQUIREMENTS.md"
    roadmap_path = planning / "ROADMAP.md"

    if not reqs_path.exists():
        return []

    reqs_content = reqs_path.read_text()
    roadmap_content = roadmap_path.read_text() if roadmap_path.exists() else ""

    import re
    # Find all requirements
    all_reqs = re.findall(r'(REQ-\d+)', reqs_content)
    # Find assigned requirements
    assigned = re.findall(r'(REQ-\d+)', roadmap_content)

    unassigned = set(all_reqs) - set(assigned)
    return [{"id": r} for r in sorted(unassigned)]


def add_phase_info(phase_name: str, goal: str) -> dict:
    """Get info needed to add a phase."""
    phases = get_roadmap_phases()
    next_phase = max([p["number"] for p in phases], default=0) + 1

    return {
        "phase_number": next_phase,
        "phase_name": phase_name,
        "goal": goal,
        "existing_phases": phases,
        "unassigned_requirements": get_unassigned_requirements()
    }


# ============================================================================
# Command: coder-insert-phase
# ============================================================================

def get_insert_phase_info(after_phase: int, name: str, goal: str) -> dict:
    """Get info for inserting a phase."""
    phases = get_roadmap_phases()

    # Find phases that need renumbering
    phases_to_renumber = [p for p in phases if p["number"] > after_phase]

    return {
        "insert_after": after_phase,
        "new_phase_number": after_phase + 1,
        "phase_name": name,
        "goal": goal,
        "phases_to_renumber": phases_to_renumber,
        "total_renumber": len(phases_to_renumber)
    }


# ============================================================================
# Command: coder-remove-phase
# ============================================================================

def get_remove_phase_info(phase_num: int) -> dict:
    """Get info for removing a phase."""
    planning = get_planning_dir()
    phases = get_roadmap_phases()

    phase = next((p for p in phases if p["number"] == phase_num), None)
    if not phase:
        return {"error": f"Phase {phase_num} not found"}

    # Check if phase has started
    phases_dir = planning / "phases"
    phase_started = False
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                if list(d.glob("*-PLAN.md")) or list(d.glob("*-SUMMARY.md")):
                    phase_started = True
                break

    # Get requirements for this phase
    roadmap_path = planning / "ROADMAP.md"
    phase_reqs = []
    if roadmap_path.exists():
        content = roadmap_path.read_text()
        import re
        pattern = rf'## Phase {phase_num}.*?(?=## Phase \d+|$)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            phase_reqs = re.findall(r'(REQ-\d+)', match.group(0))

    return {
        "phase": phase,
        "can_remove": not phase_started,
        "started": phase_started,
        "requirements": phase_reqs,
        "phases_to_renumber": [p for p in phases if p["number"] > phase_num]
    }


# ============================================================================
# Command: coder-discuss-phase
# ============================================================================

def get_discuss_phase_context(phase_num: int) -> dict:
    """Get context for discussing a phase."""
    planning = get_planning_dir()

    # Get phase info from roadmap
    roadmap_path = planning / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"error": "No ROADMAP.md found"}

    content = roadmap_path.read_text()

    import re
    pattern = rf'## Phase {phase_num}[:\s]+(.*?)(?=## Phase \d+|$)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {"error": f"Phase {phase_num} not found"}

    phase_content = match.group(0)

    # Extract key info
    goal_match = re.search(r'\*\*Goal\*\*[:\s]+(.*?)(?=\n\*\*|\n##|$)', phase_content)
    reqs_match = re.search(r'\*\*Requirements\*\*[:\s]+(.*?)(?=\n\*\*|\n##|$)', phase_content)

    # Check for existing CONTEXT.md
    phases_dir = planning / "phases"
    context_exists = False
    phase_dir = None
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                phase_dir = d
                context_exists = (d / "CONTEXT.md").exists()
                break

    return {
        "phase": phase_num,
        "phase_content": phase_content,
        "goal": goal_match.group(1).strip() if goal_match else None,
        "requirements": reqs_match.group(1).strip() if reqs_match else None,
        "context_exists": context_exists,
        "phase_dir": str(phase_dir) if phase_dir else None
    }


# ============================================================================
# Command: coder-plan-phase
# ============================================================================

def get_plan_phase_context(phase_num: int, gaps_mode: bool = False) -> dict:
    """Get context needed for planning a phase."""
    planning = get_planning_dir()

    # Get phase info
    phase_info = get_phase_assumptions(phase_num)
    if "error" in phase_info:
        return phase_info

    # Find phase directory
    phases_dir = planning / "phases"
    phase_dir = None
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                phase_dir = d
                break

    # Check what exists
    context = {
        "phase": phase_num,
        "phase_info": phase_info,
        "has_context": False,
        "has_research": False,
        "has_verification": False,
        "gaps_mode": gaps_mode,
        "existing_plans": [],
        "brownfield": False
    }

    if phase_dir:
        context["phase_dir"] = str(phase_dir)
        context["has_context"] = (phase_dir / "CONTEXT.md").exists()
        context["has_research"] = (phase_dir / "RESEARCH.md").exists()
        context["has_verification"] = (phase_dir / "VERIFICATION.md").exists()
        context["existing_plans"] = [str(p) for p in phase_dir.glob("*-PLAN.md")]

    # Check for brownfield context
    codebase_dir = planning / "codebase"
    if codebase_dir.exists():
        context["brownfield"] = True
        context["codebase_files"] = [str(f) for f in codebase_dir.glob("*.md")]

    # Load settings for workflow options
    settings = get_settings()
    context["workflow"] = settings.get("workflow", {})

    return context


# ============================================================================
# Command: coder-execute-phase
# ============================================================================

def get_execute_phase_context(phase_num: int) -> dict:
    """Get context for executing a phase."""
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    # Find phase directory
    phase_dir = None
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                phase_dir = d
                break

    if not phase_dir:
        return {"error": f"Phase {phase_num} directory not found"}

    # Get plans
    plans = []
    for plan_path in sorted(phase_dir.glob("*-PLAN.md")):
        fm = load_md_frontmatter(plan_path)
        has_summary = plan_path.with_name(plan_path.stem.replace("-PLAN", "-SUMMARY") + ".md").exists()
        plans.append({
            "path": str(plan_path),
            "name": plan_path.stem,
            "wave": fm.get("wave", 1),
            "completed": has_summary
        })

    # Group by wave
    waves = {}
    for plan in plans:
        wave = plan.get("wave", 1)
        if wave not in waves:
            waves[wave] = []
        waves[wave].append(plan)

    # Check for checkpoints
    checkpoint_path = phase_dir / "CHECKPOINT.md"

    return {
        "phase": phase_num,
        "phase_dir": str(phase_dir),
        "plans": plans,
        "waves": waves,
        "total_plans": len(plans),
        "completed_plans": len([p for p in plans if p["completed"]]),
        "has_checkpoint": checkpoint_path.exists(),
        "settings": get_settings()
    }


# ============================================================================
# Command: coder-verify-work
# ============================================================================

def get_verify_work_context(phase_num: int) -> dict:
    """Get context for verifying a phase."""
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    # Find phase directory
    phase_dir = None
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                phase_dir = d
                break

    if not phase_dir:
        return {"error": f"Phase {phase_num} directory not found"}

    # Get phase info
    phase_info = get_phase_assumptions(phase_num)

    # Collect must_haves from all plans
    must_haves = {"truths": [], "artifacts": [], "key_links": []}
    for plan_path in sorted(phase_dir.glob("*-PLAN.md")):
        fm = load_md_frontmatter(plan_path)
        mh = fm.get("must_haves", {})
        if isinstance(mh, dict):
            must_haves["truths"].extend(mh.get("truths", []))
            must_haves["artifacts"].extend(mh.get("artifacts", []))
            must_haves["key_links"].extend(mh.get("key_links", []))

    # Check for existing verification
    verification_path = phase_dir / "VERIFICATION.md"
    uat_path = phase_dir / "UAT.md"

    return {
        "phase": phase_num,
        "phase_dir": str(phase_dir),
        "phase_info": phase_info,
        "must_haves": must_haves,
        "has_verification": verification_path.exists(),
        "has_uat": uat_path.exists()
    }


# ============================================================================
# Command: coder-complete-milestone
# ============================================================================

def get_complete_milestone_context(milestone: str = None) -> dict:
    """Get context for completing a milestone."""
    planning = get_planning_dir()

    # Load roadmap
    roadmap_path = planning / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"error": "No ROADMAP.md found"}

    content = roadmap_path.read_text()

    # Find current milestone
    import re
    milestone_match = re.search(r'## Milestone[:\s]+([^\n]+)', content)
    current_milestone = milestone or (milestone_match.group(1).strip() if milestone_match else "v1.0")

    # Check all phases complete
    phases = get_roadmap_phases()
    phases_dir = planning / "phases"

    incomplete_phases = []
    for phase in phases:
        phase_num = phase["number"]
        phase_complete = False
        if phases_dir.exists():
            for d in phases_dir.iterdir():
                if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                    verification = d / "VERIFICATION.md"
                    if verification.exists():
                        fm = load_md_frontmatter(verification)
                        if fm.get("status") == "passed":
                            phase_complete = True
                    break
        if not phase_complete:
            incomplete_phases.append(phase)

    # Get progress
    progress = get_progress_metrics()

    return {
        "milestone": current_milestone,
        "phases": phases,
        "total_phases": len(phases),
        "incomplete_phases": incomplete_phases,
        "can_complete": len(incomplete_phases) == 0,
        "progress": progress,
        "git": get_git_status()
    }


# ============================================================================
# Command: coder-new-milestone
# ============================================================================

def get_new_milestone_context(milestone_name: str) -> dict:
    """Get context for starting a new milestone."""
    planning = get_planning_dir()

    # Load existing project info
    project_path = planning / "PROJECT.md"
    has_project = project_path.exists()

    # Check for v2 requirements
    reqs_path = planning / "REQUIREMENTS.md"
    v2_reqs = []
    if reqs_path.exists():
        content = reqs_path.read_text()
        import re
        # Look for v2 scope section
        v2_match = re.search(r'## v2 Scope\n(.*?)(?=\n##|$)', content, re.DOTALL)
        if v2_match:
            v2_reqs = re.findall(r'(REQ-\d+)', v2_match.group(1))

    # Get previous milestone learnings
    archive_dir = planning / "archive"
    previous_milestones = []
    if archive_dir.exists():
        for d in archive_dir.iterdir():
            if d.is_dir():
                previous_milestones.append(d.name)

    return {
        "milestone_name": milestone_name,
        "has_project": has_project,
        "v2_requirements": v2_reqs,
        "v2_count": len(v2_reqs),
        "previous_milestones": previous_milestones
    }


# ============================================================================
# Command: coder-map-codebase
# ============================================================================

def get_codebase_overview(focus: str = "all") -> dict:
    """Get overview of existing codebase for mapping."""
    cwd = Path.cwd()

    # Detect project type
    project_type = "unknown"
    if (cwd / "package.json").exists():
        project_type = "node"
    elif (cwd / "Cargo.toml").exists():
        project_type = "rust"
    elif (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists() or (cwd / "requirements.txt").exists():
        project_type = "python"
    elif (cwd / "go.mod").exists():
        project_type = "go"

    # Count source files
    code_patterns = {
        "node": ["*.ts", "*.tsx", "*.js", "*.jsx"],
        "rust": ["*.rs"],
        "python": ["*.py"],
        "go": ["*.go"],
        "unknown": ["*.ts", "*.js", "*.py", "*.rs", "*.go"]
    }

    patterns = code_patterns.get(project_type, code_patterns["unknown"])

    file_count = 0
    for pattern in patterns:
        for f in cwd.rglob(pattern):
            if "node_modules" not in str(f) and "venv" not in str(f) and "target" not in str(f) and "__pycache__" not in str(f):
                file_count += 1

    # Check for existing mapping
    planning = get_planning_dir()
    codebase_dir = planning / "codebase"
    has_mapping = codebase_dir.exists() and any(codebase_dir.glob("*.md"))

    return {
        "project_type": project_type,
        "file_count": file_count,
        "focus": focus,
        "has_mapping": has_mapping,
        "existing_files": [f.name for f in codebase_dir.glob("*.md")] if has_mapping else [],
        "directories": [d.name for d in cwd.iterdir() if d.is_dir() and not d.name.startswith(".")][:20]
    }


# ============================================================================
# Command: coder-add-feature
# ============================================================================

def get_add_feature_context(feature_name: str, description: str = None) -> dict:
    """Get context for adding a feature to existing codebase."""
    planning = get_planning_dir()

    # Check for codebase mapping
    codebase_dir = planning / "codebase"
    has_mapping = codebase_dir.exists() and any(codebase_dir.glob("*.md"))

    # Get codebase overview
    codebase_overview = get_codebase_overview()

    # Check for existing features
    features_dir = planning / "features"
    existing_features = []
    if features_dir.exists():
        for d in features_dir.iterdir():
            if d.is_dir():
                existing_features.append(d.name)

    return {
        "feature_name": feature_name,
        "description": description,
        "needs_mapping": not has_mapping,
        "has_mapping": has_mapping,
        "codebase": codebase_overview,
        "existing_features": existing_features,
        "feature_dir": str(features_dir / feature_name)
    }


# ============================================================================
# Command: coder-new-project
# ============================================================================

def check_project_exists() -> dict:
    """Check if project already exists."""
    planning = get_planning_dir()

    result = {
        "planning_exists": planning.exists(),
        "has_project": (planning / "PROJECT.md").exists(),
        "has_roadmap": (planning / "ROADMAP.md").exists(),
        "has_state": (planning / "STATE.md").exists(),
    }

    # Check for brownfield (existing code)
    code_dirs = ["src", "lib", "app", "pkg", "internal"]
    for d in code_dirs:
        if (Path.cwd() / d).exists() and list((Path.cwd() / d).glob("*")):
            result["brownfield"] = True
            result["code_dir"] = d
            break
    else:
        result["brownfield"] = False

    # Check project files
    project_files = ["package.json", "Cargo.toml", "pyproject.toml", "go.mod", "setup.py"]
    for pf in project_files:
        if (Path.cwd() / pf).exists():
            result["project_type"] = pf.split(".")[0]
            break

    return result


def init_project_structure(name: str, description: str = None) -> dict:
    """Initialize project planning structure."""
    planning = ensure_planning_dir()

    # Create directories
    (planning / "phases").mkdir(exist_ok=True)
    (planning / "research").mkdir(exist_ok=True)

    return {
        "initialized": True,
        "planning_dir": str(planning),
        "name": name,
        "description": description,
        "directories_created": ["phases", "research"]
    }


# ============================================================================
# Command: coder-add-feature
# ============================================================================

def check_codebase_mapped() -> dict:
    """Check if codebase has been mapped."""
    planning = get_planning_dir()
    codebase_dir = planning / "codebase"

    result = {
        "mapped": codebase_dir.exists(),
        "files": []
    }

    if codebase_dir.exists():
        for f in codebase_dir.glob("*.md"):
            result["files"].append(f.name)

    return result


def init_feature(name: str, description: str = None) -> dict:
    """Initialize a new feature for brownfield development."""
    planning = ensure_planning_dir()
    features_dir = planning / "features"
    features_dir.mkdir(exist_ok=True)

    # Create slug
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())[:30].strip('-')

    feature_dir = features_dir / slug
    feature_dir.mkdir(exist_ok=True)

    return {
        "initialized": True,
        "feature_name": name,
        "slug": slug,
        "feature_dir": str(feature_dir),
        "description": description,
        "codebase_mapped": check_codebase_mapped()["mapped"]
    }


# ============================================================================
# Command: coder-add-phase
# ============================================================================

def get_roadmap_phases() -> list[dict]:
    """Get all phases from roadmap."""
    planning = get_planning_dir()
    roadmap_path = planning / "ROADMAP.md"

    if not roadmap_path.exists():
        return []

    content = roadmap_path.read_text()
    import re

    phases = []
    pattern = r'## Phase (\d+)[:\s]+([^\n]+)'
    for match in re.finditer(pattern, content):
        phases.append({
            "number": int(match.group(1)),
            "name": match.group(2).strip()
        })

    return phases


def get_unassigned_requirements() -> list[dict]:
    """Get requirements not assigned to any phase."""
    planning = get_planning_dir()
    reqs_path = planning / "REQUIREMENTS.md"
    roadmap_path = planning / "ROADMAP.md"

    if not reqs_path.exists():
        return []

    reqs_content = reqs_path.read_text()
    roadmap_content = roadmap_path.read_text() if roadmap_path.exists() else ""

    import re
    all_reqs = re.findall(r'(REQ-\d+)[:\s]+([^\n|]+)', reqs_content)
    assigned_reqs = set(re.findall(r'REQ-\d+', roadmap_content))

    unassigned = []
    for req_id, desc in all_reqs:
        if req_id not in assigned_reqs:
            unassigned.append({"id": req_id, "description": desc.strip()})

    return unassigned


# ============================================================================
# Command: coder-insert-phase
# ============================================================================

def validate_phase_insertion(after_phase: int) -> dict:
    """Validate if a phase can be inserted."""
    phases = get_roadmap_phases()

    if not phases:
        return {"valid": False, "error": "No roadmap found"}

    max_phase = max(p["number"] for p in phases)

    if after_phase < 0 or after_phase > max_phase:
        return {"valid": False, "error": f"Phase must be between 0 and {max_phase}"}

    # Check if subsequent phases are started
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    started_phases = []
    if phases_dir.exists():
        for phase_dir in phases_dir.iterdir():
            if phase_dir.is_dir():
                # Check if has plans or summaries
                if list(phase_dir.glob("*-PLAN.md")) or list(phase_dir.glob("*-SUMMARY.md")):
                    try:
                        phase_num = int(phase_dir.name.split("-")[0])
                        if phase_num > after_phase:
                            started_phases.append(phase_num)
                    except ValueError:
                        pass

    if started_phases:
        return {
            "valid": False,
            "error": f"Phases {started_phases} already have work started"
        }

    return {
        "valid": True,
        "after_phase": after_phase,
        "new_phase_number": after_phase + 1,
        "phases_to_renumber": [p["number"] for p in phases if p["number"] > after_phase]
    }


# ============================================================================
# Command: coder-remove-phase
# ============================================================================

def validate_phase_removal(phase: int) -> dict:
    """Validate if a phase can be removed."""
    phases = get_roadmap_phases()

    phase_info = next((p for p in phases if p["number"] == phase), None)
    if not phase_info:
        return {"valid": False, "error": f"Phase {phase} not found"}

    # Check if phase has started
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    if phases_dir.exists():
        for phase_dir in phases_dir.iterdir():
            if phase_dir.is_dir() and phase_dir.name.startswith(f"{phase:02d}"):
                if list(phase_dir.glob("*-PLAN.md")) or list(phase_dir.glob("*-SUMMARY.md")):
                    return {"valid": False, "error": f"Phase {phase} has work started"}

    # Get requirements assigned to this phase
    roadmap_path = planning / "ROADMAP.md"
    if roadmap_path.exists():
        import re
        content = roadmap_path.read_text()
        # Find phase section and extract requirements
        pattern = rf'## Phase {phase}.*?(?=## Phase \d+|$)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            reqs = re.findall(r'REQ-\d+', match.group(0))
            return {
                "valid": True,
                "phase": phase,
                "name": phase_info["name"],
                "requirements": reqs
            }

    return {"valid": True, "phase": phase, "name": phase_info["name"], "requirements": []}


# ============================================================================
# Command: coder-discuss-phase
# ============================================================================

def get_phase_context(phase: int) -> dict:
    """Get context for discussing a phase."""
    planning = get_planning_dir()

    # Get phase from roadmap
    roadmap_path = planning / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"error": "No ROADMAP.md found"}

    content = roadmap_path.read_text()
    import re

    # Extract phase section
    pattern = rf'## Phase {phase}[:\s]+(.*?)(?=## Phase \d+|$)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {"error": f"Phase {phase} not found"}

    phase_content = match.group(0)

    # Extract name
    name_match = re.search(rf'## Phase {phase}[:\s]+([^\n]+)', phase_content)
    phase_name = name_match.group(1).strip() if name_match else f"Phase {phase}"

    # Determine phase type
    phase_type = "general"
    type_indicators = {
        "ui": ["UI", "interface", "component", "page", "layout", "frontend"],
        "api": ["API", "endpoint", "REST", "GraphQL", "backend"],
        "data": ["database", "schema", "migration", "model", "storage"],
        "integration": ["integration", "webhook", "external", "sync"],
        "auth": ["auth", "login", "session", "permission", "security"],
    }

    lower_content = phase_content.lower()
    for ptype, indicators in type_indicators.items():
        if any(ind.lower() in lower_content for ind in indicators):
            phase_type = ptype
            break

    # Check for existing context
    phases_dir = planning / "phases"
    context_exists = False
    phase_dir = None

    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase:02d}"):
                phase_dir = d
                if (d / "CONTEXT.md").exists():
                    context_exists = True
                break

    return {
        "phase": phase,
        "name": phase_name,
        "content": phase_content,
        "type": phase_type,
        "context_exists": context_exists,
        "phase_dir": str(phase_dir) if phase_dir else None
    }


# ============================================================================
# Command: coder-plan-phase
# ============================================================================

def get_planning_context(phase: int, gaps_mode: bool = False) -> dict:
    """Get all context needed for planning a phase."""
    planning = get_planning_dir()

    context = {
        "phase": phase,
        "gaps_mode": gaps_mode,
        "files": {},
        "codebase": {}
    }

    # Load core files
    for filename in ["PROJECT.md", "ROADMAP.md", "STATE.md", "REQUIREMENTS.md"]:
        path = planning / filename
        if path.exists():
            context["files"][filename] = {
                "exists": True,
                "path": str(path)
            }

    # Load codebase context if exists (brownfield)
    codebase_dir = planning / "codebase"
    if codebase_dir.exists():
        for f in codebase_dir.glob("*.md"):
            context["codebase"][f.name] = str(f)
        context["is_brownfield"] = True
    else:
        context["is_brownfield"] = False

    # Find phase directory
    phases_dir = planning / "phases"
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase:02d}"):
                context["phase_dir"] = str(d)

                # Check for context file
                context_file = d / "CONTEXT.md"
                if context_file.exists():
                    context["has_context"] = True

                # Check for research
                research_file = d / "RESEARCH.md"
                if research_file.exists():
                    context["has_research"] = True

                # Check for verification (for gaps mode)
                if gaps_mode:
                    verification_file = d / "VERIFICATION.md"
                    if verification_file.exists():
                        context["verification_path"] = str(verification_file)

                break

    # Get settings
    context["settings"] = get_settings()

    return context


# ============================================================================
# Command: coder-execute-phase
# ============================================================================

def get_phase_plans(phase: int) -> dict:
    """Get all plans for a phase grouped by wave."""
    planning = get_planning_dir()
    phases_dir = planning / "phases"

    result = {
        "phase": phase,
        "phase_dir": None,
        "plans": [],
        "waves": {},
        "completed": [],
        "pending": []
    }

    if not phases_dir.exists():
        return result

    # Find phase directory
    for d in phases_dir.iterdir():
        if d.is_dir() and d.name.startswith(f"{phase:02d}"):
            result["phase_dir"] = str(d)

            # Get all plan files
            for plan_file in sorted(d.glob("*-PLAN.md")):
                fm = load_md_frontmatter(plan_file)

                plan_info = {
                    "path": str(plan_file),
                    "name": plan_file.stem,
                    "wave": int(fm.get("wave", 1)),
                    "autonomous": fm.get("autonomous", "true").lower() == "true"
                }

                # Check if completed (has summary)
                summary_file = plan_file.with_name(plan_file.stem.replace("-PLAN", "-SUMMARY") + ".md")
                if summary_file.exists():
                    plan_info["status"] = "completed"
                    result["completed"].append(plan_info)
                else:
                    plan_info["status"] = "pending"
                    result["pending"].append(plan_info)

                result["plans"].append(plan_info)

                # Group by wave
                wave = plan_info["wave"]
                if wave not in result["waves"]:
                    result["waves"][wave] = []
                result["waves"][wave].append(plan_info)

            break

    return result


def get_phase_tasks(phase: int) -> dict:
    """Get all tasks for a phase with completion status.

    Parses plan files to extract task names, types, and status.
    Checks SUMMARY files to determine completion.
    """
    import re

    planning = get_planning_dir()
    phases_dir = planning / "phases"

    result = {
        "phase": phase,
        "phase_name": None,
        "phase_dir": None,
        "plans": [],
        "total_tasks": 0,
        "completed_tasks": 0,
        "all_complete": False
    }

    if not phases_dir.exists():
        result["error"] = "No phases directory found"
        return result

    # Find phase directory
    phase_dir = None
    for d in phases_dir.iterdir():
        if d.is_dir() and d.name.startswith(f"{phase:02d}"):
            phase_dir = d
            result["phase_dir"] = str(d)
            result["phase_name"] = d.name
            break

    if not phase_dir:
        result["error"] = f"Phase {phase} not found"
        return result

    # Parse each plan file
    for plan_file in sorted(phase_dir.glob("*-PLAN.md")):
        fm = load_md_frontmatter(plan_file)
        content = plan_file.read_text()

        # Check if plan is completed (has SUMMARY)
        plan_num = plan_file.stem.split("-")[1] if "-" in plan_file.stem else "01"
        summary_pattern = f"SUMMARY-{plan_num}.md"
        summary_file = phase_dir / summary_pattern
        plan_completed = summary_file.exists()

        # Extract tasks using regex - get full task details
        tasks = []

        # Match entire task blocks
        task_block_pattern = re.compile(
            r'<task[^>]*type=["\']([^"\']+)["\'][^>]*>(.*?)</task>',
            re.DOTALL
        )

        def extract_tag(block: str, tag: str) -> str:
            """Extract content from a tag."""
            match = re.search(rf'<{tag}>(.*?)</{tag}>', block, re.DOTALL)
            return match.group(1).strip() if match else ""

        for match in task_block_pattern.finditer(content):
            task_type = match.group(1).strip()
            task_block = match.group(2)

            task_name = extract_tag(task_block, "name")
            files = extract_tag(task_block, "files")
            action = extract_tag(task_block, "action")
            verify = extract_tag(task_block, "verify")
            done = extract_tag(task_block, "done")

            tasks.append({
                "name": task_name,
                "type": task_type,
                "files": [f.strip() for f in files.split(",") if f.strip()] if files else [],
                "action": action,
                "verify": verify,
                "done": done,
                "completed": plan_completed
            })
            result["total_tasks"] += 1
            if plan_completed:
                result["completed_tasks"] += 1

        plan_info = {
            "plan": plan_num,
            "wave": int(fm.get("wave", 1)),
            "completed": plan_completed,
            "tasks": tasks
        }
        result["plans"].append(plan_info)

    result["all_complete"] = (
        result["total_tasks"] > 0 and
        result["completed_tasks"] == result["total_tasks"]
    )

    return result


# ============================================================================
# Command: coder-verify-work
# ============================================================================

def get_verification_context(phase: int) -> dict:
    """Get context needed for manual verification."""
    planning = get_planning_dir()

    context = {
        "phase": phase,
        "must_haves": {
            "truths": [],
            "artifacts": [],
            "key_links": []
        },
        "phase_goal": None
    }

    # Get phase goal from roadmap
    roadmap_path = planning / "ROADMAP.md"
    if roadmap_path.exists():
        import re
        content = roadmap_path.read_text()
        goal_match = re.search(rf'## Phase {phase}.*?\*\*Goal\*\*[:\s]+([^\n]+)', content, re.DOTALL)
        if goal_match:
            context["phase_goal"] = goal_match.group(1).strip()

    # Find phase directory and collect must_haves from plans
    phases_dir = planning / "phases"
    if phases_dir.exists():
        for d in phases_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{phase:02d}"):
                context["phase_dir"] = str(d)

                # Check for existing verification
                verification_path = d / "VERIFICATION.md"
                if verification_path.exists():
                    context["has_verification"] = True
                    fm = load_md_frontmatter(verification_path)
                    context["verification_status"] = fm.get("status")

                # Collect must_haves from all plans
                for plan_file in d.glob("*-PLAN.md"):
                    fm = load_md_frontmatter(plan_file)
                    must_haves = fm.get("must_haves", {})

                    if isinstance(must_haves, dict):
                        for truth in must_haves.get("truths", []):
                            if truth not in context["must_haves"]["truths"]:
                                context["must_haves"]["truths"].append(truth)

                        for artifact in must_haves.get("artifacts", []):
                            context["must_haves"]["artifacts"].append(artifact)

                        for link in must_haves.get("key_links", []):
                            context["must_haves"]["key_links"].append(link)

                break

    return context


# ============================================================================
# Command: coder-complete-milestone
# ============================================================================

def get_milestone_status() -> dict:
    """Get status of all phases for milestone completion check."""
    planning = get_planning_dir()

    result = {
        "milestone": None,
        "total_phases": 0,
        "completed_phases": 0,
        "verified_phases": 0,
        "incomplete": [],
        "unverified": []
    }

    # Get milestone from roadmap
    roadmap_path = planning / "ROADMAP.md"
    if roadmap_path.exists():
        import re
        content = roadmap_path.read_text()
        milestone_match = re.search(r'## Milestone[:\s]+([^\n]+)', content)
        if milestone_match:
            result["milestone"] = milestone_match.group(1).strip()

    phases = get_roadmap_phases()
    result["total_phases"] = len(phases)

    # Check each phase
    phases_dir = planning / "phases"
    if phases_dir.exists():
        for phase_info in phases:
            phase_num = phase_info["number"]
            phase_complete = False
            phase_verified = False

            for d in phases_dir.iterdir():
                if d.is_dir() and d.name.startswith(f"{phase_num:02d}"):
                    # Check for summaries (completion)
                    plans = list(d.glob("*-PLAN.md"))
                    summaries = list(d.glob("*-SUMMARY.md"))

                    if plans and len(summaries) >= len(plans):
                        phase_complete = True
                        result["completed_phases"] += 1

                    # Check verification
                    verification = d / "VERIFICATION.md"
                    if verification.exists():
                        fm = load_md_frontmatter(verification)
                        if fm.get("status") == "passed":
                            phase_verified = True
                            result["verified_phases"] += 1

                    break

            if not phase_complete:
                result["incomplete"].append(phase_info)
            elif not phase_verified:
                result["unverified"].append(phase_info)

    result["can_complete"] = (
        result["total_phases"] > 0 and
        len(result["incomplete"]) == 0 and
        len(result["unverified"]) == 0
    )

    return result


# ============================================================================
# Command: coder-new-milestone
# ============================================================================

def get_previous_milestone_context() -> dict:
    """Get context from previous milestone for new milestone."""
    planning = get_planning_dir()

    context = {
        "previous_milestones": [],
        "deferred_requirements": [],
        "learnings": []
    }

    # Check archive for previous milestones
    archive_dir = planning / "archive"
    if archive_dir.exists():
        for d in sorted(archive_dir.iterdir()):
            if d.is_dir():
                context["previous_milestones"].append({
                    "name": d.name,
                    "has_state": (d / "STATE.md").exists(),
                    "has_roadmap": (d / "ROADMAP.md").exists()
                })

    # Get v2 requirements from REQUIREMENTS.md
    reqs_path = planning / "REQUIREMENTS.md"
    if reqs_path.exists():
        import re
        content = reqs_path.read_text()

        # Find v2 section
        v2_match = re.search(r'## v2 Scope(.*?)(?=##|$)', content, re.DOTALL)
        if v2_match:
            reqs = re.findall(r'(REQ-\d+)[:\s]+([^\n|]+)', v2_match.group(1))
            context["deferred_requirements"] = [
                {"id": r[0], "description": r[1].strip()} for r in reqs
            ]

    return context


# ============================================================================
# Command: coder-map-codebase
# ============================================================================

def get_codebase_info() -> dict:
    """Get information about the codebase to map."""
    cwd = Path.cwd()

    info = {
        "project_root": str(cwd),
        "project_type": None,
        "has_mapping": False,
        "mapping_files": []
    }

    # Detect project type
    type_indicators = {
        "node": ["package.json"],
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
    }

    for ptype, files in type_indicators.items():
        for f in files:
            if (cwd / f).exists():
                info["project_type"] = ptype
                break
        if info["project_type"]:
            break

    # Check for existing mapping
    planning = get_planning_dir()
    codebase_dir = planning / "codebase"
    if codebase_dir.exists():
        info["has_mapping"] = True
        info["mapping_files"] = [f.name for f in codebase_dir.glob("*.md")]

    # Count source files
    extensions = {
        "node": ["*.js", "*.jsx", "*.ts", "*.tsx"],
        "python": ["*.py"],
        "rust": ["*.rs"],
        "go": ["*.go"],
    }

    exts = extensions.get(info["project_type"], ["*.py", "*.js", "*.ts"])
    file_count = 0
    for ext in exts:
        file_count += len(list(cwd.rglob(ext)))

    info["file_count"] = file_count

    return info


# ============================================================================
# Command: coder-pause
# ============================================================================

def get_pause_context() -> dict:
    """Get context for creating a pause/handoff state."""
    planning = get_planning_dir()

    context = {
        "current_phase": None,
        "current_plan": None,
        "uncommitted_changes": [],
        "last_commit": None
    }

    # Get current position from STATE.md
    state_path = planning / "STATE.md"
    if state_path.exists():
        fm = load_md_frontmatter(state_path)
        context["current_phase"] = fm.get("current_phase")
        context["current_plan"] = fm.get("current_plan")

    # Get git status
    git_status = get_git_status()
    context["uncommitted_changes"] = git_status.get("changes", [])
    context["last_commit"] = git_status.get("commit")
    context["is_dirty"] = git_status.get("dirty", False)

    return context


# ============================================================================
# Command: coder-list-phase-assumptions
# ============================================================================

def get_phase_assumptions(phase: int) -> dict:
    """Get assumptions/approach for a phase before planning."""
    planning = get_planning_dir()

    # Load roadmap to get phase info
    roadmap_path = planning / "ROADMAP.md"
    if not roadmap_path.exists():
        return {"error": "No ROADMAP.md found"}

    content = roadmap_path.read_text()

    # Extract phase section
    import re
    pattern = rf'## Phase {phase}[:\s]+(.*?)(?=## Phase \d+|$)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {"error": f"Phase {phase} not found in roadmap"}

    phase_content = match.group(0)

    # Extract key information
    goal_match = re.search(r'\*\*Goal\*\*[:\s]+(.*?)(?=\n\*\*|\n##|$)', phase_content)
    success_match = re.search(r'\*\*Success Criteria\*\*[:\s]+(.*?)(?=\n\*\*|\n##|$)', phase_content, re.DOTALL)

    return {
        "phase": phase,
        "content": phase_content,
        "goal": goal_match.group(1).strip() if goal_match else None,
        "success_criteria": success_match.group(1).strip() if success_match else None
    }


# ============================================================================
# Command: coder-plan-milestone-gaps
# ============================================================================

def find_milestone_gaps() -> list[dict]:
    """Find gaps from verification failures."""
    planning = get_planning_dir()
    phases_dir = planning / "phases"
    gaps = []

    if not phases_dir.exists():
        return gaps

    for phase_dir in sorted(phases_dir.iterdir()):
        if not phase_dir.is_dir():
            continue

        # Check for VERIFICATION.md
        verification_path = phase_dir / "VERIFICATION.md"
        if verification_path.exists():
            fm = load_md_frontmatter(verification_path)
            if fm.get("status") in ("gaps_found", "failed"):
                content = verification_path.read_text()

                # Extract gaps section
                import re
                gaps_match = re.search(r'## Gaps Summary\n(.*?)(?=\n##|$)', content, re.DOTALL)
                if gaps_match:
                    gaps.append({
                        "phase": phase_dir.name,
                        "status": fm.get("status"),
                        "score": fm.get("score"),
                        "gaps_content": gaps_match.group(1).strip()
                    })

    return gaps


# ============================================================================
# CLI Registration
# ============================================================================

def register(cli):
    """Register coder commands with CLI."""

    @cli.command("coder-resume")
    @click.option("--phase", "-p", type=int, help="Resume specific phase")
    @click.option("--plan", help="Resume specific plan (e.g., 2-03)")
    def coder_resume_cmd(phase: int = None, plan: str = None):
        """Get resume state for /coder:resume skill.

        Returns JSON with resume context for Claude Code to process.
        """
        result = get_resume_state()
        result["requested_phase"] = phase
        result["requested_plan"] = plan
        result["git_status"] = get_git_status()
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-progress")
    @click.option("--detailed", "-d", is_flag=True, help="Include detailed breakdown")
    @click.option("--phase", "-p", type=int, help="Focus on specific phase")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def coder_progress_cmd(detailed: bool, phase: int, as_json: bool):
        """Get progress metrics for /coder:progress skill.

        Returns project progress metrics and recommended next action.
        """
        result = get_progress_metrics()
        result["detailed"] = detailed
        result["focus_phase"] = phase

        if as_json or True:  # Always JSON for Claude Code
            click.echo(json.dumps(result, indent=2))

    @cli.command("coder-settings")
    @click.argument("key", required=False)
    @click.argument("value", required=False)
    @click.option("--edit", "-e", is_flag=True, help="Interactive edit mode")
    @click.option("--reset", is_flag=True, help="Reset to defaults")
    def coder_settings_cmd(key: str, value: str, edit: bool, reset: bool):
        """Manage settings for /coder:settings skill.

        View, edit, or reset workflow configuration.
        """
        if reset:
            planning = ensure_planning_dir()
            config_path = planning / "config.json"
            save_json_file(config_path, DEFAULT_SETTINGS.copy())
            click.echo(json.dumps({"reset": True, "settings": DEFAULT_SETTINGS}, indent=2))
            return

        if key and value:
            result = set_setting(key, value)
            click.echo(json.dumps(result, indent=2))
            return

        settings = get_settings()
        click.echo(json.dumps({
            "settings": settings,
            "defaults": DEFAULT_SETTINGS,
            "edit_mode": edit
        }, indent=2))

    @cli.command("coder-rollback")
    @click.option("--plan", help="Rollback specific plan")
    @click.option("--phase", type=int, help="Rollback entire phase")
    @click.option("--to", "commit", help="Rollback to specific commit")
    @click.option("--dry-run", is_flag=True, help="Preview without executing")
    def coder_rollback_cmd(plan: str, phase: int, commit: str, dry_run: bool):
        """Get rollback preview for /coder:rollback skill.

        Returns commits and files that would be affected by rollback.
        """
        if phase:
            scope = "phase"
            identifier = str(phase)
        elif plan:
            scope = "plan"
            identifier = plan
        elif commit:
            scope = "commit"
            identifier = commit
        else:
            scope = "last_plan"
            identifier = None

        result = get_rollback_preview(scope, identifier)
        result["dry_run"] = dry_run
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-diff")
    @click.option("--phase", "-p", type=int, help="Diff since phase start")
    @click.option("--plan", help="Diff for specific plan")
    @click.option("--since", help="Diff since commit or time")
    @click.option("--files", is_flag=True, help="File list only")
    @click.option("--stat", "stats_only", is_flag=True, help="Statistics only")
    def coder_diff_cmd(phase: int, plan: str, since: str, files: bool, stats_only: bool):
        """Get diff statistics for /coder:diff skill.

        Returns changes since checkpoint, phase start, or specified point.
        """
        ref = since or "HEAD~1"
        if phase:
            # Find phase start commit
            code, output = run_git_command([
                "log", "--oneline", "--grep", f"Phase {phase}",
                "--format=%H", "-1"
            ])
            if code == 0 and output.strip():
                ref = output.strip()

        result = get_diff_stats(ref)
        result["mode"] = "files" if files else "stat" if stats_only else "full"
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-cost")
    @click.argument("operation", required=False)
    @click.option("--phase", "-p", type=int, help="Phase number for context")
    @click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
    @click.option("--compare", help="Compare with model (e.g., local)")
    def coder_cost_cmd(operation: str, phase: int, detailed: bool, compare: str):
        """Estimate tokens and cost for /coder:cost skill.

        Returns token estimate and cost breakdown by model.
        """
        operation = operation or "execute-phase"
        context = {"phase": phase} if phase else {}
        settings = get_settings()
        context["model_profile"] = settings.get("model_profile", "sonnet")

        result = estimate_cost(operation, context)
        result["detailed"] = detailed
        result["compare_with"] = compare
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-metrics")
    @click.option("--record", help="Record metric type (session|phase|plan|cost)")
    @click.option("--data", help="JSON data to record")
    def coder_metrics_cmd(record: str, data: str):
        """Track execution metrics for /coder:metrics skill.

        View or record metrics about execution time, tokens, and costs.
        """
        if record and data:
            try:
                data_dict = json.loads(data)
                result = record_metric(record, data_dict)
                click.echo(json.dumps(result, indent=2))
            except json.JSONDecodeError:
                click.echo(json.dumps({"error": "Invalid JSON data"}, indent=2))
            return

        metrics = load_metrics()
        click.echo(json.dumps(metrics, indent=2))

    @cli.command("coder-history")
    @click.option("--limit", "-n", default=20, help="Number of entries")
    def coder_history_cmd(limit: int):
        """Get execution history for /coder:history skill.

        Returns recent execution events from metrics and git.
        """
        history = get_execution_history(limit)
        click.echo(json.dumps({"history": history, "count": len(history)}, indent=2))

    @cli.command("coder-quick")
    @click.argument("description", required=False)
    @click.option("--list", "list_tasks", is_flag=True, help="List quick tasks")
    @click.option("--resume", help="Resume quick task by ID")
    @click.option("--scope", help="Scope for new task")
    def coder_quick_cmd(description: str, list_tasks: bool, resume: str, scope: str):
        """Manage quick tasks for /coder:quick skill.

        List, create, or resume quick tasks.
        """
        if list_tasks:
            tasks = get_quick_tasks()
            click.echo(json.dumps({"tasks": tasks}, indent=2))
            return

        if resume:
            tasks = get_quick_tasks()
            task = next((t for t in tasks if t["id"] == resume), None)
            if task:
                click.echo(json.dumps({"resume": True, "task": task}, indent=2))
            else:
                click.echo(json.dumps({"error": f"Task {resume} not found"}, indent=2))
            return

        if description:
            result = init_quick_task(description, scope)
            click.echo(json.dumps(result, indent=2))
            return

        # Default: show status
        tasks = get_quick_tasks()
        active = [t for t in tasks if t["status"] == "in_progress"]
        click.echo(json.dumps({
            "active_task": active[0] if active else None,
            "total_tasks": len(tasks),
            "completed": len([t for t in tasks if t["status"] == "complete"])
        }, indent=2))

    @cli.command("coder-debug")
    @click.argument("description", required=False)
    @click.option("--list", "list_sessions", is_flag=True, help="List debug sessions")
    @click.option("--resume", is_flag=True, help="Resume active session")
    @click.option("--resolve", help="Resolve session")
    def coder_debug_cmd(description: str, list_sessions: bool, resume: bool, resolve: str):
        """Manage debug sessions for /coder:debug skill.

        Start, list, or manage debug investigations.
        """
        if list_sessions:
            result = list_debug_sessions()
            click.echo(json.dumps(result, indent=2))
            return

        if resume:
            session = get_debug_session()
            click.echo(json.dumps(session, indent=2))
            return

        if resolve:
            # Mark session as resolved
            planning = get_planning_dir()
            debug_dir = planning / "debug"
            active_session = debug_dir / "active-session.md"
            resolved_dir = debug_dir / "resolved"
            resolved_dir.mkdir(exist_ok=True)

            if active_session.exists():
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                resolved_path = resolved_dir / f"{timestamp}-resolved.md"
                active_session.rename(resolved_path)
                click.echo(json.dumps({
                    "resolved": True,
                    "archived_to": str(resolved_path)
                }, indent=2))
            else:
                click.echo(json.dumps({"error": "No active session"}, indent=2))
            return

        if description:
            result = init_debug_session(description)
            click.echo(json.dumps(result, indent=2))
            return

        # Default: show current session
        session = get_debug_session()
        click.echo(json.dumps(session, indent=2))

    @cli.command("coder-learn")
    @click.option("--phase", "-p", type=int, help="Learn from specific phase")
    @click.option("--pattern", help="Extract specific pattern")
    @click.option("--export", is_flag=True, help="Export as template")
    def coder_learn_cmd(phase: int, pattern: str, export: bool):
        """Extract patterns for /coder:learn skill.

        Learn from current project to create reusable patterns.
        """
        patterns = extract_patterns()

        if pattern:
            # Filter to specific pattern
            patterns = [p for p in patterns if pattern.lower() in p.get("name", "").lower()]

        result = {
            "patterns": patterns,
            "count": len(patterns),
            "export_requested": export,
            "focus_phase": phase
        }
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-handoff")
    @click.option("--for", "target", default="human", help="Target: human or ai")
    @click.option("--phase", "-p", type=int, help="Handoff specific phase")
    @click.option("--brief", is_flag=True, help="Brief summary only")
    def coder_handoff_cmd(target: str, phase: int, brief: bool):
        """Generate handoff docs for /coder:handoff skill.

        Create comprehensive documentation for handoff.
        """
        result = generate_handoff(target)
        result["focus_phase"] = phase
        result["brief"] = brief
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-add-todo")
    @click.argument("description")
    @click.option("--priority", "-p", default="normal", help="Priority: low|normal|high")
    def coder_add_todo_cmd(description: str, priority: str):
        """Add todo item for /coder:add-todo skill.

        Capture an idea for later implementation.
        """
        result = add_todo(description, priority)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-todos")
    @click.option("--all", "include_done", is_flag=True, help="Include completed")
    def coder_todos_cmd(include_done: bool):
        """List todos for /coder:add-todo skill."""
        todos = list_todos(include_done)
        click.echo(json.dumps({"todos": todos, "count": len(todos)}, indent=2))

    @cli.command("coder-template")
    @click.option("--list", "list_templates_flag", is_flag=True, help="List templates")
    @click.argument("name", required=False)
    def coder_template_cmd(list_templates_flag: bool, name: str):
        """Manage templates for /coder:template skill.

        List or use file templates.
        """
        if list_templates_flag or not name:
            templates = list_templates()
            click.echo(json.dumps({"templates": templates}, indent=2))
            return

        # Find and return template info
        templates = list_templates()
        template = next((t for t in templates if t["name"] == name), None)
        if template:
            click.echo(json.dumps({"template": template}, indent=2))
        else:
            click.echo(json.dumps({"error": f"Template '{name}' not found"}, indent=2))

    @cli.command("coder-compare")
    @click.argument("branch1")
    @click.argument("branch2", required=False)
    def coder_compare_cmd(branch1: str, branch2: str):
        """Compare branches for /coder:compare skill.

        Show differences between branches.
        """
        result = compare_branches(branch1, branch2)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-split")
    @click.argument("plan_path")
    def coder_split_cmd(plan_path: str):
        """Analyze plan for splitting for /coder:split skill.

        Suggest how to break a plan into smaller plans.
        """
        result = analyze_plan_for_split(plan_path)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-merge")
    @click.argument("plan_paths", nargs=-1)
    def coder_merge_cmd(plan_paths: tuple):
        """Analyze plans for merging for /coder:merge skill.

        Check if plans can be combined.
        """
        result = analyze_plans_for_merge(list(plan_paths))
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-replay")
    @click.argument("phase", type=int)
    @click.option("--plan", "-p", type=int, help="Replay specific plan")
    def coder_replay_cmd(phase: int, plan: int):
        """Get replay context for /coder:replay skill.

        Prepare to re-run a phase or plan.
        """
        result = get_replay_context(phase, plan)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-phase-assumptions")
    @click.argument("phase", type=int)
    def coder_phase_assumptions_cmd(phase: int):
        """Show phase assumptions for /coder:list-phase-assumptions skill.

        Display planning approach before execution.
        """
        result = get_phase_assumptions(phase)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-gaps")
    def coder_gaps_cmd():
        """Find verification gaps for /coder:plan-milestone-gaps skill.

        List gaps from failed verifications.
        """
        gaps = find_milestone_gaps()
        click.echo(json.dumps({"gaps": gaps, "count": len(gaps)}, indent=2))

    @cli.command("coder-pause")
    @click.option("--reason", "-r", help="Reason for pausing")
    def coder_pause_cmd(reason: str):
        """Create pause state for /coder:pause skill.

        Capture current state for seamless resume later.
        """
        result = create_pause_file(reason)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-new-project")
    @click.argument("name", required=False)
    @click.option("--description", "-d", help="Project description")
    @click.option("--check", is_flag=True, help="Check project state only")
    def coder_new_project_cmd(name: str, description: str, check: bool):
        """Initialize project for /coder:new-project skill.

        Check for existing project or initialize new one.
        """
        if check or not name:
            result = check_project_exists()
            click.echo(json.dumps(result, indent=2))
            return

        result = init_new_project(name, description)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-add-phase")
    @click.argument("name")
    @click.argument("goal", required=False)
    def coder_add_phase_cmd(name: str, goal: str):
        """Get info for /coder:add-phase skill.

        Prepare to add a new phase to roadmap.
        """
        result = add_phase_info(name, goal or "")
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-insert-phase")
    @click.argument("after_phase", type=int)
    @click.argument("name")
    @click.argument("goal", required=False)
    def coder_insert_phase_cmd(after_phase: int, name: str, goal: str):
        """Get info for /coder:insert-phase skill.

        Prepare to insert a phase at specific position.
        """
        result = get_insert_phase_info(after_phase, name, goal or "")
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-remove-phase")
    @click.argument("phase", type=int)
    def coder_remove_phase_cmd(phase: int):
        """Get info for /coder:remove-phase skill.

        Check if phase can be removed.
        """
        result = get_remove_phase_info(phase)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-discuss-phase")
    @click.argument("phase", type=int)
    def coder_discuss_phase_cmd(phase: int):
        """Get context for /coder:discuss-phase skill.

        Load phase info for implementation discussion.
        """
        result = get_discuss_phase_context(phase)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-plan-phase")
    @click.argument("phase", type=int)
    @click.option("--gaps", is_flag=True, help="Re-plan from verification gaps")
    def coder_plan_phase_cmd(phase: int, gaps: bool):
        """Get context for /coder:plan-phase skill.

        Load all context needed for planning.
        """
        result = get_plan_phase_context(phase, gaps)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-execute-phase")
    @click.argument("phase", type=int)
    def coder_execute_phase_cmd(phase: int):
        """Get context for /coder:execute-phase skill.

        Load plans and execution state.
        """
        result = get_execute_phase_context(phase)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-verify-work")
    @click.argument("phase", type=int)
    def coder_verify_work_cmd(phase: int):
        """Get context for /coder:verify-work skill.

        Load must-haves and verification state.
        """
        result = get_verify_work_context(phase)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-complete-milestone")
    @click.argument("milestone", required=False)
    def coder_complete_milestone_cmd(milestone: str):
        """Get context for /coder:complete-milestone skill.

        Check if all phases complete and prepare for archive.
        """
        result = get_complete_milestone_context(milestone)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-new-milestone")
    @click.argument("name")
    def coder_new_milestone_cmd(name: str):
        """Get context for /coder:new-milestone skill.

        Prepare to start a new milestone.
        """
        result = get_new_milestone_context(name)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-map-codebase")
    @click.option("--focus", default="all", help="Focus: tech|arch|quality|concerns|all")
    def coder_map_codebase_cmd(focus: str):
        """Get codebase overview for /coder:map-codebase skill.

        Analyze existing codebase structure.
        """
        result = get_codebase_overview(focus)
        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-help")
    @click.argument("topic", required=False)
    def coder_help_cmd(topic: str):
        """Get help content for /coder:help skill.

        Return command reference and workflow info.
        """
        commands = {
            "core": [
                {"name": "new-project", "description": "Initialize new project"},
                {"name": "discuss-phase", "description": "Capture implementation decisions"},
                {"name": "plan-phase", "description": "Create executable plans"},
                {"name": "execute-phase", "description": "Execute all phase plans"},
                {"name": "verify-work", "description": "Manual acceptance testing"},
                {"name": "complete-milestone", "description": "Archive and tag release"},
            ],
            "phase": [
                {"name": "add-phase", "description": "Append phase to roadmap"},
                {"name": "insert-phase", "description": "Insert before phase N"},
                {"name": "remove-phase", "description": "Remove future phase"},
            ],
            "navigation": [
                {"name": "progress", "description": "Current status and metrics"},
                {"name": "help", "description": "This help"},
                {"name": "settings", "description": "Configure preferences"},
            ],
            "utility": [
                {"name": "quick", "description": "Ad-hoc task with guarantees"},
                {"name": "debug", "description": "Systematic debugging"},
                {"name": "add-todo", "description": "Capture for later"},
                {"name": "pause", "description": "Create handoff state"},
                {"name": "resume", "description": "Restore from pause"},
                {"name": "rollback", "description": "Undo execution"},
                {"name": "diff", "description": "Show changes"},
                {"name": "cost", "description": "Estimate tokens"},
                {"name": "metrics", "description": "Track execution"},
                {"name": "history", "description": "Execution history"},
                {"name": "learn", "description": "Extract patterns"},
                {"name": "handoff", "description": "Generate docs"},
            ]
        }

        result = {
            "commands": commands,
            "topic": topic
        }

        if topic:
            # Filter to specific topic
            for category, cmds in commands.items():
                matching = [c for c in cmds if topic.lower() in c["name"].lower()]
                if matching:
                    result["matching"] = matching
                    break

        click.echo(json.dumps(result, indent=2))

    @cli.command("coder-phase-tasks")
    @click.argument("phase", type=int)
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def coder_phase_tasks_cmd(phase: int, as_json: bool):
        """List all tasks for a phase with completion status.

        Example:
            eri-rpg coder-phase-tasks 3
        """
        result = get_phase_tasks(phase)

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        # Human-readable output
        if "error" in result:
            click.echo(f"Error: {result['error']}")
            return

        phase_name = result.get("phase_name", f"Phase {phase}")
        click.echo(f"\n# {phase_name}\n")

        for plan in result["plans"]:
            click.echo(f"## Plan {plan['plan']} (Wave {plan['wave']})\n")

            for i, task in enumerate(plan["tasks"], 1):
                task_type = task.get("type", "auto")
                name = task.get("name", "").strip()
                # Remove redundant "Task N:" prefix if present
                if name.lower().startswith(f"task {i}:"):
                    name = name[len(f"task {i}:"):].strip()
                click.echo(f"### Task {i}: {name}")
                if task_type != "auto":
                    click.echo(f"Type: {task_type}")

                if task.get("files"):
                    click.echo(f"Files: {', '.join(task['files'])}")

                if task.get("action"):
                    # Show first 3 lines of action, truncate rest
                    lines = task["action"].strip().split("\n")
                    preview = "\n".join(lines[:5])
                    if len(lines) > 5:
                        preview += f"\n... ({len(lines) - 5} more lines)"
                    click.echo(f"Action:\n{preview}")

                if task.get("done"):
                    click.echo(f"Done when: {task['done']}")

                click.echo()

    @cli.command("coder-phase-list")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def coder_phase_list_cmd(as_json: bool):
        """List all phases with status.

        Example:
            eri-rpg coder-phase-list
        """
        planning = get_planning_dir()
        phases_dir = planning / "phases"

        result = {
            "phases": [],
            "total": 0,
            "completed": 0,
            "current": None
        }

        if not phases_dir.exists():
            if as_json:
                result["error"] = "No phases directory found"
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo("No phases directory found")
            return

        # Read ROADMAP.md for phase names if available
        roadmap_path = planning / "ROADMAP.md"
        phase_goals = {}
        if roadmap_path.exists():
            import re
            content = roadmap_path.read_text()
            # Match "### Phase N: Name" or "### Phase N - Name"
            for match in re.finditer(r'###\s*Phase\s*(\d+)[:\-\s]+([^\n]+)', content):
                phase_goals[int(match.group(1))] = match.group(2).strip()

        # Scan phase directories
        for d in sorted(phases_dir.iterdir()):
            if not d.is_dir():
                continue

            # Parse directory name like "03-jobs"
            parts = d.name.split("-", 1)
            if not parts[0].isdigit():
                continue

            phase_num = int(parts[0])
            phase_name = parts[1] if len(parts) > 1 else f"Phase {phase_num}"

            # Count plans and completions
            plans = list(d.glob("*-PLAN.md"))
            summaries = list(d.glob("SUMMARY-*.md"))

            phase_info = {
                "number": phase_num,
                "name": phase_name,
                "goal": phase_goals.get(phase_num, ""),
                "plans": len(plans),
                "completed_plans": len(summaries),
                "status": "complete" if len(summaries) >= len(plans) and len(plans) > 0 else "pending"
            }

            if phase_info["status"] == "complete":
                result["completed"] += 1
            elif result["current"] is None:
                result["current"] = phase_num

            result["phases"].append(phase_info)
            result["total"] += 1

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        # Human-readable output
        click.echo(f"\nPhases ({result['completed']}/{result['total']} complete)\n")

        for p in result["phases"]:
            status = "[x]" if p["status"] == "complete" else "[ ]"
            current = " <-- current" if p["number"] == result["current"] else ""
            goal = f" - {p['goal']}" if p["goal"] else ""
            plans = f"({p['completed_plans']}/{p['plans']} plans)"
            click.echo(f"{status} Phase {p['number']}: {p['name']}{goal} {plans}{current}")
