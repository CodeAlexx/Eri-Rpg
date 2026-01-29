"""
State tracking for orchestration mode.

Tracks current task, phase, and history to guide users
through multi-step workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import os


@dataclass
class State:
    """Orchestration state for tracking progress.

    Valid phases:
    - "idle": No active task
    - "extracting": Extracting feature from source project
    - "planning": Creating transplant plan
    - "building": Creating new project structure (new mode)
    - "context_ready": Context generated, waiting for Claude
    - "implementing": Claude is implementing
    - "validating": Validating implementation
    - "done": Task complete
    """
    active_project: Optional[str] = None  # Currently active project name
    current_task: Optional[str] = None
    phase: str = "idle"
    waiting_on: Optional[str] = None  # "user" | "claude" | None
    context_file: Optional[str] = None
    feature_file: Optional[str] = None
    plan_file: Optional[str] = None
    history: List[Dict] = field(default_factory=list)

    _state_dir: str = field(default="", repr=False)

    def __post_init__(self):
        if not self._state_dir:
            self._state_dir = os.path.expanduser("~/.eri-rpg")
        self._state_path = os.path.join(self._state_dir, "state.json")

    def update(self, **kwargs) -> None:
        """Update state fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def log(self, action: str, details: str = "") -> None:
        """Log an action to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "phase": self.phase,
        }
        self.history.append(entry)
        self.save()

    def reset(self) -> None:
        """Reset state to idle."""
        self.current_task = None
        self.phase = "idle"
        self.waiting_on = None
        self.context_file = None
        self.feature_file = None
        self.plan_file = None
        # Note: active_project is NOT reset - it persists across sessions
        self.save()

    def set_active_project(self, name: str) -> None:
        """Set the active project."""
        self.active_project = name
        self.save()

    def get_active_project(self) -> Optional[str]:
        """Get the active project name."""
        return self.active_project

    def get_next_step(self) -> str:
        """Get recommended next step based on current state."""
        if self.phase == "idle":
            return "Start a task with: eri-rpg do '<task description>'"

        elif self.phase == "extracting":
            if self.feature_file:
                return f"Feature extracted to {self.feature_file}. Plan with: eri-rpg plan {self.feature_file} <target>"
            return "Extracting feature..."

        elif self.phase == "planning":
            if self.plan_file:
                return f"Plan created at {self.plan_file}. Generate context with: eri-rpg context {self.feature_file} <target>"
            return "Planning transplant..."

        elif self.phase == "building":
            if self.context_file:
                return f"Project spec created at {self.context_file}. Give it to Claude Code to build."
            return "Building project structure..."

        elif self.phase == "context_ready":
            return f"Give Claude Code the context at {self.context_file}\nAfter implementation, run: eri-rpg validate"

        elif self.phase == "implementing":
            return "Waiting for Claude Code to implement. When done: eri-rpg validate"

        elif self.phase == "validating":
            return "Validating implementation..."

        elif self.phase == "done":
            return "Task complete! Start a new task or run: eri-rpg status"

        return "Unknown state. Run: eri-rpg status"

    def save(self) -> None:
        """Save state to disk."""
        os.makedirs(self._state_dir, exist_ok=True)

        data = {
            "active_project": self.active_project,
            "current_task": self.current_task,
            "phase": self.phase,
            "waiting_on": self.waiting_on,
            "context_file": self.context_file,
            "feature_file": self.feature_file,
            "plan_file": self.plan_file,
            "history": self.history[-50:],  # Keep last 50 entries
        }

        with open(self._state_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "State":
        """Load state from disk."""
        state_dir = os.path.expanduser("~/.eri-rpg")
        state_path = os.path.join(state_dir, "state.json")

        state = cls(_state_dir=state_dir)

        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                data = json.load(f)
            state.active_project = data.get("active_project")
            state.current_task = data.get("current_task")
            state.phase = data.get("phase", "idle")
            state.waiting_on = data.get("waiting_on")
            state.context_file = data.get("context_file")
            state.feature_file = data.get("feature_file")
            state.plan_file = data.get("plan_file")
            state.history = data.get("history", [])

        return state

    def format_status(self) -> str:
        """Format current status for display."""
        lines = []

        if self.active_project:
            lines.append(f"Active project: {self.active_project}")

        if self.current_task:
            lines.append(f"Current task: {self.current_task}")
        else:
            lines.append("No active task")

        lines.append(f"Phase: {self.phase}")

        if self.waiting_on:
            lines.append(f"Waiting on: {self.waiting_on}")

        if self.feature_file:
            lines.append(f"Feature: {self.feature_file}")
        if self.plan_file:
            lines.append(f"Plan: {self.plan_file}")
        if self.context_file:
            lines.append(f"Context: {self.context_file}")

        lines.append("")
        lines.append(f"Next step: {self.get_next_step()}")

        return "\n".join(lines)
