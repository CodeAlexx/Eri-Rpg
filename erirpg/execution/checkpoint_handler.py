"""
Checkpoint handling for human-in-the-loop execution.

When a checkpoint is hit:
1. Serialize current state
2. Return checkpoint to user
3. User provides response
4. Spawn FRESH continuation agent with:
   - Completed tasks
   - Resume point
   - User response

Important: Continuation spawns a NEW agent, not resume.
This prevents context bleed.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import os

from erirpg.models.plan import Plan
from erirpg.models.checkpoint import (
    Checkpoint,
    CheckpointState,
    CheckpointType,
    CompletedTask,
    save_checkpoint,
    load_checkpoint,
)


class CheckpointHandler:
    """Handles checkpoint creation and continuation."""

    def __init__(self, project_path: str):
        """Initialize checkpoint handler.

        Args:
            project_path: Path to project root
        """
        self.project_path = project_path

    def create_checkpoint(
        self,
        plan: Plan,
        checkpoint_type: CheckpointType,
        current_task_index: int,
        completed_tasks: List[CompletedTask],
        blocker: str,
        awaiting: str,
        execution_context: str = "",
    ) -> Checkpoint:
        """Create a checkpoint at the current execution point.

        Args:
            plan: Plan being executed
            checkpoint_type: Type of checkpoint
            current_task_index: Index of current task
            completed_tasks: Tasks completed so far
            blocker: What's blocking progress
            awaiting: What we're waiting for from user
            execution_context: Context for continuation

        Returns:
            Created Checkpoint
        """
        current_task_name = ""
        if current_task_index < len(plan.tasks):
            current_task_name = plan.tasks[current_task_index].get("name", "")

        state = CheckpointState(
            checkpoint_id="",  # Will be generated
            plan_id=plan.id,
            phase=plan.phase,
            completed_tasks=completed_tasks,
            current_task_index=current_task_index,
            current_task_name=current_task_name,
            checkpoint_type=checkpoint_type,
            blocker=blocker,
            awaiting=awaiting,
            execution_context=execution_context,
        )

        checkpoint = Checkpoint(
            state=state,
            progress_display=f"{len(completed_tasks)} of {len(plan.tasks)} tasks completed",
        )

        # Save checkpoint
        save_checkpoint(self.project_path, checkpoint)

        return checkpoint

    def get_pending_checkpoint(self, plan_id: str = "") -> Optional[Checkpoint]:
        """Get a pending checkpoint for a plan.

        Args:
            plan_id: Plan ID to filter by (optional)

        Returns:
            Pending checkpoint if found
        """
        checkpoint_dir = os.path.join(self.project_path, ".eri-rpg", "checkpoints")
        if not os.path.exists(checkpoint_dir):
            return None

        for filename in os.listdir(checkpoint_dir):
            if filename.endswith(".json"):
                checkpoint_id = filename[:-5]
                checkpoint = load_checkpoint(self.project_path, checkpoint_id)

                if checkpoint and not checkpoint.state.is_resolved():
                    if not plan_id or checkpoint.state.plan_id == plan_id:
                        return checkpoint

        return None

    def resolve_checkpoint(self, checkpoint_id: str, response: str) -> Optional[Checkpoint]:
        """Resolve a checkpoint with user response.

        Args:
            checkpoint_id: Checkpoint ID
            response: User's response

        Returns:
            Resolved checkpoint
        """
        checkpoint = load_checkpoint(self.project_path, checkpoint_id)
        if not checkpoint:
            return None

        checkpoint.state.resolve(response)
        save_checkpoint(self.project_path, checkpoint)

        return checkpoint

    def build_continuation_context(self, checkpoint: Checkpoint) -> str:
        """Build context for spawning continuation agent.

        Args:
            checkpoint: Resolved checkpoint

        Returns:
            Context string for continuation agent
        """
        state = checkpoint.state
        lines = [
            "# Continuation Context",
            "",
            f"## Resuming plan: {state.plan_id}",
            f"## Phase: {state.phase}",
            "",
            "## Completed Tasks",
        ]

        for task in state.completed_tasks:
            commit = f" [{task.commit_hash[:8]}]" if task.commit_hash else ""
            lines.append(f"- ✓ {task.name}{commit}")

        lines.extend([
            "",
            f"## Resume From: Task {state.current_task_index + 1} - {state.current_task_name}",
            "",
            "## Checkpoint Resolution",
            f"Type: {state.checkpoint_type.value}",
            f"Blocker: {state.blocker}",
            f"Awaiting: {state.awaiting}",
            f"User Response: {state.user_response}",
        ])

        if state.execution_context:
            lines.extend([
                "",
                "## Execution Context",
                state.execution_context,
            ])

        return "\n".join(lines)


def create_checkpoint(
    project_path: str,
    plan: Plan,
    checkpoint_type: CheckpointType,
    current_task_index: int,
    completed_tasks: List[CompletedTask],
    blocker: str,
    awaiting: str,
) -> Checkpoint:
    """Convenience function to create a checkpoint.

    Args:
        project_path: Path to project root
        plan: Plan being executed
        checkpoint_type: Type of checkpoint
        current_task_index: Index of current task
        completed_tasks: Tasks completed so far
        blocker: What's blocking progress
        awaiting: What we're waiting for

    Returns:
        Created Checkpoint
    """
    handler = CheckpointHandler(project_path)
    return handler.create_checkpoint(
        plan=plan,
        checkpoint_type=checkpoint_type,
        current_task_index=current_task_index,
        completed_tasks=completed_tasks,
        blocker=blocker,
        awaiting=awaiting,
    )


def continue_from_checkpoint(
    project_path: str,
    checkpoint_id: str,
    response: str,
) -> Optional[str]:
    """Continue execution from a checkpoint.

    Args:
        project_path: Path to project root
        checkpoint_id: Checkpoint ID
        response: User's response

    Returns:
        Continuation context for spawning new agent, or None if checkpoint not found
    """
    handler = CheckpointHandler(project_path)

    # Resolve checkpoint
    checkpoint = handler.resolve_checkpoint(checkpoint_id, response)
    if not checkpoint:
        return None

    # Build continuation context
    return handler.build_continuation_context(checkpoint)


def create_continuation_prompt(checkpoint: Checkpoint) -> str:
    """Create the prompt for spawning a continuation agent.

    Args:
        checkpoint: Resolved checkpoint

    Returns:
        Prompt for Task tool
    """
    state = checkpoint.state

    completed_tasks_text = "\n".join(
        f"- Task {i+1}: {t.name} (commit: {t.commit_hash or 'pending'})"
        for i, t in enumerate(state.completed_tasks)
    )

    return f"""Continue executing plan from checkpoint.

