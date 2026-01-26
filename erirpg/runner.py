"""
Runner for EriRPG.

Executes plans step-by-step with pause/resume support,
context generation, and checkpoint management.

Usage:
    plan = Plan.load("plan.json")
    runner = Runner(plan, project_path)
    runner.start()

    # Later, resume:
    runner = Runner.resume(run_id, project_path)
    runner.continue_run()
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import os
import shutil

from erirpg.planner import Plan, PlanStep, StepStatus, StepType
from erirpg.runs import (
    RunRecord,
    RunStatus,
    StepResult,
    create_run,
    load_run,
    save_run,
    get_run_dir,
    get_runs_dir,
)


@dataclass
class StepContext:
    """Context generated for a single step execution."""
    step_id: str
    step_type: str
    target: str
    action: str
    details: str

    # Relevant files and modules
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)

    # Knowledge context
    learnings: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)

    # Constraints and verification
    constraints: List[str] = field(default_factory=list)
    verify_command: str = ""

    # Generated content path
    context_file: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "target": self.target,
            "action": self.action,
            "details": self.details,
            "input_files": self.input_files,
            "output_files": self.output_files,
            "learnings": self.learnings,
            "patterns": self.patterns,
            "constraints": self.constraints,
            "verify_command": self.verify_command,
            "context_file": self.context_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepContext":
        """Deserialize from dictionary."""
        return cls(
            step_id=data.get("step_id", ""),
            step_type=data.get("step_type", ""),
            target=data.get("target", ""),
            action=data.get("action", ""),
            details=data.get("details", ""),
            input_files=data.get("input_files", []),
            output_files=data.get("output_files", []),
            learnings=data.get("learnings", []),
            patterns=data.get("patterns", []),
            constraints=data.get("constraints", []),
            verify_command=data.get("verify_command", ""),
            context_file=data.get("context_file", ""),
        )

    def format_for_claude(self) -> str:
        """Format context as markdown for Claude."""
        lines = [
            f"# Step: {self.action}",
            "",
            f"**Type:** {self.step_type}",
            f"**Target:** {self.target}",
            "",
        ]

        if self.details:
            lines.extend([
                "## Details",
                self.details,
                "",
            ])

        if self.input_files:
            lines.extend([
                "## Input Files",
                *[f"- {f}" for f in self.input_files],
                "",
            ])

        if self.output_files:
            lines.extend([
                "## Expected Outputs",
                *[f"- {f}" for f in self.output_files],
                "",
            ])

        if self.learnings:
            lines.extend([
                "## Relevant Knowledge",
            ])
            for learning in self.learnings:
                lines.append(f"### {learning.get('module', 'Unknown')}")
                lines.append(learning.get('summary', ''))
                if learning.get('gotchas'):
                    lines.append("**Gotchas:**")
                    for g in learning['gotchas']:
                        lines.append(f"- {g}")
                lines.append("")

        if self.patterns:
            lines.extend([
                "## Patterns to Follow",
                *[f"- {p}" for p in self.patterns],
                "",
            ])

        if self.constraints:
            lines.extend([
                "## Constraints",
                *[f"- {c}" for c in self.constraints],
                "",
            ])

        if self.verify_command:
            lines.extend([
                "## Verification",
                f"Run: `{self.verify_command}`",
                "",
            ])

        return "\n".join(lines)


def build_step_context(
    step: PlanStep,
    plan: Plan,
    project_path: str,
    graph: Any = None,
    knowledge: Any = None,
) -> StepContext:
    """Build focused context for a single step.

    Includes only the relevant files, learnings, and constraints
    needed for this specific step.
    """
    ctx = StepContext(
        step_id=step.id,
        step_type=step.step_type,
        target=step.target,
        action=step.action,
        details=step.details,
        input_files=step.inputs.copy(),
        output_files=step.outputs.copy(),
        verify_command=step.verify_command,
    )

    # Add constraints based on risk level
    if step.risk == "high" or step.risk == "critical":
        ctx.constraints.append(f"HIGH RISK: {step.risk_reason}")
        ctx.constraints.append("Verify changes carefully before proceeding")

    if step.risk == "critical":
        ctx.constraints.append("CRITICAL: Get explicit approval before modifying")

    # Add step-type specific constraints
    if step.step_type == StepType.CREATE.value:
        ctx.constraints.append("Create new file - do not overwrite existing")
    elif step.step_type == StepType.MODIFY.value:
        ctx.constraints.append("Modify existing file - preserve unrelated functionality")
    elif step.step_type == StepType.WIRE.value:
        ctx.constraints.append("Wire imports - maintain existing import structure")

    # Look up relevant learnings
    if knowledge and hasattr(knowledge, 'learnings'):
        # Get learnings for input files
        for input_file in step.inputs:
            learning = knowledge.learnings.get(input_file)
            if learning:
                ctx.learnings.append({
                    "module": input_file,
                    "summary": learning.summary,
                    "purpose": learning.purpose,
                    "gotchas": learning.gotchas,
                })

        # Get learnings for target if it's a module
        if step.target and step.target.endswith('.py'):
            learning = knowledge.learnings.get(step.target)
            if learning:
                ctx.learnings.append({
                    "module": step.target,
                    "summary": learning.summary,
                    "purpose": learning.purpose,
                    "gotchas": learning.gotchas,
                })

        # Add relevant patterns
        if hasattr(knowledge, 'patterns'):
            for name, desc in knowledge.patterns.items():
                # Include patterns that might be relevant
                if any(kw in step.action.lower() or kw in step.target.lower()
                       for kw in name.lower().split('_')):
                    ctx.patterns.append(f"{name}: {desc}")

    return ctx


def save_step_context(
    ctx: StepContext,
    run_dir: str,
) -> str:
    """Save step context to a file and return the path."""
    contexts_dir = os.path.join(run_dir, "contexts")
    os.makedirs(contexts_dir, exist_ok=True)

    # Save as markdown for Claude
    md_path = os.path.join(contexts_dir, f"{ctx.step_id}.md")
    with open(md_path, "w") as f:
        f.write(ctx.format_for_claude())

    # Also save as JSON for programmatic access
    json_path = os.path.join(contexts_dir, f"{ctx.step_id}.json")
    with open(json_path, "w") as f:
        json.dump(ctx.to_dict(), f, indent=2)

    ctx.context_file = md_path
    return md_path


class Runner:
    """Orchestrates plan execution with checkpoints."""

    def __init__(
        self,
        plan: Plan,
        project_path: str,
        graph: Any = None,
        knowledge: Any = None,
        verification_config: Any = None,
    ):
        self.plan = plan
        self.project_path = project_path
        self.graph = graph
        self.knowledge = knowledge
        self.run: Optional[RunRecord] = None
        self._step_handlers: Dict[str, Callable] = {}
        self._verification_config = verification_config
        self._verifier = None

    @classmethod
    def resume(cls, run_id: str, project_path: str) -> "Runner":
        """Resume a previous run."""
        run = load_run(project_path, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        plan = Plan.load(run.plan_path)

        # Restore step statuses from run record
        for step_result in run.step_results:
            step = plan.get_step(step_result.step_id)
            if step:
                step.status = step_result.status
                step.error = step_result.error or ""

        runner = cls(plan, project_path)
        runner.run = run

        return runner

    def start(self) -> RunRecord:
        """Start a new run."""
        self.run = create_run(self.plan, self.project_path)
        save_run(self.project_path, self.run)
        return self.run

    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next step to execute."""
        return self.plan.get_next_step()

    def get_ready_steps(self) -> List[PlanStep]:
        """Get all steps ready for parallel execution."""
        return self.plan.get_ready_steps()

    def prepare_step(self, step: PlanStep) -> StepContext:
        """Prepare context for a step execution."""
        if not self.run:
            raise RuntimeError("Run not started. Call start() first.")

        # Build context
        ctx = build_step_context(
            step, self.plan, self.project_path,
            self.graph, self.knowledge
        )

        # Save context to run directory
        run_dir = get_run_dir(self.project_path, self.run.id)
        save_step_context(ctx, run_dir)

        return ctx

    def mark_step_started(self, step: PlanStep) -> None:
        """Mark a step as in progress."""
        if not self.run:
            raise RuntimeError("Run not started")

        step.mark_in_progress()
        self.run.current_step = step.id
        self.run.status = RunStatus.IN_PROGRESS.value
        self.run.add_step_result(StepResult(
            step_id=step.id,
            status=StepStatus.IN_PROGRESS.value,
            started_at=datetime.now(),
        ))
        save_run(self.project_path, self.run)

    def mark_step_completed(
        self,
        step: PlanStep,
        output: str = "",
        artifacts: List[str] = None,
    ) -> None:
        """Mark a step as completed."""
        if not self.run:
            raise RuntimeError("Run not started")

        step.mark_completed()

        # Update step result
        result = self.run.get_step_result(step.id)
        if result:
            result.status = StepStatus.COMPLETED.value
            result.completed_at = datetime.now()
            result.output = output
            result.artifacts = artifacts or []
        else:
            self.run.add_step_result(StepResult(
                step_id=step.id,
                status=StepStatus.COMPLETED.value,
                completed_at=datetime.now(),
                output=output,
                artifacts=artifacts or [],
            ))

        self._update_run_status()
        save_run(self.project_path, self.run)

    def mark_step_failed(
        self,
        step: PlanStep,
        error: str,
        output: str = "",
    ) -> None:
        """Mark a step as failed."""
        if not self.run:
            raise RuntimeError("Run not started")

        step.mark_failed(error)

        result = self.run.get_step_result(step.id)
        if result:
            result.status = StepStatus.FAILED.value
            result.completed_at = datetime.now()
            result.error = error
            result.output = output
        else:
            self.run.add_step_result(StepResult(
                step_id=step.id,
                status=StepStatus.FAILED.value,
                completed_at=datetime.now(),
                error=error,
                output=output,
            ))

        self.run.status = RunStatus.FAILED.value
        save_run(self.project_path, self.run)

    def mark_step_skipped(self, step: PlanStep, reason: str = "") -> None:
        """Mark a step as skipped."""
        if not self.run:
            raise RuntimeError("Run not started")

        step.mark_skipped(reason)

        self.run.add_step_result(StepResult(
            step_id=step.id,
            status=StepStatus.SKIPPED.value,
            completed_at=datetime.now(),
            output=f"Skipped: {reason}" if reason else "Skipped",
        ))

        self._update_run_status()
        save_run(self.project_path, self.run)

    def pause(self) -> None:
        """Pause the run (can be resumed later)."""
        if not self.run:
            return

        self.run.status = RunStatus.PAUSED.value
        save_run(self.project_path, self.run)

    def verify_step(self, step: PlanStep, is_checkpoint: bool = False) -> Optional[Any]:
        """Run verification for a step.

        Args:
            step: The step to verify
            is_checkpoint: Whether this is a checkpoint step

        Returns:
            VerificationResult or None if verification is not configured
        """
        if not self.run:
            raise RuntimeError("Run not started")

        # Lazy load verifier
        if self._verifier is None and self._verification_config is not None:
            from erirpg.verification import Verifier
            self._verifier = Verifier(self._verification_config, self.project_path)

        if self._verifier is None:
            return None

        # Check if we should run verification
        if not self._verifier.should_run_for_step(is_checkpoint):
            return None

        # Run verification
        result = self._verifier.run_verification(step.id, step.step_type)

        # Save result
        from erirpg.verification import save_verification_result
        save_verification_result(self.project_path, self.run.id, result)

        return result

    def get_verification_results(self) -> List[Any]:
        """Get all verification results for the current run.

        Returns:
            List of VerificationResults
        """
        if not self.run:
            return []

        from erirpg.verification import list_verification_results
        return list_verification_results(self.project_path, self.run.id)

    def _update_run_status(self) -> None:
        """Update run status based on step statuses."""
        if not self.run:
            return

        self.plan.update_stats()

        if self.plan.status == "completed":
            self.run.status = RunStatus.COMPLETED.value
            self.run.completed_at = datetime.now()
        elif self.plan.status == "failed":
            self.run.status = RunStatus.FAILED.value
        elif any(s.status == StepStatus.IN_PROGRESS.value for s in self.plan.steps):
            self.run.status = RunStatus.IN_PROGRESS.value

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress summary."""
        self.plan.update_stats()

        return {
            "run_id": self.run.id if self.run else None,
            "status": self.run.status if self.run else "not_started",
            "total_steps": self.plan.total_steps,
            "completed_steps": self.plan.completed_steps,
            "failed_steps": self.plan.failed_steps,
            "current_step": self.run.current_step if self.run else None,
            "progress_pct": (self.plan.completed_steps / self.plan.total_steps * 100)
                           if self.plan.total_steps > 0 else 0,
        }

    def get_report(self) -> str:
        """Generate a human-readable report of the run."""
        if not self.run:
            return "Run not started."

        lines = [
            f"Run Report: {self.run.id}",
            "=" * 50,
            f"Plan: {self.plan.name or self.plan.id}",
            f"Status: {self.run.status}",
            f"Started: {self.run.started_at.strftime('%Y-%m-%d %H:%M')}",
        ]

        if self.run.completed_at:
            lines.append(f"Completed: {self.run.completed_at.strftime('%Y-%m-%d %H:%M')}")
            duration = self.run.completed_at - self.run.started_at
            lines.append(f"Duration: {duration}")

        progress = self.get_progress()
        lines.extend([
            "",
            f"Progress: {progress['completed_steps']}/{progress['total_steps']} steps ({progress['progress_pct']:.0f}%)",
            "",
            "Steps:",
        ])

        for step in sorted(self.plan.steps, key=lambda s: s.order):
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "failed": "✗",
                "skipped": "○",
            }.get(step.status, "?")

            lines.append(f"  {status_icon} {step.order}. {step.action}")

            result = self.run.get_step_result(step.id)
            if result and result.error:
                lines.append(f"      Error: {result.error}")

        return "\n".join(lines)


def list_runs(project_path: str) -> List[RunRecord]:
    """List all runs for a project."""
    runs_dir = get_runs_dir(project_path)
    if not os.path.exists(runs_dir):
        return []

    runs = []
    for run_id in os.listdir(runs_dir):
        run_dir = os.path.join(runs_dir, run_id)
        if os.path.isdir(run_dir):
            run = load_run(project_path, run_id)
            if run:
                runs.append(run)

    # Sort by start time, newest first
    runs.sort(key=lambda r: r.started_at, reverse=True)
    return runs
