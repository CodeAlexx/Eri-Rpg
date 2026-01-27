"""
EriRPG Agent API.

Spec-driven agent interface. Human writes spec, agent executes.
No CLI involvement in the hot path.

HARD ENFORCEMENT: All code changes MUST go through this Agent API.
- Use agent.preflight() before any changes (MANDATORY)
- Use agent.edit_file() or agent.write_file() for all file modifications
- Direct file edits without preflight are BLOCKED by Python hooks
- Any attempt to use open() in write mode without EriRPG raises RuntimeError

Usage:
    from erirpg.agent import Agent

    # From spec file
    agent = Agent.from_spec("goal.yaml")

    # Or from goal string
    agent = Agent.from_goal("transplant masked_loss from onetrainer to eritrainer")

    # Execute loop with preflight
    while not agent.is_complete():
        step = agent.current_step()
        context = agent.get_context()

        # MANDATORY: Run preflight before any changes
        report = agent.preflight(files=["path/to/file.py"], operation="modify")
        if not report.ready:
            # Handle blockers
            print(report.format())
            break

        # Agent implements the step using agent.edit_file()...

        agent.complete_step(
            files_touched=["path/to/file.py"],
            notes="Implemented the feature"
        )
        # Auto-learn happens automatically

    # Get report
    report = agent.get_report()
"""

import os
import sys
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from erirpg.spec import Spec, SpecStep
from erirpg.agent.plan import Plan, Step, StepStatus
from erirpg.agent.run import RunState, save_run, load_run, get_latest_run, Decision, RunSummary
from erirpg.agent.learner import auto_learn, get_knowledge, is_stale, update_learning
from erirpg.memory import load_knowledge as load_knowledge_store, git_head, in_git_repo
from erirpg.config import load_config, ProjectConfig

if TYPE_CHECKING:
    from erirpg.preflight import PreflightReport
    from erirpg.memory import StoredLearning, RollbackResult
    from erirpg.verification import VerificationResult


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE - Hard enforcement of EriRPG workflow
# ═══════════════════════════════════════════════════════════════════════════════

_ACTIVE_AGENT: Optional["Agent"] = None
_PREFLIGHT_DONE: bool = False


def get_active_agent() -> "Agent":
    """
    Get the current active agent or raise error.

    Use this to ensure there's an active EriRPG context before
    any code changes.

    Raises:
        RuntimeError: If no active agent exists
    """
    if _ACTIVE_AGENT is None:
        raise RuntimeError(
            "╔══════════════════════════════════════════════════════╗\n"
            "║  NO ACTIVE ERI-RPG AGENT                             ║\n"
            "╠══════════════════════════════════════════════════════╣\n"
            "║  Start an EriRPG run before making code changes:     ║\n"
            "║                                                      ║\n"
            "║    from erirpg.agent import Agent                    ║\n"
            "║    agent = Agent.from_goal('task', project='name')   ║\n"
            "║    agent.preflight(files, operation)                 ║\n"
            "╚══════════════════════════════════════════════════════╝"
        )
    return _ACTIVE_AGENT


def require_preflight() -> None:
    """
    Check that preflight was done or raise error.

    Call this before any file operations to ensure the EriRPG
    workflow is being followed.

    Raises:
        RuntimeError: If preflight wasn't run
    """
    if not _PREFLIGHT_DONE:
        raise RuntimeError(
            "╔══════════════════════════════════════════════════════╗\n"
            "║  PREFLIGHT REQUIRED                                  ║\n"
            "╠══════════════════════════════════════════════════════╣\n"
            "║  Run preflight before any file operations:           ║\n"
            "║                                                      ║\n"
            "║    agent.preflight(files=['path/to/file.py'],        ║\n"
            "║                    operation='modify')               ║\n"
            "╚══════════════════════════════════════════════════════╝"
        )


def _set_active_agent(agent: Optional["Agent"]) -> None:
    """Set the active agent (internal use only)."""
    global _ACTIVE_AGENT
    _ACTIVE_AGENT = agent


def _set_preflight_done(done: bool) -> None:
    """Set preflight state (internal use only)."""
    global _PREFLIGHT_DONE
    _PREFLIGHT_DONE = done


