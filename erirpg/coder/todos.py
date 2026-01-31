"""
Todo management for coder workflow.

Commands:
- add-todo: Capture ideas for later implementation
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import get_planning_dir, ensure_planning_dir, timestamp


def get_todos_path(project_path: Optional[Path] = None) -> Path:
    """Get path to todos.json."""
    return get_planning_dir(project_path) / "todos.json"


def load_todos(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load todos from .planning/todos.json."""
    todos_path = get_todos_path(project_path)
    if todos_path.exists():
        return json.loads(todos_path.read_text())
    return {
        "pending": [],
        "completed": [],
    }


def save_todos(todos: Dict[str, Any], project_path: Optional[Path] = None) -> None:
    """Save todos to .planning/todos.json."""
    ensure_planning_dir(project_path)
    todos_path = get_todos_path(project_path)
    todos_path.write_text(json.dumps(todos, indent=2))


def add_todo(
    description: str,
    priority: str = "medium",
    phase: Optional[int] = None,
    tags: Optional[List[str]] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Add a todo item.

    Args:
        description: What needs to be done
        priority: high, medium, or low
        phase: Optional phase this relates to
        tags: Optional tags for categorization
        project_path: Project path

    Returns:
        The created todo
    """
    todos = load_todos(project_path)

    todo = {
        "id": len(todos["pending"]) + len(todos["completed"]) + 1,
        "description": description,
        "priority": priority,
        "phase": phase,
        "tags": tags or [],
        "created_at": timestamp(),
        "status": "pending",
    }

    todos["pending"].append(todo)
    save_todos(todos, project_path)

    return todo


def complete_todo(
    todo_id: int,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Mark a todo as complete.

    Args:
        todo_id: ID of the todo to complete
        project_path: Project path

    Returns:
        The completed todo
    """
    todos = load_todos(project_path)

    # Find todo
    todo = None
    for i, t in enumerate(todos["pending"]):
        if t["id"] == todo_id:
            todo = todos["pending"].pop(i)
            break

    if not todo:
        return {"error": f"Todo {todo_id} not found in pending"}

    todo["status"] = "completed"
    todo["completed_at"] = timestamp()

    todos["completed"].append(todo)
    save_todos(todos, project_path)

    return todo


def delete_todo(
    todo_id: int,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Delete a todo.

    Args:
        todo_id: ID of the todo to delete
        project_path: Project path
    """
    todos = load_todos(project_path)

    # Check pending
    for i, t in enumerate(todos["pending"]):
        if t["id"] == todo_id:
            deleted = todos["pending"].pop(i)
            save_todos(todos, project_path)
            return {"deleted": deleted}

    # Check completed
    for i, t in enumerate(todos["completed"]):
        if t["id"] == todo_id:
            deleted = todos["completed"].pop(i)
            save_todos(todos, project_path)
            return {"deleted": deleted}

    return {"error": f"Todo {todo_id} not found"}


def list_todos(
    status: str = "all",
    priority: Optional[str] = None,
    phase: Optional[int] = None,
    project_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """List todos with optional filters.

    Args:
        status: "pending", "completed", or "all"
        priority: Filter by priority
        phase: Filter by phase
        project_path: Project path
    """
    todos = load_todos(project_path)

    result = []

    if status in ("pending", "all"):
        result.extend(todos["pending"])

    if status in ("completed", "all"):
        result.extend(todos["completed"])

    # Apply filters
    if priority:
        result = [t for t in result if t.get("priority") == priority]

    if phase is not None:
        result = [t for t in result if t.get("phase") == phase]

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    result.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

    return result


def get_todo(
    todo_id: int,
    project_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Get a specific todo by ID."""
    todos = load_todos(project_path)

    for t in todos["pending"] + todos["completed"]:
        if t["id"] == todo_id:
            return t

    return None


def update_todo(
    todo_id: int,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    phase: Optional[int] = None,
    tags: Optional[List[str]] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Update a todo item.

    Args:
        todo_id: ID of the todo to update
        description: New description
        priority: New priority
        phase: New phase
        tags: New tags
        project_path: Project path
    """
    todos = load_todos(project_path)

    # Find todo in pending
    for todo in todos["pending"]:
        if todo["id"] == todo_id:
            if description is not None:
                todo["description"] = description
            if priority is not None:
                todo["priority"] = priority
            if phase is not None:
                todo["phase"] = phase
            if tags is not None:
                todo["tags"] = tags
            todo["updated_at"] = timestamp()

            save_todos(todos, project_path)
            return todo

    return {"error": f"Todo {todo_id} not found in pending (cannot update completed todos)"}


def promote_todo_to_phase(
    todo_id: int,
    phase: int,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Promote a todo to a phase requirement.

    This marks the todo as promoted and adds it to the phase context.
    """
    todo = get_todo(todo_id, project_path)
    if not todo:
        return {"error": f"Todo {todo_id} not found"}

    # Mark as completed with promotion note
    todos = load_todos(project_path)
    for i, t in enumerate(todos["pending"]):
        if t["id"] == todo_id:
            t["status"] = "promoted"
            t["promoted_to_phase"] = phase
            t["promoted_at"] = timestamp()
            todos["completed"].append(todos["pending"].pop(i))
            break

    save_todos(todos, project_path)

    return {
        "promoted": True,
        "todo": todo,
        "phase": phase,
        "action": f"Add to /coder:discuss-phase {phase}",
    }


def get_todos_summary(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get summary of todos."""
    todos = load_todos(project_path)

    pending = todos["pending"]
    completed = todos["completed"]

    # Count by priority
    by_priority = {"high": 0, "medium": 0, "low": 0}
    for t in pending:
        p = t.get("priority", "medium")
        by_priority[p] = by_priority.get(p, 0) + 1

    # Count by phase
    by_phase = {}
    for t in pending:
        phase = t.get("phase")
        if phase:
            by_phase[phase] = by_phase.get(phase, 0) + 1

    return {
        "pending_count": len(pending),
        "completed_count": len(completed),
        "by_priority": by_priority,
        "by_phase": by_phase,
        "high_priority": [t for t in pending if t.get("priority") == "high"],
    }


def update_state_todos(project_path: Optional[Path] = None) -> None:
    """Update STATE.md with pending todos section."""
    planning_dir = get_planning_dir(project_path)
    state_path = planning_dir / "STATE.md"

    if not state_path.exists():
        return

    todos = load_todos(project_path)
    pending = todos["pending"]

    if not pending:
        return

    content = state_path.read_text()

    # Format todos section
    todos_section = "\n### Pending Todos\n"
    for t in pending[:10]:  # Limit to 10
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "🟡")
        todos_section += f"- {priority_icon} [{t['id']}] {t['description']}\n"

    # Update or add section
    if "### Pending Todos" in content:
        # Replace existing section
        parts = content.split("### Pending Todos")
        before = parts[0]
        after_parts = parts[1].split("\n###") if "\n###" in parts[1] else [parts[1]]
        after = "\n###".join(after_parts[1:]) if len(after_parts) > 1 else ""
        content = before + todos_section + ("\n###" + after if after else "")
    elif "## Accumulated Context" in content:
        # Add under Accumulated Context
        content = content.replace(
            "## Accumulated Context",
            f"## Accumulated Context{todos_section}"
        )
    else:
        # Append
        content += "\n" + todos_section

    state_path.write_text(content)