## Plan: {state.plan_id}
## Phase: {state.phase}

## Already Completed
{completed_tasks_text}

## Resume From
Task {state.current_task_index + 1}: {state.current_task_name}

## Checkpoint Details
Type: {state.checkpoint_type.value}
Blocker: {state.blocker}
Awaiting: {state.awaiting}
User Response: {state.user_response}

## Instructions
1. Continue from task {state.current_task_index + 1}
2. The user has responded to the checkpoint - incorporate their response
3. Complete remaining tasks
4. Follow deviation rules for any new issues

{state.execution_context}
"""


def list_pending_checkpoints(project_path: str) -> List[Checkpoint]:
    """List all pending (unresolved) checkpoints.

    Args:
        project_path: Path to project root

    Returns:
        List of pending checkpoints
    """
    checkpoint_dir = os.path.join(project_path, ".eri-rpg", "checkpoints")
    if not os.path.exists(checkpoint_dir):
        return []

    checkpoints = []
    for filename in os.listdir(checkpoint_dir):
        if filename.endswith(".json"):
            checkpoint_id = filename[:-5]
            checkpoint = load_checkpoint(project_path, checkpoint_id)

            if checkpoint and not checkpoint.state.is_resolved():
                checkpoints.append(checkpoint)

    return checkpoints


def format_checkpoint_summary(checkpoints: List[Checkpoint]) -> str:
    """Format a summary of pending checkpoints.

    Args:
        checkpoints: List of checkpoints

    Returns:
        Formatted summary
    """
    if not checkpoints:
        return "No pending checkpoints."

    lines = [
        "Pending Checkpoints",
        "=" * 40,
    ]

    for cp in checkpoints:
        state = cp.state
        icon = {
            CheckpointType.HUMAN_VERIFY: "👁️",
            CheckpointType.DECISION: "❓",
            CheckpointType.HUMAN_ACTION: "🖐️",
        }.get(state.checkpoint_type, "?")

        lines.extend([
            f"\n{icon} {state.checkpoint_id}",
            f"   Plan: {state.plan_id}",
            f"   Type: {state.checkpoint_type.value}",
            f"   Blocker: {state.blocker}",
            f"   Awaiting: {state.awaiting}",
        ])

    return "\n".join(lines)