# ═══════════════════════════════════════════════════════════════════════════════


class Agent:
    """
    Main agent interface for spec-driven execution.

    This is the API surface for Claude Code (or any agent) to use.
    No CLI commands needed - just Python calls.

    ENFORCEMENT: All code changes MUST go through this Agent.
    - preflight() is MANDATORY before any code changes
    - Use edit_file() or write_file() for all modifications
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

        # Load project configuration
        self._config = load_config(project_path)

        # Preflight enforcement
        self._preflight_done = False
        self._preflight_report: Optional["PreflightReport"] = None

        # File snapshots for rollback
        self._snapshots: Dict[str, str] = {}  # path -> original content
        self._files_modified: List[str] = []

        # Register as active agent (hard enforcement)

        # Install write hooks (opt-in when Agent is created)
        from erirpg.write_guard import install_hooks
        install_hooks()
        _set_active_agent(self)

    @property
    def config(self) -> ProjectConfig:
        """Get the project configuration."""
        return self._config

    @property
    def multi_agent_enabled(self) -> bool:
        """Check if multi-agent mode is enabled."""
        return self._config.multi_agent.enabled

    @property
    def max_concurrency(self) -> int:
        """Get max concurrent sub-agents."""
        return self._config.multi_agent.max_concurrency

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

        If spec has explicit steps, use those.
        Otherwise, create steps based on the goal type.
        """
        # Use custom steps from spec if provided
        if spec.steps:
            steps = []
            for i, spec_step in enumerate(spec.steps):
                steps.append(Step(
                    id=spec_step.id,
                    goal=spec_step.goal,
                    description=spec_step.description,
                    order=i + 1,
                    context_files=spec_step.context_files,
                    verification_commands=spec_step.verification or spec.verification,
                ))
            return Plan.create(
                goal=spec.goal,
                steps=steps,
                source_project=spec.source_project,
                target_project=spec.target_project,
                constraints=spec.constraints,
                final_verification=spec.verification,
            )

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

    # === New Spec-Driven Execution ===

    @classmethod
    def from_new_spec(cls, spec: "NewSpec", project_path: str) -> "Agent":
        """
        Create agent from a NEW spec (erirpg.spec.Spec).

        This is the spec-driven execution interface. Claude Code
        follows the spec. Step by step. No freestyling.

        Args:
            spec: A Spec object from erirpg.spec
            project_path: Working directory

        Usage:
            from erirpg.spec import Spec
            spec = Spec.generate(goal, project, graph, knowledge)
            agent = Agent.from_new_spec(spec, project_path)
        """
        from erirpg.spec import Spec as NewSpec

        # Convert new Spec to old Spec format for compatibility
        old_spec = Spec.from_goal(spec.goal)

        # Create plan from new spec steps
        steps = []
        for i, new_step in enumerate(spec.steps):
            steps.append(Step(
                id=new_step.id,
                goal=new_step.description,
                description=f"{new_step.action}: {new_step.description}",
                order=i + 1,
                context_files=new_step.targets,
                verification_commands=[new_step.verification] if new_step.verification else [],
            ))

        plan = Plan.create(
            goal=spec.goal,
            steps=steps,
            final_verification=spec.verification,
        )

        run = cls._create_run(old_spec, plan, project_path)

        agent = cls(spec=old_spec, plan=plan, project_path=project_path, run=run)

        # Store reference to new spec
        agent._new_spec = spec

        return agent

    def next_step(self) -> Optional[Step]:
        """
        Get the next incomplete step.

        Returns the next step that should be executed, respecting
        dependencies. Returns None if all steps are complete or
        blocked.

        This is the primary interface for spec-driven execution:
        1. Get next step
        2. Run preflight for step targets
        3. Execute the step action
        4. Verify the step
        5. Complete the step
        """
        # Check for in-progress step first
        current = self.current_step()
        if current and current.status == StepStatus.IN_PROGRESS:
            return current

        # Get next pending step
        return self.start_step()

    def verify_step(self) -> bool:
        """
        Check if the current step succeeded.

        Runs verification without completing the step.
        Agent REFUSES to proceed if verification fails.

        Returns:
            True if verification passed, False otherwise
        """
        step = self.current_step()
        if not step:
            return True  # No step, nothing to verify

        # Run verification
        result = self._run_verification(step)

        if result is None:
            # No verification configured, assume success
            return True

        if not result.passed:
            # Show failure info
            print(f"\n{'═' * 50}")
            print(f" ⚠️  VERIFICATION FAILED for step: {step.id}")
            print(f"{'═' * 50}")
            for cmd_result in result.failed_commands:
                print(f"  ✗ {cmd_result.name}: exit code {cmd_result.exit_code}")
                if cmd_result.stderr:
                    for line in cmd_result.stderr.strip().split("\n")[:5]:
                        print(f"    {line}")

            # Show rollback command
            if self._files_modified:
                print(f"\nRollback with:")
                for file_path in self._files_modified:
                    print(f"  eri-rpg rollback {self._get_project_name()} {file_path} --code")
            print("")

            return False

        return True

    def get_spec_status(self) -> str:
        """
        Get formatted status of the current spec execution.

        Returns a human-readable status string showing progress,
        current step, and any blockers.
        """
        if hasattr(self, '_new_spec') and self._new_spec:
            return self._new_spec.format_status()

        # Fallback to basic status
        completed, total = self.progress()
        current = self.current_step()

        lines = [
            f"{'═' * 50}",
            f" RUN: {self.spec.goal[:40]}{'...' if len(self.spec.goal) > 40 else ''}",
            f"{'═' * 50}",
            f"Progress: {completed}/{total} steps",
            "",
        ]

        for step in self.plan.steps:
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "failed": "✗",
                "skipped": "◌",
            }.get(step.status.value, "?")
            lines.append(f"  {status_icon} [{step.id}] {step.goal}")

        if current:
            lines.append("")
            lines.append(f"Next: {current.goal}")

        return "\n".join(lines)

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

    def needs_discussion(
        self,
        goal: str,
        force: bool = False,
        skip: bool = False,
    ) -> tuple:
        """Check if a goal needs discussion before spec generation.
        
        This is a convenience method that wraps discuss.needs_discussion()
        for use in the agent workflow.
        
        Args:
            goal: The user's goal
            force: Force discussion even if not needed
            skip: Skip discussion even if needed
            
        Returns:
            (needs_discussion, reason) tuple
        """
        from erirpg.discuss import needs_discussion as check_needs_discussion
        return check_needs_discussion(goal, self.project_path, force, skip)

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
        auto_commit: bool = True,
        skip_verification: bool = False,
    ) -> bool:
        """
        Complete the current step.

        MANDATORY VERIFICATION: If verification exists and fails, the step
        is NOT completed. Use skip_verification=True only for legitimate
        reasons (e.g., test-only changes that don't need re-verification).

        If in a git repo and auto_commit is True, creates a commit
        with the step notes and links it to the run state.

        Args:
            files_touched: List of files that were modified
            notes: Any notes about what was done
            auto_learn_files: Whether to auto-learn the touched files
            auto_commit: Whether to git commit (default: True)
            skip_verification: Skip verification check (use with caution)

        Returns:
            True if step was completed, False if verification failed
        """
        step = self.current_step()
        if not step:
            return False

        # Use tracked files if none provided
        files_touched = files_touched or self._files_modified.copy()

        # MANDATORY VERIFICATION - run BEFORE completing step
        if not skip_verification:
            verification_result = self._run_verification(step)
            if verification_result and not verification_result.passed:
                # Collect stdout/stderr for run report
                error_details = []
                for cmd_result in verification_result.failed_commands:
                    error_details.append({
                        "command": cmd_result.name,
                        "exit_code": cmd_result.exit_code,
                        "stdout": cmd_result.stdout[:2000] if cmd_result.stdout else "",
                        "stderr": cmd_result.stderr[:2000] if cmd_result.stderr else "",
                    })

                # Mark step as FAILED with verification output
                error_msg = f"Verification failed: {len(verification_result.failed_commands)} command(s)"
                if self._run:
                    self._run.fail_step(step, error_msg)
                    # Store detailed verification output in log
                    self._run.add_log("verification_failed", {
                        "step_id": step.id,
                        "commands": error_details,
                    })
                    self._save()

                # Show failure info and rollback command
                print(f"\n{'═' * 50}")
                print(f" ⚠️  VERIFICATION FAILED - STEP MARKED FAILED")
                print(f"{'═' * 50}")
                for cmd_result in verification_result.failed_commands:
                    print(f"  ✗ {cmd_result.name}: exit code {cmd_result.exit_code}")
                    if cmd_result.stderr:
                        for line in cmd_result.stderr.strip().split("\n")[:5]:
                            print(f"    {line}")
                print(f"\nRollback with:")
                for file_path in files_touched:
                    print(f"  eri-rpg rollback {self._get_project_name()} {file_path} --code")
                print(f"\nFix the issue and call complete_step() again.")
                print("")
                # Step is FAILED, not completed
                return False

        # Mark step as complete
        if self._run:
            self._run.complete_step(step, files_touched, notes)

        # Git commit if enabled and in repo
        commit_hash = None
        if auto_commit and in_git_repo() and files_touched:
            commit_hash = self._git_commit(files_touched, notes, step)

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

            # Update learning versions with commit_after if we committed
            if commit_hash and self._preflight_report:
                self._update_learning_commits(commit_hash)

        # Reset preflight state for next operation
        self.reset_preflight()

        self._save()
        return True

    def _git_commit(
        self,
        files: List[str],
        notes: str,
        step: Step,
    ) -> Optional[str]:
        """
        Create a git commit for the step.

        Args:
            files: Files to stage and commit
            notes: Commit message notes
            step: Current step for metadata

        Returns:
            Commit hash if successful, None otherwise
        """
        run_id = self._run.id if self._run else "unknown"
        commit_msg = f"[eri-rpg] {notes}\n\nRun: {run_id}\nStep: {step.id}"

        try:
            # Stage files
            full_paths = [str(Path(self.project_path) / f) for f in files]
            subprocess.run(
                ['git', 'add'] + full_paths,
                check=True,
                capture_output=True,
                cwd=self.project_path,
            )

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                check=True,
                capture_output=True,
                cwd=self.project_path,
            )

            # Get commit hash
            return git_head()

        except subprocess.CalledProcessError as e:
            # Log but don't fail - commit is optional
            print(f"Warning: git commit failed: {e}")
            return None

    def _get_project_name(self) -> str:
        """Get the project name from registry."""
        from erirpg.registry import Registry
        registry = Registry.get_instance()
        for proj in registry.list():
            if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                return proj.name
        return "unknown"

    def _run_verification(self, step: Step) -> Optional["VerificationResult"]:
        """
        Run verification if project has tests configured.

        Args:
            step: Current step for context

        Returns:
            VerificationResult or None if no verification configured
        """
        from erirpg.verification import (
            load_verification_config,
            Verifier,
            VerificationResult,
            get_default_python_config,
            get_default_node_config,
        )

        # Try to load verification config
        config = load_verification_config(self.project_path)

        # If no config, try to auto-detect project type
        if not config:
            # Check for Python project
            if Path(self.project_path, "pyproject.toml").exists() or \
               Path(self.project_path, "setup.py").exists() or \
               Path(self.project_path, "pytest.ini").exists():
                # Only use default if pytest is available
                pytest_path = Path(self.project_path, "tests")
                if pytest_path.exists() or Path(self.project_path, "test").exists():
                    config = get_default_python_config()
            # Check for Node project
            elif Path(self.project_path, "package.json").exists():
                config = get_default_node_config()

        if not config or not config.commands:
            return None

        # Check if we should run verification for this step
        verifier = Verifier(config, self.project_path)
        if not verifier.should_run_for_step(is_checkpoint=False):
            return None

        # Run verification
        result = verifier.run_verification(
            step_id=step.id,
            step_type=step.id,  # Use step ID as type for filtering
        )

        # Save result
        if self._run:
            from erirpg.verification import save_verification_result
            save_verification_result(self.project_path, self._run.id, result)

        return result

    def _update_learning_commits(self, commit_hash: str) -> None:
        """Update learning versions with the commit_after hash."""
        if not self._preflight_report:
            return

        try:
            from erirpg.memory import load_knowledge, save_knowledge
            from erirpg.registry import Registry

            # Find project name
            project_name = "unknown"
            registry = Registry.get_instance()
            for proj in registry.list():
                if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                    project_name = proj.name
                    break

            store = load_knowledge(self.project_path, project_name)

            # Update commit_after on latest version of each touched learning
            for file_path, learning in self._preflight_report.existing_learnings.items():
                stored = store.get_learning(file_path)
                if stored and stored.versions:
                    stored.versions[-1].commit_after = commit_hash
                    store.add_learning(stored)

            save_knowledge(self.project_path, store)
        except Exception as e:
            print(f"Warning: Could not update learning commits: {e}")

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

    # === Preflight API (MANDATORY) ===

    def preflight(
        self,
        files: List[str],
        operation: str,
        strict: bool = True,
    ) -> "PreflightReport":
        """
        MANDATORY before any code operation.

        Run preflight checks to ensure we understand what we're about to touch.
        This checks for existing learnings, staleness, and impact zone.

        Args:
            files: Files that will be touched
            operation: "refactor" | "transplant" | "modify" | "new"
            strict: If True, missing learnings block refactor/modify operations

        Returns:
            PreflightReport - review before proceeding
        """
        from erirpg.preflight import preflight as run_preflight

        # Try to load graph
        graph = None
        try:
            from erirpg.indexer import get_or_load_graph
            from erirpg.registry import Registry
            registry = Registry.get_instance()
            for proj in registry.list():
                if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                    graph = get_or_load_graph(proj)
                    break
        except Exception as e:
            import sys; print(f"[EriRPG] {e}", file=sys.stderr)

        report = run_preflight(
            project_path=self.project_path,
            files=files,
            operation=operation,
            graph=graph,
            strict=strict,
        )

        self._preflight_report = report

        if report.ready:
            self._preflight_done = True
            _set_preflight_done(True)

            # Enable writes via Python hooks (HARD ENFORCEMENT)
            from erirpg.write_guard import enable_writes
            enable_writes(files, self.project_path)

            # Save preflight state for Claude Code hooks to read
            self._save_preflight_state(files, operation)

            # Snapshot files before changes
            for f in files:
                self._snapshot_file(f)

        return report

    def _save_preflight_state(self, files: List[str], operation: str) -> None:
        """Save preflight state to file for Claude Code hooks."""
        import json
        from datetime import datetime

        state = {
            "ready": True,
            "operation": operation,
            "target_files": files,
            "timestamp": datetime.now().isoformat(),
            "run_id": self._run.id if self._run else None,
        }

        state_dir = Path(self.project_path) / ".eri-rpg"
        state_dir.mkdir(parents=True, exist_ok=True)

        state_file = state_dir / "preflight_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _clear_preflight_state(self) -> None:
        """Clear preflight state file."""
        state_file = Path(self.project_path) / ".eri-rpg" / "preflight_state.json"
        if state_file.exists():
            state_file.unlink()

    def _snapshot_file(self, file_path: str) -> None:
        """Snapshot a file's content for potential rollback."""
        if file_path in self._snapshots:
            return  # Already snapshotted

        full_path = Path(self.project_path) / file_path
        if full_path.exists():
            try:
                self._snapshots[file_path] = full_path.read_text()
            except Exception as e:
                import sys; print(f"[EriRPG] {e}", file=sys.stderr)  # Can't snapshot, proceed anyway

    def reset_preflight(self) -> None:
        """Reset preflight state for a new operation."""
        self._preflight_done = False
        self._preflight_report = None
        self._snapshots = {}
        self._files_modified = []
        _set_preflight_done(False)

        # Disable writes via hooks (HARD ENFORCEMENT)
        from erirpg.write_guard import disable_writes
        disable_writes()

        # Clear preflight state file for Claude Code hooks
        self._clear_preflight_state()

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

    def add_decision(
        self,
        decision: str,
        rationale: str = "",
        step_id: str = "",
    ) -> "Decision":
        """
        Record a decision made during the run.

        Args:
            decision: What was decided
            rationale: Why this decision was made
            step_id: Which step this relates to (defaults to current)

        Returns:
            The created Decision

        Example:
            agent.add_decision(
                "Use dataclasses for new types",
                rationale="Consistent with existing code patterns"
            )
        """
        from erirpg.agent.run import Decision
        if not self._run:
            raise RuntimeError("Cannot add decision without an active run.")
        return self._run.add_decision(decision, rationale, step_id)

    def generate_summary(self, one_liner: str = "") -> "RunSummary":
        """
        Generate a summary of the completed run.

        Args:
            one_liner: Brief summary of what was accomplished.
                      If not provided, generates from spec goal.

        Returns:
            RunSummary object

        Example:
            summary = agent.generate_summary("Added run summary support to EriRPG")
            print(summary.to_dict())
        """
        from erirpg.agent.run import RunSummary
        if not self._run:
            raise RuntimeError("Cannot generate summary without an active run.")
        return self._run.generate_summary(one_liner)

    # === File Editing API ===

    def edit_file(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        description: str = "",
    ) -> bool:
        """
        Edit a file within the EriRPG run.

        This is the ONLY sanctioned way to modify files during a run.
        All changes are tracked in the run state.

        ENFORCEMENT: Requires preflight() to have been run first.

        Args:
            file_path: Path to the file (relative to project_path)
            old_content: Content to replace
            new_content: Replacement content
            description: Description of the change

        Returns:
            True if edit succeeded, False otherwise

        Raises:
            RuntimeError: If no active run exists or preflight not done
        """
        if not self._run:
            raise RuntimeError(
                "Cannot edit files without an active EriRPG run. "
                "Use Agent.from_goal() or Agent.resume() first."
            )

        # ENFORCEMENT: Require preflight
        if not self._preflight_done:
            raise RuntimeError(
                "Cannot edit files without preflight.\n"
                "Run: agent.preflight([files], operation) first.\n"
                "No preflight = no code changes."
            )

        # ENFORCEMENT: Check file is in preflight targets
        if self._preflight_report and file_path not in self._preflight_report.target_files:
            raise RuntimeError(
                f"File {file_path} not in preflight target list.\n"
                "Re-run preflight with all files you intend to modify."
            )

        step = self.current_step()
        if not step:
            raise RuntimeError(
                "Cannot edit files without an active step. "
                "Call start_step() first."
            )

        # Resolve full path
        full_path = Path(self.project_path) / file_path
        if not full_path.exists():
            # For new files, old_content should be empty
            if old_content:
                raise FileNotFoundError(f"File not found: {full_path}")
            # Create new file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(new_content)
        else:
            # Edit existing file
            current_content = full_path.read_text()
            if old_content not in current_content:
                raise ValueError(
                    f"old_content not found in {file_path}. "
                    "File may have changed or old_content is incorrect."
                )
            updated_content = current_content.replace(old_content, new_content, 1)
            full_path.write_text(updated_content)

        # Track the edit in run state
        self._run.track_file_edit(
            file_path=str(file_path),
            description=description,
            step_id=step.id,
        )

        # Track modified file for complete_step
        if file_path not in self._files_modified:
            self._files_modified.append(file_path)

        self._save()

        return True

    def write_file(
        self,
        file_path: str,
        content: str,
        description: str = "",
    ) -> bool:
        """
        Write a new file or completely overwrite existing file.

        This is the ONLY sanctioned way to create files during a run.

        ENFORCEMENT: Requires preflight() to have been run first.

        Args:
            file_path: Path to the file (relative to project_path)
            content: File content
            description: Description of the change

        Returns:
            True if write succeeded

        Raises:
            RuntimeError: If no active run exists or preflight not done
        """
        if not self._run:
            raise RuntimeError(
                "Cannot write files without an active EriRPG run. "
                "Use Agent.from_goal() or Agent.resume() first."
            )

        # ENFORCEMENT: Require preflight
        if not self._preflight_done:
            raise RuntimeError(
                "Cannot write files without preflight.\n"
                "Run: agent.preflight([files], operation) first.\n"
                "No preflight = no code changes."
            )

        # ENFORCEMENT: Check file is in preflight targets
        if self._preflight_report and file_path not in self._preflight_report.target_files:
            raise RuntimeError(
                f"File {file_path} not in preflight target list.\n"
                "Re-run preflight with all files you intend to modify."
            )

        step = self.current_step()
        if not step:
            raise RuntimeError(
                "Cannot write files without an active step. "
                "Call start_step() first."
            )

        # Snapshot if not already done
        if file_path not in self._snapshots:
            self._snapshot_file(file_path)

        # Resolve full path
        full_path = Path(self.project_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

        # Track the edit in run state
        self._run.track_file_edit(
            file_path=str(file_path),
            description=description,
            step_id=step.id,
        )

        # Track modified file for complete_step
        if file_path not in self._files_modified:
            self._files_modified.append(file_path)

        self._save()

        return True

    # === Rollback API ===

    def rollback(
        self,
        file_path: str,
        to_version: Optional[int] = None,
        dry_run: bool = False,
        use_git: bool = False,
    ) -> "RollbackResult":
        """
        Rollback a file to a previous version.

        Can rollback using either:
        1. Stored snapshots (default) - from LearningVersion.files_content
        2. Git (use_git=True) - checkout from commit_before

        Args:
            file_path: Path to the file (relative to project_path)
            to_version: Version number to rollback to (default: previous)
            dry_run: If True, only report what would be restored
            use_git: If True, use git checkout instead of snapshots

        Returns:
            RollbackResult with details of what was restored

        Raises:
            RuntimeError: If no learning exists for the file
            ValueError: If version not found or no content to restore
        """
        from erirpg.memory import (
            load_knowledge, save_knowledge, RollbackResult
        )
        from erirpg.registry import Registry
        from erirpg.write_guard import enable_writes, disable_writes

        # Find project name
        project_name = "unknown"
        registry = Registry.get_instance()
        for proj in registry.list():
            if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                project_name = proj.name
                break

        # Load knowledge store
        store = load_knowledge(self.project_path, project_name)
        learning = store.get_learning(file_path)

        if not learning:
            result = RollbackResult(
                from_version=0,
                to_version=to_version or 0,
                module_path=file_path,
                success=False,
                error=f"No learning exists for {file_path}",
            )
            return result

        # Determine target version
        target = to_version if to_version is not None else learning.current_version - 1

        if target < 0 or target >= len(learning.versions):
            result = RollbackResult(
                from_version=learning.current_version,
                to_version=target,
                module_path=file_path,
                success=False,
                error=f"Version {target} not found (have {len(learning.versions)} versions)",
            )
            return result

        version = learning.versions[target]

        # Git-based rollback
        if use_git and version.commit_before:
            return self._rollback_git(file_path, version.commit_before, learning, dry_run)

        # Snapshot-based rollback
        if not version.files_content:
            result = RollbackResult(
                from_version=learning.current_version,
                to_version=target,
                module_path=file_path,
                success=False,
                error=(
                    f"Version {target} has no stored file content. "
                    "Try use_git=True if commit_before is available."
                ),
            )
            if version.commit_before:
                result.error += f"\nGit commit available: {version.commit_before}"
            return result

        # Enable writes temporarily for rollback
        files_to_restore = list(version.files_content.keys())
        if not dry_run:
            enable_writes(files_to_restore, self.project_path)

        try:
            result = learning.rollback_files(
                project_path=self.project_path,
                to_version=target,
                dry_run=dry_run,
            )

            # Save updated learning (with rolled-back version)
            if not dry_run and result.success:
                store.add_learning(learning)
                save_knowledge(self.project_path, store)

                # Log the rollback
                if self._run:
                    self._run.add_log("rollback", {
                        "file_path": file_path,
                        "from_version": result.from_version,
                        "to_version": result.to_version,
                        "files_restored": [f["path"] for f in result.files_restored],
                    })
                    self._save()

            return result

        finally:
            # Disable writes after rollback
            if not dry_run:
                disable_writes()

    def _rollback_git(
        self,
        file_path: str,
        commit: str,
        learning: "StoredLearning",
        dry_run: bool = False,
    ) -> "RollbackResult":
        """
        Rollback using git checkout.

        Args:
            file_path: File to rollback
            commit: Git commit to restore from
            learning: Learning object for the file
            dry_run: If True, only report what would happen

        Returns:
            RollbackResult
        """
        from erirpg.memory import RollbackResult

        result = RollbackResult(
            from_version=learning.current_version,
            to_version=learning.current_version - 1,
            module_path=file_path,
            git_commit=commit,
        )

        if dry_run:
            result.files_restored.append({
                "path": file_path,
                "action": "would_restore",
                "bytes": 0,
            })
            result.success = True
            return result

        try:
            # Git checkout the specific file at the commit
            full_path = Path(self.project_path) / file_path
            subprocess.run(
                ['git', 'checkout', commit, '--', str(full_path)],
                check=True,
                capture_output=True,
                cwd=self.project_path,
            )

            # Get restored file size
            size = full_path.stat().st_size if full_path.exists() else 0

            result.files_restored.append({
                "path": file_path,
                "action": "restored",
                "bytes": size,
            })
            result.success = True
            result.metadata_restored = True

            # Update learning version
            learning.current_version -= 1

            # Log the rollback
            if self._run:
                self._run.add_log("rollback_git", {
                    "file_path": file_path,
                    "commit": commit,
                })
                self._save()

        except subprocess.CalledProcessError as e:
            result.success = False
            result.error = f"Git checkout failed: {e.stderr.decode() if e.stderr else str(e)}"
            result.files_failed.append(file_path)

        return result

    def list_versions(self, file_path: str) -> List[Dict[str, Any]]:
        """
        List available versions for a file.

        Args:
            file_path: Path to the file

        Returns:
            List of version info dicts
        """
        from erirpg.memory import load_knowledge
        from erirpg.registry import Registry

        # Find project name
        project_name = "unknown"
        registry = Registry.get_instance()
        for proj in registry.list():
            if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                project_name = proj.name
                break

        store = load_knowledge(self.project_path, project_name)
        learning = store.get_learning(file_path)

        if not learning or not learning.versions:
            return []

        versions = []
        for v in learning.versions:
            versions.append({
                "version": v.version,
                "timestamp": v.timestamp.isoformat(),
                "operation": v.operation,
                "change_description": v.change_description,
                "has_content": bool(v.files_content),
                "commit_before": v.commit_before,
                "commit_after": v.commit_after,
                "is_current": v.version == learning.current_version,
            })

        return versions

    def can_rollback(self, file_path: str, to_version: Optional[int] = None) -> Dict[str, Any]:
        """
        Check if rollback is possible for a file.

        Args:
            file_path: Path to the file
            to_version: Version to check (default: previous)

        Returns:
            Dict with 'possible', 'reason', and available methods
        """
        from erirpg.memory import load_knowledge
        from erirpg.registry import Registry

        # Find project name
        project_name = "unknown"
        registry = Registry.get_instance()
        for proj in registry.list():
            if os.path.abspath(proj.path) == os.path.abspath(self.project_path):
                project_name = proj.name
                break

        store = load_knowledge(self.project_path, project_name)
        learning = store.get_learning(file_path)

        result = {
            "possible": False,
            "reason": "",
            "snapshot_available": False,
            "git_available": False,
            "versions_count": 0,
            "current_version": 0,
        }

        if not learning:
            result["reason"] = f"No learning exists for {file_path}"
            return result

        result["versions_count"] = len(learning.versions)
        result["current_version"] = learning.current_version

        target = to_version if to_version is not None else learning.current_version - 1

        if target < 0:
            result["reason"] = "Already at first version"
            return result

        if target >= len(learning.versions):
            result["reason"] = f"Version {target} not found"
            return result

        version = learning.versions[target]

        result["snapshot_available"] = bool(version.files_content)
        result["git_available"] = bool(version.commit_before)

        if result["snapshot_available"] or result["git_available"]:
            result["possible"] = True
            methods = []
            if result["snapshot_available"]:
                methods.append("snapshot")
            if result["git_available"]:
                methods.append(f"git ({version.commit_before})")
            result["reason"] = f"Can rollback via: {', '.join(methods)}"
        else:
            result["reason"] = "No snapshot or git commit stored for this version"

        return result

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
    # Hard enforcement
    "get_active_agent",
    "require_preflight",
]
