"""
EriRPG Agent API.

Spec-driven agent interface. Human writes spec, agent executes.
No CLI involvement in the hot path.

Usage:
    from erirpg.agent import Agent

    # From spec file
    agent = Agent.from_spec("goal.yaml")

    # Or from goal string
    agent = Agent.from_goal("transplant masked_loss from onetrainer to eritrainer")

    # Execute loop
    while not agent.is_complete():
        step = agent.current_step()
        context = agent.get_context()

        # Agent implements the step...

        agent.complete_step(
            files_touched=["path/to/file.py"],
            notes="Implemented the feature"
        )
        # Auto-learn happens automatically

    # Get report
    report = agent.get_report()
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from erirpg.agent.spec import Spec
from erirpg.agent.plan import Plan, Step, StepStatus
from erirpg.agent.run import RunState, save_run, load_run, get_latest_run
from erirpg.agent.learner import auto_learn, get_knowledge, is_stale, update_learning
from erirpg.memory import load_knowledge as load_knowledge_store


class Agent:
    """
    Main agent interface for spec-driven execution.

    This is the API surface for Claude Code (or any agent) to use.
    No CLI commands needed - just Python calls.
    """

    def __init__(
        self,
        spec: Spec,
        plan: Plan,
        project_path: str,
        run: Optional[RunState] = None,
    ):
        self.spec = spec
        self.plan = plan
        self.project_path = project_path
        self._run = run

    @classmethod
    def from_spec(cls, spec_path: str, project_path: Optional[str] = None) -> "Agent":
        """
        Create agent from a spec file.

        Args:
            spec_path: Path to goal.yaml or similar spec file
            project_path: Working directory (default: spec file's directory)
        """
        spec = Spec.from_file(spec_path)
        if not project_path:
            project_path = str(Path(spec_path).parent.absolute())

        plan = cls._generate_plan(spec, project_path)
        run = cls._create_run(spec, plan, project_path)

        return cls(spec=spec, plan=plan, project_path=project_path, run=run)

    @classmethod
    def from_goal(
        cls,
        goal: str,
        project_path: Optional[str] = None,
        source_project: Optional[str] = None,
        target_project: Optional[str] = None,
        constraints: Optional[List[str]] = None,
    ) -> "Agent":
        """
        Create agent from a goal string.

        Args:
            goal: The goal to accomplish
            project_path: Working directory (default: current directory)
            source_project: Source project for transplants
            target_project: Target project for transplants
            constraints: List of constraints
        """
        spec = Spec.from_goal(
            goal=goal,
            source_project=source_project,
            target_project=target_project,
            constraints=constraints or [],
        )
        project_path = project_path or os.getcwd()

        plan = cls._generate_plan(spec, project_path)
        run = cls._create_run(spec, plan, project_path)

        return cls(spec=spec, plan=plan, project_path=project_path, run=run)

    @classmethod
    def resume(cls, project_path: str, run_id: Optional[str] = None) -> Optional["Agent"]:
        """
        Resume a previous run.

        Args:
            project_path: Project directory
            run_id: Specific run ID (default: latest incomplete run)
        """
        if run_id:
            run = load_run(project_path, run_id)
        else:
            run = get_latest_run(project_path)

        if not run:
            return None

        return cls(
            spec=run.spec,
            plan=run.plan,
            project_path=project_path,
            run=run,
        )

    @staticmethod
    def _generate_plan(spec: Spec, project_path: str) -> Plan:
        """
        Generate a plan from a spec.

        This creates steps based on the goal type.
        """
        # Parse goal to determine type
        goal_lower = spec.goal.lower()

        steps = []

        if "transplant" in goal_lower or "from" in goal_lower:
            # Transplant workflow
            steps = [
                Step(
                    id="analyze",
                    goal="Analyze source and identify components",
                    description="Find the relevant modules in source project",
                    order=1,
                    context_files=spec.context_hints,
                ),
                Step(
                    id="plan",
                    goal="Plan the transplant mappings",
                    description="Map source interfaces to target equivalents",
                    order=2,
                ),
                Step(
                    id="implement",
                    goal="Implement the transplanted feature",
                    description="Write the code in target project",
                    order=3,
                    verification_commands=spec.verification,
                ),
                Step(
                    id="verify",
                    goal="Verify the implementation",
                    description="Run tests and validate",
                    order=4,
                    verification_commands=spec.verification,
                ),
            ]
        elif "fix" in goal_lower or "bug" in goal_lower:
            # Bug fix workflow
            steps = [
                Step(
                    id="investigate",
                    goal="Investigate the issue",
                    description="Find root cause",
                    order=1,
                ),
                Step(
                    id="fix",
                    goal="Implement the fix",
                    description="Write the fix",
                    order=2,
                ),
                Step(
                    id="verify",
                    goal="Verify the fix",
                    description="Run tests",
                    order=3,
                    verification_commands=spec.verification,
                ),
            ]
        elif "implement" in goal_lower or "add" in goal_lower or "create" in goal_lower:
            # New feature workflow
            steps = [
                Step(
                    id="design",
                    goal="Design the implementation",
                    description="Plan the approach",
                    order=1,
                ),
                Step(
                    id="implement",
                    goal="Implement the feature",
                    description="Write the code",
                    order=2,
                ),
                Step(
                    id="test",
                    goal="Test the implementation",
                    description="Write and run tests",
                    order=3,
                    verification_commands=spec.verification,
                ),
            ]
        else:
            # Generic workflow
            steps = [
                Step(
                    id="execute",
                    goal=spec.goal,
                    description="Execute the goal",
                    order=1,
                    verification_commands=spec.verification,
                ),
            ]

        return Plan.create(
            goal=spec.goal,
            steps=steps,
            source_project=spec.source_project,
            target_project=spec.target_project,
            constraints=spec.constraints,
            final_verification=spec.verification,
        )

    @staticmethod
    def _create_run(spec: Spec, plan: Plan, project_path: str) -> RunState:
        """Create a new run state."""
        run_id = hashlib.sha256(
            f"{spec.goal}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        run = RunState(
            id=run_id,
            spec=spec,
            plan=plan,
            work_dir=project_path,
        )

        # Save immediately
        save_run(project_path, run)
        return run

    # === Execution API ===

    def current_step(self) -> Optional[Step]:
        """Get the current step to execute."""
        return self.plan.current_step()

    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return self.plan.is_complete()

    def progress(self) -> tuple:
        """Return (completed, total) step counts."""
        return self.plan.progress()

    def start_step(self) -> Optional[Step]:
        """Start the next pending step."""
        step = self.plan.next_step()
        if step:
            if self._run:
                self._run.start_step(step)
                self._save()
        return step

    def complete_step(
        self,
        files_touched: Optional[List[str]] = None,
        notes: str = "",
        auto_learn_files: bool = True,
    ) -> None:
        """
        Complete the current step.

        Args:
            files_touched: List of files that were modified
            notes: Any notes about what was done
            auto_learn_files: Whether to auto-learn the touched files
        """
        step = self.current_step()
        if not step:
            return

        files_touched = files_touched or []

        if self._run:
            self._run.complete_step(step, files_touched, notes)

        # Auto-learn
        if auto_learn_files and files_touched:
            learned = auto_learn(
                self.project_path,
                files_touched,
                step.goal,
                notes,
            )
            if self._run:
                self._run.add_learned_files(learned)

        self._save()

    def fail_step(self, error: str) -> None:
        """Mark current step as failed."""
        step = self.current_step()
        if step and self._run:
            self._run.fail_step(step, error)
            self._save()

    def skip_step(self, reason: str = "") -> None:
        """Skip the current step."""
        step = self.current_step()
        if step and self._run:
            self._run.skip_step(step, reason)
            self._save()

    # === Context API ===

    def get_context(self) -> str:
        """
        Get context for the current step.

        Returns markdown-formatted context including:
        - Goal and constraints
        - Current step details
        - Relevant knowledge
        - Files to examine
        """
        step = self.current_step()
        if not step:
            return "No current step."

        lines = [
            f"# {self.spec.goal}",
            "",
            f"## Current Step: {step.goal}",
            "",
            step.description,
            "",
        ]

        if self.spec.constraints:
            lines.append("## Constraints")
            for c in self.spec.constraints:
                lines.append(f"- {c}")
            lines.append("")

        # Add relevant knowledge
        knowledge_lines = self._get_relevant_knowledge(step)
        if knowledge_lines:
            lines.append("## Relevant Knowledge")
            lines.extend(knowledge_lines)
            lines.append("")

        if step.context_files:
            lines.append("## Files to Examine")
            for f in step.context_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if step.verification_commands:
            lines.append("## Verification")
            for cmd in step.verification_commands:
                lines.append(f"- `{cmd}`")
            lines.append("")

        # Progress
        completed, total = self.progress()
        lines.append(f"## Progress: {completed}/{total} steps complete")

        return "\n".join(lines)

    def _get_relevant_knowledge(self, step: Step) -> List[str]:
        """Get relevant stored knowledge for a step."""
        lines = []

        # Check knowledge_needed from step
        for path in step.knowledge_needed:
            learning = get_knowledge(self.project_path, path)
            if learning:
                stale_marker = " (STALE)" if learning.is_stale(self.project_path) else ""
                lines.append(f"### {path}{stale_marker}")
                lines.append(f"**Summary**: {learning.summary}")
                lines.append(f"**Purpose**: {learning.purpose}")
                if learning.gotchas:
                    lines.append("**Gotchas**:")
                    for g in learning.gotchas:
                        lines.append(f"  - {g}")
                lines.append("")

        return lines

    # === Knowledge API ===

    def recall(self, file_path: str) -> Optional[str]:
        """
        Recall knowledge about a file.

        Returns formatted knowledge or None if not found/stale.
        """
        learning = get_knowledge(self.project_path, file_path)
        if not learning:
            return None

        return learning.format_for_context(self.project_path)

    def learn(
        self,
        file_path: str,
        summary: str,
        purpose: str,
        key_functions: Optional[Dict[str, str]] = None,
        gotchas: Optional[List[str]] = None,
    ) -> None:
        """
        Store knowledge about a file.

        Use this when you've deeply understood a file.
        """
        update_learning(
            self.project_path,
            file_path,
            summary=summary,
            purpose=purpose,
            key_functions=key_functions,
            gotchas=gotchas,
        )

    def is_knowledge_stale(self, file_path: str) -> bool:
        """Check if knowledge for a file is stale."""
        return is_stale(self.project_path, file_path)

    # === Report API ===

    def get_report(self) -> Dict[str, Any]:
        """Get a report of the run."""
        if self._run:
            return self._run.get_report()
        return {
            "goal": self.spec.goal,
            "progress": self.progress(),
            "is_complete": self.is_complete(),
        }

    # === Persistence ===

    def _save(self) -> None:
        """Save run state."""
        if self._run:
            save_run(self.project_path, self._run)


# Convenience exports
__all__ = [
    "Agent",
    "Spec",
    "Plan",
    "Step",
    "StepStatus",
    "RunState",
    "auto_learn",
    "get_knowledge",
    "is_stale",
    "update_learning",
]
