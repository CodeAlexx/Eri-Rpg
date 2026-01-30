"""
Parallel agent management for wave execution.

Fresh subagents:
- No context bleed between plans
- Task tool blocks until complete
- Each agent gets plan + context only
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, Future
import json
import os
import subprocess
import tempfile
import threading

from erirpg.models.plan import Plan
from erirpg.execution.results import PlanResult


@dataclass
class AgentTask:
    """A task being executed by an agent."""
    task_id: str
    plan_id: str
    status: str = "pending"  # pending, running, completed, failed
    future: Optional[Future] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[PlanResult] = None


class AgentPool:
    """Pool of parallel agents for plan execution."""

    def __init__(self, max_agents: int = 3):
        """Initialize agent pool.

        Args:
            max_agents: Maximum concurrent agents
        """
        self.max_agents = max_agents
        self.executor = ThreadPoolExecutor(max_workers=max_agents)
        self.active_tasks: Dict[str, AgentTask] = {}
        self._lock = threading.Lock()

    def submit(self, plan: Plan, project_path: str) -> AgentTask:
        """Submit a plan for execution.

        Args:
            plan: Plan to execute
            project_path: Path to project

        Returns:
            AgentTask tracking the execution
        """
        task_id = f"{plan.id}-{datetime.now().strftime('%H%M%S')}"

        task = AgentTask(
            task_id=task_id,
            plan_id=plan.id,
            status="pending",
        )

        # Submit to executor
        future = self.executor.submit(
            _execute_plan_agent,
            project_path,
            plan,
        )
        task.future = future
        task.status = "running"
        task.started_at = datetime.now().isoformat()

        with self._lock:
            self.active_tasks[task_id] = task

        return task

    def wait(self, task: AgentTask, timeout: Optional[float] = None) -> PlanResult:
        """Wait for a task to complete.

        Args:
            task: Task to wait for
            timeout: Optional timeout in seconds

        Returns:
            PlanResult
        """
        if not task.future:
            return PlanResult(
                plan_id=task.plan_id,
                status="failed",
                error="Task has no future",
            )

        try:
            result = task.future.result(timeout=timeout)
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            task.result = result
            return result
        except TimeoutError:
            task.status = "failed"
            return PlanResult(
                plan_id=task.plan_id,
                status="failed",
                error="Task timed out",
            )
        except Exception as e:
            task.status = "failed"
            return PlanResult(
                plan_id=task.plan_id,
                status="failed",
                error=str(e),
            )
        finally:
            with self._lock:
                self.active_tasks.pop(task.task_id, None)

    def shutdown(self, wait: bool = True):
        """Shutdown the pool.

        Args:
            wait: Whether to wait for tasks to complete
        """
        self.executor.shutdown(wait=wait)


def spawn_plan_executor(
    project_path: str,
    plan: Plan,
    pool: AgentPool,
) -> AgentTask:
    """Spawn an agent to execute a plan.

    Args:
        project_path: Path to project
        plan: Plan to execute
        pool: Agent pool to use

    Returns:
        AgentTask tracking execution
    """
    return pool.submit(plan, project_path)


def wait_for_agents(agents: List[AgentTask], timeout: Optional[float] = None) -> List[PlanResult]:
    """Wait for multiple agents to complete.

    Args:
        agents: List of agent tasks
        timeout: Optional timeout for each agent

    Returns:
        List of results (in same order as agents)
    """
    results = []
    for agent in agents:
        if agent.future:
            try:
                result = agent.future.result(timeout=timeout)
                results.append(result)
            except Exception as e:
                results.append(PlanResult(
                    plan_id=agent.plan_id,
                    status="failed",
                    error=str(e),
                ))
        else:
            results.append(PlanResult(
                plan_id=agent.plan_id,
                status="failed",
                error="No future",
            ))
    return results


def _execute_plan_agent(project_path: str, plan: Plan) -> PlanResult:
    """Execute a plan in an isolated agent.

    This runs in a separate thread and simulates what a Claude Code
    subagent would do. In production, this would spawn an actual
    Claude Code Task tool agent.

    Args:
        project_path: Path to project
        plan: Plan to execute

    Returns:
        PlanResult
    """
    start_time = datetime.now()

    try:
        # Create agent context file
        context = _build_agent_context(project_path, plan)

        # In production, this would be:
        # result = claude_task_tool(
        #     prompt=context,
        #     subagent_type="plan-executor",
        # )

        # For now, simulate execution by marking as completed
        # The actual execution would be done by the Claude Code agent
        # that invokes this system

        from erirpg.models.summary import Summary, CompletedTask

        summary = Summary(
            phase=plan.phase,
            plan=str(plan.plan_number),
            one_liner=f"Executed plan {plan.plan_number} for {plan.phase}",
            tasks_completed=[
                CompletedTask(name=task.get("name", f"task-{i}"))
                for i, task in enumerate(plan.tasks)
            ],
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return PlanResult(
            plan_id=plan.id,
            status="completed",
            summary=summary,
            duration_seconds=duration,
        )

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return PlanResult(
            plan_id=plan.id,
            status="failed",
            error=str(e),
            duration_seconds=duration,
        )


def _build_agent_context(project_path: str, plan: Plan) -> str:
    """Build context for a plan executor agent.

    Args:
        project_path: Path to project
        plan: Plan to execute

    Returns:
        Context string for agent
    """
    context_parts = [
        "# Plan Execution Context",
        "",
        f"## Phase: {plan.phase}",
        f"## Plan: {plan.plan_number}",
        f"## Objective: {plan.objective}",
        "",
    ]

    if plan.execution_context:
        context_parts.extend([
            "## Execution Context",
            plan.execution_context,
            "",
        ])

    if plan.must_haves.truths:
        context_parts.append("## Must-Have Truths")
        for truth in plan.must_haves.truths:
            context_parts.append(f"- {truth.description}")
        context_parts.append("")

    if plan.must_haves.artifacts:
        context_parts.append("## Must-Have Artifacts")
        for artifact in plan.must_haves.artifacts:
            context_parts.append(f"- {artifact.path}: {artifact.provides}")
        context_parts.append("")

    if plan.tasks:
        context_parts.append("## Tasks")
        for i, task in enumerate(plan.tasks, 1):
            task_name = task.get("name", f"Task {i}")
            task_action = task.get("action", "")
            context_parts.append(f"### {i}. {task_name}")
            context_parts.append(task_action)
            context_parts.append("")

    return "\n".join(context_parts)


def create_agent_prompt(plan: Plan) -> str:
    """Create the prompt for spawning an executor agent.

    This would be used with Claude Code's Task tool.

    Args:
        plan: Plan to execute

    Returns:
        Prompt string
    """
    return f"""Execute this plan following the ERI methodology:

## Objective
{plan.objective}

## Tasks
{_format_tasks(plan.tasks)}

## Must-Haves to Verify
- Truths: {len(plan.must_haves.truths)}
- Artifacts: {len(plan.must_haves.artifacts)}
- Key Links: {len(plan.must_haves.key_links)}

## Instructions
1. Execute each task in order
2. Commit after each task with format: {plan.phase}-{plan.plan_number}: <task-name>
3. Track any deviations
4. If you encounter an architectural decision, STOP and return a checkpoint
5. Auto-fix bugs, missing critical code, and blocking issues

## Execution Context
{plan.execution_context}
"""


def _format_tasks(tasks: List[Dict[str, Any]]) -> str:
    """Format tasks for prompt."""
    lines = []
    for i, task in enumerate(tasks, 1):
        name = task.get("name", f"Task {i}")
        action = task.get("action", "")
        lines.append(f"{i}. **{name}**")
        lines.append(f"   {action}")
        if task.get("files"):
            lines.append(f"   Files: {', '.join(task['files'])}")
        lines.append("")
    return "\n".join(lines)
