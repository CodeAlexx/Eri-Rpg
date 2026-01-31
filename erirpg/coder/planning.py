"""
Plan manipulation for coder workflow.

Commands:
- split: Break plan into smaller plans
- merge: Combine multiple plans
- replay: Re-run a phase with modifications
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import re
from datetime import datetime

from . import get_planning_dir, timestamp


def get_plan_path(
    phase: int, plan: int, project_path: Optional[Path] = None
) -> Optional[Path]:
    """Get path to a plan file."""
    planning_dir = get_planning_dir(project_path)
    phases_dir = planning_dir / "phases"

    if not phases_dir.exists():
        return None

    for d in phases_dir.iterdir():
        if d.name.startswith(f"{phase:02d}-"):
            # Look for plan file
            pattern = f"*{phase:02d}-{plan:02d}*-PLAN.md"
            matches = list(d.glob(pattern))
            if matches:
                return matches[0]
            # Try alternate patterns
            for f in d.glob("*-PLAN.md"):
                if f"-{plan:02d}" in f.name or f"_{plan:02d}" in f.name:
                    return f

    return None


def load_plan(
    phase: int, plan: int, project_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Load a plan file and parse its structure."""
    plan_path = get_plan_path(phase, plan, project_path)
    if not plan_path or not plan_path.exists():
        return None

    content = plan_path.read_text()

    # Parse frontmatter
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except:
                pass
            body = parts[2]

    # Parse tasks
    tasks = []
    task_pattern = re.compile(r'<task[^>]*>(.*?)</task>', re.DOTALL)
    for match in task_pattern.finditer(body):
        task_content = match.group(1)
        task = {
            "raw": match.group(0),
            "content": task_content,
        }

        # Extract task parts
        name_match = re.search(r'<name>(.*?)</name>', task_content, re.DOTALL)
        files_match = re.search(r'<files>(.*?)</files>', task_content, re.DOTALL)
        action_match = re.search(r'<action>(.*?)</action>', task_content, re.DOTALL)
        verify_match = re.search(r'<verify>(.*?)</verify>', task_content, re.DOTALL)
        done_match = re.search(r'<done>(.*?)</done>', task_content, re.DOTALL)

        if name_match:
            task["name"] = name_match.group(1).strip()
        if files_match:
            task["files"] = [f.strip() for f in files_match.group(1).strip().split("\n") if f.strip()]
        if action_match:
            task["action"] = action_match.group(1).strip()
        if verify_match:
            task["verify"] = verify_match.group(1).strip()
        if done_match:
            task["done"] = done_match.group(1).strip()

        tasks.append(task)

    # Extract sections
    objective_match = re.search(r'<objective>(.*?)</objective>', body, re.DOTALL)
    verification_match = re.search(r'<verification>(.*?)</verification>', body, re.DOTALL)

    return {
        "path": plan_path,
        "frontmatter": frontmatter,
        "body": body,
        "tasks": tasks,
        "objective": objective_match.group(1).strip() if objective_match else "",
        "verification": verification_match.group(1).strip() if verification_match else "",
    }


def save_plan(
    plan_data: Dict[str, Any],
    path: Path,
) -> None:
    """Save a plan to file."""
    import yaml

    content = "---\n"
    content += yaml.dump(plan_data["frontmatter"], default_flow_style=False)
    content += "---\n\n"

    if plan_data.get("objective"):
        content += f"<objective>\n{plan_data['objective']}\n</objective>\n\n"

    content += "<tasks>\n\n"
    for task in plan_data.get("tasks", []):
        if task.get("raw"):
            content += task["raw"] + "\n\n"
        else:
            content += '<task type="auto">\n'
            if task.get("name"):
                content += f"  <name>{task['name']}</name>\n"
            if task.get("files"):
                content += f"  <files>{chr(10).join(task['files'])}</files>\n"
            if task.get("action"):
                content += f"  <action>{task['action']}</action>\n"
            if task.get("verify"):
                content += f"  <verify>{task['verify']}</verify>\n"
            if task.get("done"):
                content += f"  <done>{task['done']}</done>\n"
            content += "</task>\n\n"

    content += "</tasks>\n\n"

    if plan_data.get("verification"):
        content += f"<verification>\n{plan_data['verification']}\n</verification>\n\n"

    path.write_text(content)


