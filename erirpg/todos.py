"""
Personal TODO list for EriRPG.

Persists in ~/.eri-rpg/todos.json, shows at session start.
Quick task tracking that survives across sessions and projects.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def get_todos_path() -> Path:
    """Get path to global todos file."""
    p = Path.home() / ".eri-rpg" / "todos.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Todo:
    """A single todo item."""
    id: int
    text: str
    project: Optional[str] = None  # Optional project association
    priority: str = "normal"  # low, normal, high, urgent
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def is_done(self) -> bool:
        return self.completed_at is not None

    def complete(self) -> None:
        self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Todo":
        return cls(
            id=d["id"],
            text=d["text"],
            project=d.get("project"),
            priority=d.get("priority", "normal"),
            created_at=d.get("created_at", datetime.now().isoformat()),
            completed_at=d.get("completed_at"),
            tags=d.get("tags", []),
        )


@dataclass
class TodoList:
    """Collection of todos with persistence."""
    todos: List[Todo] = field(default_factory=list)
    next_id: int = 1

    def add(self, text: str, project: str = None, priority: str = "normal", tags: List[str] = None) -> Todo:
        """Add a new todo."""
        todo = Todo(
            id=self.next_id,
            text=text,
            project=project,
            priority=priority,
            tags=tags or [],
        )
        self.todos.append(todo)
        self.next_id += 1
        return todo

    def get(self, todo_id: int) -> Optional[Todo]:
        """Get a todo by ID."""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def complete(self, todo_id: int) -> Optional[Todo]:
        """Mark a todo as complete."""
        todo = self.get(todo_id)
        if todo:
            todo.complete()
        return todo

    def remove(self, todo_id: int) -> bool:
        """Remove a todo entirely."""
        for i, todo in enumerate(self.todos):
            if todo.id == todo_id:
                self.todos.pop(i)
                return True
        return False

    def pending(self, project: str = None) -> List[Todo]:
        """Get pending (incomplete) todos, optionally filtered by project."""
        result = [t for t in self.todos if not t.is_done()]
        if project:
            result = [t for t in result if t.project == project]
        return result

    def completed(self, limit: int = 10) -> List[Todo]:
        """Get recently completed todos."""
        done = [t for t in self.todos if t.is_done()]
        done.sort(key=lambda t: t.completed_at or "", reverse=True)
        return done[:limit]

    def by_priority(self) -> List[Todo]:
        """Get pending todos sorted by priority."""
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        pending = self.pending()
        pending.sort(key=lambda t: priority_order.get(t.priority, 2))
        return pending

    def clear_completed(self) -> int:
        """Remove all completed todos. Returns count removed."""
        before = len(self.todos)
        self.todos = [t for t in self.todos if not t.is_done()]
        return before - len(self.todos)

    def to_dict(self) -> dict:
        return {
            "todos": [t.to_dict() for t in self.todos],
            "next_id": self.next_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TodoList":
        return cls(
            todos=[Todo.from_dict(t) for t in d.get("todos", [])],
            next_id=d.get("next_id", 1),
        )


def load_todos() -> TodoList:
    """Load todos from disk."""
    path = get_todos_path()
    if not path.exists():
        return TodoList()
    try:
        with open(path) as f:
            data = json.load(f)
        return TodoList.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return TodoList()


def save_todos(todo_list: TodoList) -> None:
    """Save todos to disk."""
    path = get_todos_path()
    with open(path, "w") as f:
        json.dump(todo_list.to_dict(), f, indent=2)


def add_todo(text: str, project: str = None, priority: str = "normal", tags: List[str] = None) -> Todo:
    """Add a todo and save."""
    todos = load_todos()
    todo = todos.add(text, project, priority, tags)
    save_todos(todos)
    return todo


def complete_todo(todo_id: int) -> Optional[Todo]:
    """Complete a todo and save."""
    todos = load_todos()
    todo = todos.complete(todo_id)
    if todo:
        save_todos(todos)
    return todo


def remove_todo(todo_id: int) -> bool:
    """Remove a todo and save."""
    todos = load_todos()
    if todos.remove(todo_id):
        save_todos(todos)
        return True
    return False


def clear_completed() -> int:
    """Clear completed todos and save."""
    todos = load_todos()
    count = todos.clear_completed()
    save_todos(todos)
    return count


def format_todo(todo: Todo, show_project: bool = True) -> str:
    """Format a single todo for display."""
    priority_icons = {
        "urgent": "🔴",
        "high": "🟠",
        "normal": "⚪",
        "low": "🔵",
    }
    icon = priority_icons.get(todo.priority, "⚪")
    status = "✅" if todo.is_done() else f"[{todo.id}]"

    parts = [f"{status} {icon} {todo.text}"]

    if show_project and todo.project:
        parts.append(f"@{todo.project}")

    if todo.tags:
        parts.append(" ".join(f"#{t}" for t in todo.tags))

    return " ".join(parts)


def format_todo_list(todos: List[Todo], title: str = "Todos", show_project: bool = True) -> str:
    """Format a list of todos for display."""
    if not todos:
        return f"{title}: (none)"

    lines = [f"{title}:"]
    for todo in todos:
        lines.append(f"  {format_todo(todo, show_project)}")
    return "\n".join(lines)


def get_session_summary() -> str:
    """Get a summary for session start."""
    todos = load_todos()
    pending = todos.by_priority()

    if not pending:
        return ""

    lines = [f"📋 {len(pending)} pending todo(s):"]

    # Show up to 5 most important
    for todo in pending[:5]:
        lines.append(f"  {format_todo(todo)}")

    if len(pending) > 5:
        lines.append(f"  ... and {len(pending) - 5} more")

    return "\n".join(lines)
