"""
Task model for plan execution.

Tasks are the atomic units of work within a plan.
XML format in files, structured here for processing.

Task types:
- auto: Fully automated, no human needed
- checkpoint:human-verify: Human must verify completion
- checkpoint:decision: Human must make a decision
- checkpoint:human-action: Human must perform an action

TDD tasks have behavior and implementation sections.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(Enum):
    """Type of task execution."""
    AUTO = "auto"
    CHECKPOINT_VERIFY = "checkpoint:human-verify"
    CHECKPOINT_DECISION = "checkpoint:decision"
    CHECKPOINT_ACTION = "checkpoint:human-action"


class TaskStatus(Enum):
    """Status of task execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Waiting on checkpoint


@dataclass
class Task:
    """A task within a plan.

    Standard task structure:
    - name: Task name
    - files: Files to be modified
    - action: What to do
    - verify: How to verify success
    - done: Criteria for completion

    TDD tasks add:
    - behavior: Test specification
    - implementation: Implementation approach
    """
    name: str
    task_type: TaskType = TaskType.AUTO

    # Standard fields
    files: List[str] = field(default_factory=list)
    action: str = ""
    verify: str = ""
    done: str = ""

    # TDD fields (optional)
    tdd: bool = False
    behavior: str = ""
    implementation: str = ""

    # Checkpoint fields (for non-auto tasks)
    checkpoint_details: str = ""  # What human needs to do/verify
    awaiting: str = ""  # What we're waiting for

    # Execution state
    status: TaskStatus = TaskStatus.PENDING
    commit_hash: Optional[str] = None
    files_touched: List[str] = field(default_factory=list)
    notes: str = ""

    # Timestamps
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.task_type.value,
            "files": self.files,
            "action": self.action,
            "verify": self.verify,
            "done": self.done,
            "tdd": self.tdd,
            "behavior": self.behavior,
            "implementation": self.implementation,
            "checkpoint_details": self.checkpoint_details,
            "awaiting": self.awaiting,
            "status": self.status.value,
            "commit_hash": self.commit_hash,
            "files_touched": self.files_touched,
            "notes": self.notes,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task_type_str = data.get("type", "auto")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.AUTO

        status_str = data.get("status", "pending")
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING

        return cls(
            name=data.get("name", ""),
            task_type=task_type,
            files=data.get("files", []),
            action=data.get("action", ""),
            verify=data.get("verify", ""),
            done=data.get("done", ""),
            tdd=data.get("tdd", False),
            behavior=data.get("behavior", ""),
            implementation=data.get("implementation", ""),
            checkpoint_details=data.get("checkpoint_details", ""),
            awaiting=data.get("awaiting", ""),
            status=status,
            commit_hash=data.get("commit_hash"),
            files_touched=data.get("files_touched", []),
            notes=data.get("notes", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )

    def is_checkpoint(self) -> bool:
        """Check if this task requires human interaction."""
        return self.task_type != TaskType.AUTO

    def is_auto(self) -> bool:
        """Check if this task is fully automated."""
        return self.task_type == TaskType.AUTO

    def is_complete(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.COMPLETED

    def is_blocked(self) -> bool:
        """Check if task is blocked on checkpoint."""
        return self.status == TaskStatus.BLOCKED

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now().isoformat()

    def mark_completed(self, commit_hash: Optional[str] = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        if commit_hash:
            self.commit_hash = commit_hash

    def mark_failed(self, notes: str = "") -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now().isoformat()
        self.notes = notes

    def mark_blocked(self) -> None:
        """Mark task as blocked on checkpoint."""
        self.status = TaskStatus.BLOCKED

    def validate(self) -> List[str]:
        """Validate task structure. Returns list of errors."""
        errors = []

        if not self.name:
            errors.append("Task has no name")

        if self.is_auto():
            if not self.files:
                errors.append(f"Auto task '{self.name}' has no files")
            if not self.action:
                errors.append(f"Auto task '{self.name}' has no action")
            if not self.verify:
                errors.append(f"Auto task '{self.name}' has no verify")
            if not self.done:
                errors.append(f"Auto task '{self.name}' has no done criteria")

            if self.tdd:
                if not self.behavior:
                    errors.append(f"TDD task '{self.name}' has no behavior")
                if not self.implementation:
                    errors.append(f"TDD task '{self.name}' has no implementation")

        else:
            # Checkpoint tasks need details
            if not self.checkpoint_details:
                errors.append(f"Checkpoint task '{self.name}' has no checkpoint_details")
            if not self.awaiting:
                errors.append(f"Checkpoint task '{self.name}' has no awaiting")

        return errors

    def to_xml(self) -> str:
        """Convert task to XML format for plan files."""
        tdd_attr = ' tdd="true"' if self.tdd else ""
        lines = [f'<task type="{self.task_type.value}"{tdd_attr}>']
        lines.append(f"  <name>{self.name}</name>")

        if self.files:
            files_str = ", ".join(self.files)
            lines.append(f"  <files>{files_str}</files>")

        if self.action:
            lines.append(f"  <action>{self.action}</action>")

        if self.tdd:
            lines.append(f"  <behavior>{self.behavior}</behavior>")
            lines.append(f"  <implementation>{self.implementation}</implementation>")

        if self.verify:
            lines.append(f"  <verify>{self.verify}</verify>")

        if self.done:
            lines.append(f"  <done>{self.done}</done>")

        if self.checkpoint_details:
            lines.append(f"  <checkpoint_details>{self.checkpoint_details}</checkpoint_details>")

        if self.awaiting:
            lines.append(f"  <awaiting>{self.awaiting}</awaiting>")

        lines.append("</task>")
        return "\n".join(lines)

    @classmethod
    def from_xml(cls, xml_str: str) -> "Task":
        """Parse task from XML string."""
        import re

        # Extract type attribute
        type_match = re.search(r'type="([^"]+)"', xml_str)
        task_type_str = type_match.group(1) if type_match else "auto"
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.AUTO

        # Extract TDD attribute
        tdd = 'tdd="true"' in xml_str

        # Helper to extract tag content
        def get_tag(tag: str) -> str:
            match = re.search(f"<{tag}>(.+?)</{tag}>", xml_str, re.DOTALL)
            return match.group(1).strip() if match else ""

        # Extract files (comma-separated)
        files_str = get_tag("files")
        files = [f.strip() for f in files_str.split(",")] if files_str else []

        return cls(
            name=get_tag("name"),
            task_type=task_type,
            files=files,
            action=get_tag("action"),
            verify=get_tag("verify"),
            done=get_tag("done"),
            tdd=tdd,
            behavior=get_tag("behavior"),
            implementation=get_tag("implementation"),
            checkpoint_details=get_tag("checkpoint_details"),
            awaiting=get_tag("awaiting"),
        )


def parse_tasks_from_plan_md(content: str) -> List[Task]:
    """Parse tasks from plan markdown file.

    Looks for <tasks>...</tasks> section and extracts
    individual <task>...</task> elements.
    """
    import re

    # Find tasks section
    tasks_match = re.search(r"<tasks>(.*?)</tasks>", content, re.DOTALL)
    if not tasks_match:
        return []

    tasks_content = tasks_match.group(1)

    # Find individual tasks
    task_matches = re.findall(r"<task[^>]*>.*?</task>", tasks_content, re.DOTALL)

    return [Task.from_xml(task_xml) for task_xml in task_matches]