def split_plan(
    phase: int,
    plan: int,
    split_at: int,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Split a plan into two at the specified task.

    Args:
        phase: Phase number
        plan: Plan number
        split_at: Task number to split at (this task goes to second plan)
        project_path: Project path

    Returns:
        Dict with paths to new plans
    """
    plan_data = load_plan(phase, plan, project_path)
    if not plan_data:
        return {"error": f"Plan {phase}-{plan:02d} not found"}

    tasks = plan_data["tasks"]
    if split_at < 1 or split_at > len(tasks):
        return {"error": f"Invalid split point. Plan has {len(tasks)} tasks."}

    # Split tasks
    tasks_a = tasks[:split_at - 1]
    tasks_b = tasks[split_at - 1:]

    if not tasks_a or not tasks_b:
        return {"error": "Split would create empty plan"}

    # Create new plan data
    plan_a = {
        "frontmatter": {**plan_data["frontmatter"]},
        "objective": plan_data["objective"],
        "tasks": tasks_a,
        "verification": "See subsequent plan for final verification",
    }

    plan_b = {
        "frontmatter": {**plan_data["frontmatter"]},
        "objective": plan_data["objective"] + " (continued)",
        "tasks": tasks_b,
        "verification": plan_data["verification"],
    }

    # Update plan numbers
    original_path = plan_data["path"]
    dir_path = original_path.parent

    # Rename original to -a
    plan_a_path = dir_path / original_path.name.replace("-PLAN.md", "a-PLAN.md")
    plan_b_path = dir_path / original_path.name.replace("-PLAN.md", "b-PLAN.md")

    # Update frontmatter
    plan_a["frontmatter"]["plan"] = f"{plan}a"
    plan_b["frontmatter"]["plan"] = f"{plan}b"
    plan_b["frontmatter"]["depends_on"] = [f"{phase:02d}-{plan}a"]

    # Save plans
    save_plan(plan_a, plan_a_path)
    save_plan(plan_b, plan_b_path)

    # Archive original
    archive_dir = dir_path / "archived"
    archive_dir.mkdir(exist_ok=True)
    original_path.rename(archive_dir / original_path.name)

    return {
        "success": True,
        "plan_a": str(plan_a_path),
        "plan_b": str(plan_b_path),
        "archived": str(archive_dir / original_path.name),
        "tasks_a": len(tasks_a),
        "tasks_b": len(tasks_b),
    }


def merge_plans(
    phase: int,
    plans: List[int],
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Merge multiple plans into one.

    Args:
        phase: Phase number
        plans: List of plan numbers to merge
        project_path: Project path

    Returns:
        Dict with path to merged plan
    """
    if len(plans) < 2:
        return {"error": "Need at least 2 plans to merge"}

    # Load all plans
    plan_data_list = []
    for plan_num in plans:
        data = load_plan(phase, plan_num, project_path)
        if not data:
            return {"error": f"Plan {phase}-{plan_num:02d} not found"}
        plan_data_list.append(data)

    # Combine tasks
    all_tasks = []
    for data in plan_data_list:
        all_tasks.extend(data["tasks"])

    # Check task limit
    if len(all_tasks) > 5:
        return {
            "error": f"Merged plan would have {len(all_tasks)} tasks. Maximum is 5.",
            "suggestion": "Consider merging fewer plans or splitting first.",
        }

    # Create merged plan
    first_plan = plan_data_list[0]
    merged = {
        "frontmatter": {**first_plan["frontmatter"]},
        "objective": first_plan["objective"],
        "tasks": all_tasks,
        "verification": plan_data_list[-1]["verification"],
    }

    # Use first plan's number
    merged["frontmatter"]["plan"] = plans[0]
    merged["frontmatter"]["merged_from"] = plans

    # Save merged plan
    merged_path = first_plan["path"]
    save_plan(merged, merged_path)

    # Archive other plans
    dir_path = first_plan["path"].parent
    archive_dir = dir_path / "archived"
    archive_dir.mkdir(exist_ok=True)

    archived = []
    for data in plan_data_list[1:]:
        archive_path = archive_dir / data["path"].name
        data["path"].rename(archive_path)
        archived.append(str(archive_path))

    return {
        "success": True,
        "merged_plan": str(merged_path),
        "archived": archived,
        "total_tasks": len(all_tasks),
    }


def prepare_replay(
    phase: int,
    plan: Optional[int] = None,
    modifications: Optional[Dict] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Prepare a phase or plan for replay.

    Args:
        phase: Phase number
        plan: Optional specific plan (replays whole phase if None)
        modifications: Optional modifications to apply
        project_path: Project path

    Returns:
        Dict with replay preparation info
    """
    planning_dir = get_planning_dir(project_path)
    phases_dir = planning_dir / "phases"

    # Find phase directory
    phase_dir = None
    for d in phases_dir.iterdir() if phases_dir.exists() else []:
        if d.name.startswith(f"{phase:02d}-"):
            phase_dir = d
            break

    if not phase_dir:
        return {"error": f"Phase {phase} not found"}

    # Archive existing summaries
    archive_dir = phase_dir / "archived"
    archive_dir.mkdir(exist_ok=True)

    archived = []
    if plan:
        # Archive specific plan's summary
        pattern = f"*{phase:02d}-{plan:02d}*-SUMMARY.md"
        for summary in phase_dir.glob(pattern):
            archive_path = archive_dir / f"{summary.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            summary.rename(archive_path)
            archived.append(str(archive_path))
    else:
        # Archive all summaries
        for summary in phase_dir.glob("*-SUMMARY.md"):
            archive_path = archive_dir / f"{summary.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            summary.rename(archive_path)
            archived.append(str(archive_path))

    # Apply modifications if provided
    modified_plans = []
    if modifications:
        if plan:
            plan_data = load_plan(phase, plan, project_path)
            if plan_data:
                # Apply modifications
                for key, value in modifications.items():
                    if key == "objective":
                        plan_data["objective"] = value
                    elif key == "verification":
                        plan_data["verification"] = value
                    elif key.startswith("task_"):
                        # Modify specific task
                        task_idx = int(key.split("_")[1]) - 1
                        if 0 <= task_idx < len(plan_data["tasks"]):
                            plan_data["tasks"][task_idx].update(value)

                save_plan(plan_data, plan_data["path"])
                modified_plans.append(str(plan_data["path"]))

    return {
        "success": True,
        "phase": phase,
        "plan": plan,
        "archived_summaries": archived,
        "modified_plans": modified_plans,
        "next_command": f"/coder:execute-phase {phase}" + (f" --plan {plan}" if plan else ""),
    }


def list_phase_plans(
    phase: int, project_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """List all plans in a phase."""
    planning_dir = get_planning_dir(project_path)
    phases_dir = planning_dir / "phases"

    plans = []
    for d in phases_dir.iterdir() if phases_dir.exists() else []:
        if d.name.startswith(f"{phase:02d}-"):
            for plan_file in sorted(d.glob("*-PLAN.md")):
                plan_data = load_plan(phase, _extract_plan_num(plan_file.name), project_path)
                if plan_data:
                    # Check for summary
                    summary_path = plan_file.with_name(
                        plan_file.name.replace("-PLAN.md", "-SUMMARY.md")
                    )
                    has_summary = summary_path.exists()

                    plans.append({
                        "path": str(plan_file),
                        "name": plan_file.stem,
                        "tasks": len(plan_data["tasks"]),
                        "completed": has_summary,
                        "wave": plan_data["frontmatter"].get("wave", 1),
                    })

    return plans


def _extract_plan_num(filename: str) -> int:
    """Extract plan number from filename."""
    # Match patterns like "02-03-PLAN.md" or "phase-02-plan-03-PLAN.md"
    match = re.search(r'(\d+)-(\d+)', filename)
    if match:
        return int(match.group(2))
    return 1


def get_phase_assumptions(
    phase: int, project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Get assumptions made when planning a phase.

    Extracts decisions, patterns, and architectural choices from plan files.
    """
    plans = list_phase_plans(phase, project_path)
    if not plans:
        return {"error": f"No plans found for phase {phase}"}

    assumptions = {
        "phase": phase,
        "patterns": [],
        "decisions": [],
        "dependencies": [],
        "file_structure": [],
        "technologies": [],
    }

    for plan_info in plans:
        plan_data = load_plan(phase, _extract_plan_num(plan_info["path"]), project_path)
        if not plan_data:
            continue

        fm = plan_data["frontmatter"]

        # Extract dependencies
        if fm.get("depends_on"):
            assumptions["dependencies"].extend(fm["depends_on"])

        # Extract technologies from must_haves
        must_haves = fm.get("must_haves", {})
        if must_haves.get("artifacts"):
            for artifact in must_haves["artifacts"]:
                if isinstance(artifact, dict):
                    assumptions["file_structure"].append(artifact.get("path", ""))

        # Extract patterns from tasks
        for task in plan_data["tasks"]:
            action = task.get("action", "")
            # Look for pattern keywords
            if "pattern" in action.lower():
                assumptions["patterns"].append(action[:200])
            # Look for decisions
            if any(kw in action.lower() for kw in ["decided", "chose", "using", "instead of"]):
                assumptions["decisions"].append(action[:200])

    # Deduplicate
    assumptions["dependencies"] = list(set(assumptions["dependencies"]))
    assumptions["file_structure"] = list(set(assumptions["file_structure"]))

    return assumptions
