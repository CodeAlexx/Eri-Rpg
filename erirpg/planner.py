"""
Planner for EriRPG.

Converts specs into executable plans with ordered steps, dependency tracking,
and verification commands.

Usage:
    spec = load_spec("my-task.json")
    plan = generate_plan(spec, graph, knowledge)
    plan.save("plan.json")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib
import json
import os

from erirpg.specs import BaseSpec, TaskSpec, ProjectSpec, TransplantSpec, load_spec


# Plan schema version
PLAN_VERSION = "1.0"


class StepType(Enum):
    """Types of plan steps."""
    READ = "read"           # Read/understand code
    EXTRACT = "extract"     # Extract feature from source
    CREATE = "create"       # Create new file/module
    MODIFY = "modify"       # Modify existing file
    WIRE = "wire"           # Wire up imports/connections
    VERIFY = "verify"       # Run verification command
    TEST = "test"           # Run tests
    LEARN = "learn"         # Store learning
    CHECKPOINT = "checkpoint"  # Save progress


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RiskLevel(Enum):
    """Risk level for steps."""
    LOW = "low"           # Safe operation
    MEDIUM = "medium"     # Moderate risk
    HIGH = "high"         # High impact, needs care
    CRITICAL = "critical" # Very risky, needs explicit approval


def _generate_step_id(step_type: str, target: str, index: int) -> str:
    """Generate a deterministic step ID."""
    content = f"{step_type}:{target}:{index}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"step-{index:02d}-{hash_val}"


def _generate_plan_id(spec_id: str) -> str:
    """Generate a plan ID from spec ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"plan-{spec_id[:20]}-{timestamp}"


@dataclass
class PlanStep:
    """A single step in an execution plan.

    Steps are atomic units of work with clear inputs, outputs,
    and verification criteria.
    """
    id: str = ""
    step_type: str = "read"  # StepType value
    target: str = ""         # Target file/module/feature
    action: str = ""         # Human-readable action description
    details: str = ""        # Detailed instructions

    # Dependencies and ordering
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    order: int = 0           # Execution order (lower = earlier)

    # Risk and verification
    risk: str = "low"        # RiskLevel value
    risk_reason: str = ""    # Why this risk level
    verify_command: str = "" # Command to verify step succeeded
    verify_expected: str = "" # Expected output from verify

    # Execution state
    status: str = "pending"  # StepStatus value
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: str = ""

    # Context
    inputs: List[str] = field(default_factory=list)   # Files/modules needed
    outputs: List[str] = field(default_factory=list)  # Files/modules produced
    notes: str = ""

    def validate(self) -> List[str]:
        """Validate the step. Returns list of error messages."""
        errors = []
        if not self.id:
            errors.append("id is required")
        if not self.target:
            errors.append("target is required")
        if not self.action:
            errors.append("action is required")

        valid_types = {t.value for t in StepType}
        if self.step_type not in valid_types:
            errors.append(f"step_type must be one of: {', '.join(valid_types)}")

        valid_statuses = {s.value for s in StepStatus}
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")

        valid_risks = {r.value for r in RiskLevel}
        if self.risk not in valid_risks:
            errors.append(f"risk must be one of: {', '.join(valid_risks)}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "step_type": self.step_type,
            "target": self.target,
            "action": self.action,
            "details": self.details,
            "depends_on": self.depends_on,
            "order": self.order,
            "risk": self.risk,
            "risk_reason": self.risk_reason,
            "verify_command": self.verify_command,
            "verify_expected": self.verify_expected,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            step_type=data.get("step_type", "read"),
            target=data.get("target", ""),
            action=data.get("action", ""),
            details=data.get("details", ""),
            depends_on=data.get("depends_on", []),
            order=data.get("order", 0),
            risk=data.get("risk", "low"),
            risk_reason=data.get("risk_reason", ""),
            verify_command=data.get("verify_command", ""),
            verify_expected=data.get("verify_expected", ""),
            status=data.get("status", "pending"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error", ""),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            notes=data.get("notes", ""),
        )

    def mark_in_progress(self) -> None:
        """Mark step as in progress."""
        self.status = StepStatus.IN_PROGRESS.value
        self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED.value
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED.value
        self.completed_at = datetime.now()
        self.error = error

    def mark_skipped(self, reason: str = "") -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED.value
        self.completed_at = datetime.now()
        if reason:
            self.notes = f"Skipped: {reason}"


@dataclass
class Plan:
    """An execution plan with ordered steps.

    Plans are deterministic - the same spec with the same context
    should always produce the same plan.
    """
    id: str = ""
    version: str = PLAN_VERSION
    spec_id: str = ""        # Source spec ID
    spec_type: str = ""      # Source spec type
    name: str = ""
    description: str = ""

    # Steps
    steps: List[PlanStep] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # Overall plan status

    # Context used to generate plan
    context_hash: str = ""   # Hash of graph + knowledge state

    # Statistics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0

    def validate(self) -> List[str]:
        """Validate the plan. Returns list of error messages."""
        errors = []
        if not self.id:
            errors.append("id is required")
        if not self.spec_id:
            errors.append("spec_id is required")
        if not self.steps:
            errors.append("plan must have at least one step")

        # Validate each step
        for i, step in enumerate(self.steps):
            step_errors = step.validate()
            for err in step_errors:
                errors.append(f"step[{i}]: {err}")

        # Check dependency references
        step_ids = {s.id for s in self.steps}
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(f"step {step.id} depends on unknown step: {dep_id}")

        # Check for circular dependencies
        if self._has_cycles():
            errors.append("plan has circular dependencies")

        return errors

    def _has_cycles(self) -> bool:
        """Check if dependency graph has cycles."""
        visited = set()
        rec_stack = set()

        step_map = {s.id: s for s in self.steps}

        def dfs(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = step_map.get(step_id)
            if step:
                for dep_id in step.depends_on:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(step_id)
            return False

        for step in self.steps:
            if step.id not in visited:
                if dfs(step.id):
                    return True

        return False

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next step that can be executed.

        Returns a pending step whose dependencies are all completed.
        """
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED.value}

        for step in sorted(self.steps, key=lambda s: s.order):
            if step.status != StepStatus.PENDING.value:
                continue

            # Check all dependencies are completed
            deps_satisfied = all(dep_id in completed_ids for dep_id in step.depends_on)
            if deps_satisfied:
                return step

        return None

    def get_ready_steps(self) -> List[PlanStep]:
        """Get all steps that are ready to execute (parallel execution)."""
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED.value}

        ready = []
        for step in sorted(self.steps, key=lambda s: s.order):
            if step.status != StepStatus.PENDING.value:
                continue

            deps_satisfied = all(dep_id in completed_ids for dep_id in step.depends_on)
            if deps_satisfied:
                ready.append(step)

        return ready

    def update_stats(self) -> None:
        """Update plan statistics from step statuses."""
        self.total_steps = len(self.steps)
        self.completed_steps = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED.value)
        self.failed_steps = sum(1 for s in self.steps if s.status == StepStatus.FAILED.value)
        self.updated_at = datetime.now()

        # Update overall status
        if self.failed_steps > 0:
            self.status = "failed"
        elif self.completed_steps == self.total_steps:
            self.status = "completed"
        elif any(s.status == StepStatus.IN_PROGRESS.value for s in self.steps):
            self.status = "in_progress"
        else:
            self.status = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "spec_id": self.spec_id,
            "spec_type": self.spec_type,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "context_hash": self.context_hash,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        """Deserialize from dictionary."""
        plan = cls(
            id=data.get("id", ""),
            version=data.get("version", PLAN_VERSION),
            spec_id=data.get("spec_id", ""),
            spec_type=data.get("spec_type", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=[PlanStep.from_dict(s) for s in data.get("steps", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            status=data.get("status", "pending"),
            context_hash=data.get("context_hash", ""),
            total_steps=data.get("total_steps", 0),
            completed_steps=data.get("completed_steps", 0),
            failed_steps=data.get("failed_steps", 0),
        )
        return plan

    def save(self, path: str) -> None:
        """Save plan to JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Plan":
        """Load plan from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines = [
            f"Plan: {self.name or self.id}",
            f"Status: {self.status}",
            f"Progress: {self.completed_steps}/{self.total_steps} steps",
            "",
            "Steps:",
        ]

        for step in sorted(self.steps, key=lambda s: s.order):
            status_icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "failed": "✗",
                "skipped": "○",
            }.get(step.status, "?")

            risk_badge = f" [{step.risk}]" if step.risk != "low" else ""
            lines.append(f"  {status_icon} {step.order}. {step.action}{risk_badge}")
            if step.error:
                lines.append(f"      Error: {step.error}")

        return "\n".join(lines)


# =============================================================================
# Plan Generation
# =============================================================================

def _compute_context_hash(graph: Any, knowledge: Any) -> str:
    """Compute hash of graph + knowledge state for reproducibility."""
    content = ""

    if graph:
        # Include module paths and their dependencies
        for path in sorted(graph.modules.keys()):
            mod = graph.get_module(path)
            deps = sorted(graph.get_dependencies(path))
            content += f"{path}:{','.join(deps)};"

    if knowledge:
        # Include learning paths
        for path in sorted(knowledge.learnings.keys()):
            content += f"L:{path};"

    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _assess_risk(module_path: str, graph: Any, action: str) -> Tuple[str, str]:
    """Assess risk level for modifying a module.

    Returns (risk_level, reason).
    """
    if not graph:
        return "low", ""

    # Get dependents
    try:
        dependents = graph.get_dependents(module_path) if hasattr(graph, 'get_dependents') else []
    except (ValueError, KeyError):
        dependents = []

    num_dependents = len(dependents) if dependents else 0

    if action == "create":
        return "low", "New file, no existing dependents"

    if num_dependents > 10:
        return "high", f"Many dependents ({num_dependents})"
    elif num_dependents > 5:
        return "medium", f"Some dependents ({num_dependents})"
    elif num_dependents > 0:
        return "low", f"Few dependents ({num_dependents})"
    else:
        return "low", "No dependents"


def generate_plan_for_task(
    spec: TaskSpec,
    graph: Any = None,
    knowledge: Any = None,
) -> Plan:
    """Generate an execution plan for a TaskSpec.

    Uses rule-based heuristics based on task type.
    """
    plan = Plan(
        id=_generate_plan_id(spec.id),
        spec_id=spec.id,
        spec_type="task",
        name=f"Plan for: {spec.name}",
        description=spec.description,
        context_hash=_compute_context_hash(graph, knowledge),
    )

    steps = []
    step_index = 0

    if spec.task_type == "extract":
        # Extract task: find modules → understand → extract
        steps.extend(_generate_extract_steps(spec, graph, knowledge, step_index))

    elif spec.task_type == "plan":
        # Plan task: load feature → analyze target → create mappings
        steps.extend(_generate_plan_task_steps(spec, graph, knowledge, step_index))

    elif spec.task_type == "implement":
        # Implement task: for each module in plan → create/modify → verify
        steps.extend(_generate_implement_steps(spec, graph, knowledge, step_index))

    elif spec.task_type == "validate":
        # Validate task: run tests → check outputs
        steps.extend(_generate_validate_steps(spec, graph, knowledge, step_index))

    else:
        # Generic task: read → understand → do → verify
        steps.extend(_generate_generic_steps(spec, graph, knowledge, step_index))

    plan.steps = steps
    plan.update_stats()

    return plan


def _generate_extract_steps(
    spec: TaskSpec,
    graph: Any,
    knowledge: Any,
    start_index: int,
) -> List[PlanStep]:
    """Generate steps for an extract task."""
    steps = []
    idx = start_index

    # Step 1: Find matching modules
    steps.append(PlanStep(
        id=_generate_step_id("read", "search", idx),
        step_type=StepType.READ.value,
        target=spec.source_project,
        action=f"Find modules matching: {spec.query}",
        details=f"Search {spec.source_project} for modules related to '{spec.query}'",
        order=idx,
        risk="low",
        inputs=[spec.source_project],
        outputs=["module_list"],
    ))
    idx += 1

    # Step 2: Read and understand each found module
    steps.append(PlanStep(
        id=_generate_step_id("read", "understand", idx),
        step_type=StepType.READ.value,
        target="found_modules",
        action="Read and understand matching modules",
        details="For each matching module, understand purpose and dependencies",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
        inputs=["module_list"],
        outputs=["understanding"],
    ))
    idx += 1

    # Step 3: Extract feature
    steps.append(PlanStep(
        id=_generate_step_id("extract", spec.query, idx),
        step_type=StepType.EXTRACT.value,
        target=spec.query,
        action=f"Extract feature: {spec.query}",
        details="Package modules, dependencies, and interfaces into feature JSON",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
        inputs=["understanding"],
        outputs=["feature.json"],
        verify_command="cat feature.json | jq .name",
        verify_expected=spec.query,
    ))
    idx += 1

    # Step 4: Store learnings
    steps.append(PlanStep(
        id=_generate_step_id("learn", "modules", idx),
        step_type=StepType.LEARN.value,
        target="extracted_modules",
        action="Store learnings for extracted modules",
        details="Save understanding of each module for future use",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
    ))

    return steps


def _generate_plan_task_steps(
    spec: TaskSpec,
    graph: Any,
    knowledge: Any,
    start_index: int,
) -> List[PlanStep]:
    """Generate steps for a plan task."""
    steps = []
    idx = start_index

    # Step 1: Load feature file
    steps.append(PlanStep(
        id=_generate_step_id("read", "feature", idx),
        step_type=StepType.READ.value,
        target=spec.feature_file,
        action=f"Load feature from {spec.feature_file}",
        details="Parse feature JSON and understand components",
        order=idx,
        risk="low",
        inputs=[spec.feature_file],
        outputs=["feature_data"],
    ))
    idx += 1

    # Step 2: Analyze target project
    steps.append(PlanStep(
        id=_generate_step_id("read", "target", idx),
        step_type=StepType.READ.value,
        target=spec.target_project,
        action=f"Analyze target project: {spec.target_project}",
        details="Understand target structure and find integration points",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
        inputs=["feature_data", spec.target_project],
        outputs=["target_analysis"],
    ))
    idx += 1

    # Step 3: Create mappings
    steps.append(PlanStep(
        id=_generate_step_id("create", "mappings", idx),
        step_type=StepType.CREATE.value,
        target="transplant_plan",
        action="Create transplant mappings",
        details="Map source components to target locations",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
        inputs=["feature_data", "target_analysis"],
        outputs=["plan.json"],
    ))

    return steps


def _generate_implement_steps(
    spec: TaskSpec,
    graph: Any,
    knowledge: Any,
    start_index: int,
) -> List[PlanStep]:
    """Generate steps for an implement task."""
    steps = []
    idx = start_index

    # Step 1: Load plan
    steps.append(PlanStep(
        id=_generate_step_id("read", "plan", idx),
        step_type=StepType.READ.value,
        target=spec.plan_file or "plan.json",
        action="Load transplant plan",
        details="Parse plan and understand implementation steps",
        order=idx,
        risk="low",
    ))
    idx += 1

    # Step 2: Create/modify modules (generic - would be expanded)
    risk, risk_reason = _assess_risk(spec.target_project, graph, "modify")
    steps.append(PlanStep(
        id=_generate_step_id("modify", "target", idx),
        step_type=StepType.MODIFY.value,
        target=spec.target_project,
        action="Implement changes in target project",
        details="Create new files and modify existing ones per plan",
        depends_on=[steps[-1].id],
        order=idx,
        risk=risk,
        risk_reason=risk_reason,
    ))
    idx += 1

    # Step 3: Wire up imports
    steps.append(PlanStep(
        id=_generate_step_id("wire", "imports", idx),
        step_type=StepType.WIRE.value,
        target=spec.target_project,
        action="Wire up imports and connections",
        details="Add imports, update __init__.py, connect to existing code",
        depends_on=[steps[-1].id],
        order=idx,
        risk="medium",
        risk_reason="Modifying existing files",
    ))
    idx += 1

    # Step 4: Verify
    steps.append(PlanStep(
        id=_generate_step_id("verify", "implementation", idx),
        step_type=StepType.VERIFY.value,
        target=spec.target_project,
        action="Verify implementation",
        details="Check imports work, no syntax errors",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
        verify_command="python -m py_compile target_file.py",
    ))

    return steps


def _generate_validate_steps(
    spec: TaskSpec,
    graph: Any,
    knowledge: Any,
    start_index: int,
) -> List[PlanStep]:
    """Generate steps for a validate task."""
    steps = []
    idx = start_index

    # Step 1: Run tests
    steps.append(PlanStep(
        id=_generate_step_id("test", "run", idx),
        step_type=StepType.TEST.value,
        target=spec.target_project,
        action="Run test suite",
        details="Execute project tests to verify implementation",
        order=idx,
        risk="low",
        verify_command="pytest",
    ))
    idx += 1

    # Step 2: Check outputs
    steps.append(PlanStep(
        id=_generate_step_id("verify", "outputs", idx),
        step_type=StepType.VERIFY.value,
        target=spec.target_project,
        action="Verify expected outputs",
        details="Check that expected files exist and have correct content",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
    ))
    idx += 1

    # Step 3: Checkpoint
    steps.append(PlanStep(
        id=_generate_step_id("checkpoint", "complete", idx),
        step_type=StepType.CHECKPOINT.value,
        target="validation",
        action="Mark validation complete",
        details="Save validation results and update status",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
    ))

    return steps


def _generate_generic_steps(
    spec: TaskSpec,
    graph: Any,
    knowledge: Any,
    start_index: int,
) -> List[PlanStep]:
    """Generate generic steps for untyped tasks."""
    steps = []
    idx = start_index

    # Step 1: Understand task
    steps.append(PlanStep(
        id=_generate_step_id("read", "understand", idx),
        step_type=StepType.READ.value,
        target=spec.source_project or spec.target_project or "project",
        action=f"Understand: {spec.name}",
        details=spec.description or "Analyze requirements and current state",
        order=idx,
        risk="low",
    ))
    idx += 1

    # Step 2: Execute task
    steps.append(PlanStep(
        id=_generate_step_id("modify", "execute", idx),
        step_type=StepType.MODIFY.value,
        target="project",
        action=f"Execute: {spec.name}",
        details="Perform the required changes",
        depends_on=[steps[-1].id],
        order=idx,
        risk="medium",
        risk_reason="Task-specific changes",
    ))
    idx += 1

    # Step 3: Verify
    steps.append(PlanStep(
        id=_generate_step_id("verify", "result", idx),
        step_type=StepType.VERIFY.value,
        target="project",
        action="Verify changes",
        details="Confirm changes work correctly",
        depends_on=[steps[-1].id],
        order=idx,
        risk="low",
    ))

    return steps


def generate_plan_for_project(
    spec: ProjectSpec,
    graph: Any = None,
    knowledge: Any = None,
) -> Plan:
    """Generate an execution plan for a ProjectSpec."""
    plan = Plan(
        id=_generate_plan_id(spec.id),
        spec_id=spec.id,
        spec_type="project",
        name=f"Create project: {spec.name}",
        description=spec.description,
        context_hash=_compute_context_hash(graph, knowledge),
    )

    steps = []
    idx = 0

    # Step 1: Create directory structure
    steps.append(PlanStep(
        id=_generate_step_id("create", "structure", idx),
        step_type=StepType.CREATE.value,
        target=spec.output_path or spec.name,
        action=f"Create project structure for {spec.name}",
        details=f"Create directories: {', '.join(spec.directories)}",
        order=idx,
        risk="low",
        outputs=spec.directories,
    ))
    idx += 1

    # Step 2: Create initial files
    for file_path in spec.files:
        steps.append(PlanStep(
            id=_generate_step_id("create", file_path, idx),
            step_type=StepType.CREATE.value,
            target=file_path,
            action=f"Create {file_path}",
            details=f"Create file with initial content",
            depends_on=[steps[0].id],  # Depends on structure creation
            order=idx,
            risk="low",
            outputs=[file_path],
        ))
        idx += 1

    # Step 3: Verify structure
    steps.append(PlanStep(
        id=_generate_step_id("verify", "structure", idx),
        step_type=StepType.VERIFY.value,
        target=spec.output_path or spec.name,
        action="Verify project structure",
        details="Check all files and directories exist",
        depends_on=[s.id for s in steps[1:]],  # Depends on all file creations
        order=idx,
        risk="low",
        verify_command=f"ls -la {spec.output_path or spec.name}",
    ))

    plan.steps = steps
    plan.update_stats()

    return plan


def generate_plan_for_transplant(
    spec: TransplantSpec,
    graph: Any = None,
    knowledge: Any = None,
) -> Plan:
    """Generate an execution plan for a TransplantSpec."""
    plan = Plan(
        id=_generate_plan_id(spec.id),
        spec_id=spec.id,
        spec_type="transplant",
        name=f"Transplant {spec.feature_name} to {spec.target_project}",
        description=spec.description,
        context_hash=_compute_context_hash(graph, knowledge),
    )

    steps = []
    idx = 0

    # Step 1: Load feature (if from file)
    if spec.feature_file:
        steps.append(PlanStep(
            id=_generate_step_id("read", "feature", idx),
            step_type=StepType.READ.value,
            target=spec.feature_file,
            action=f"Load feature from {spec.feature_file}",
            details="Parse feature JSON",
            order=idx,
            risk="low",
            inputs=[spec.feature_file],
        ))
        idx += 1

    # Step 2: Analyze source components
    steps.append(PlanStep(
        id=_generate_step_id("read", "source", idx),
        step_type=StepType.READ.value,
        target=spec.source_project,
        action=f"Analyze source: {spec.source_project}",
        details=f"Understand components: {', '.join(spec.components[:3])}{'...' if len(spec.components) > 3 else ''}",
        depends_on=[steps[-1].id] if steps else [],
        order=idx,
        risk="low",
    ))
    idx += 1

    # Step 3: Create files in order
    for component in spec.generation_order or spec.components:
        risk, risk_reason = _assess_risk(component, graph, "create")
        steps.append(PlanStep(
            id=_generate_step_id("create", component, idx),
            step_type=StepType.CREATE.value,
            target=component,
            action=f"Create {component}",
            details="Transplant source code with adaptations",
            depends_on=[steps[-1].id],
            order=idx,
            risk=risk,
            risk_reason=risk_reason,
            outputs=[component],
        ))
        idx += 1

    # Step 4: Apply mappings (wiring)
    if spec.mappings:
        steps.append(PlanStep(
            id=_generate_step_id("wire", "mappings", idx),
            step_type=StepType.WIRE.value,
            target=spec.target_project,
            action="Apply interface mappings",
            details=f"Wire {len(spec.mappings)} interface connections",
            depends_on=[steps[-1].id] if steps else [],
            order=idx,
            risk="medium",
            risk_reason="Modifying existing interfaces",
        ))
        idx += 1

    # Step 5: Verify transplant
    steps.append(PlanStep(
        id=_generate_step_id("verify", "transplant", idx),
        step_type=StepType.VERIFY.value,
        target=spec.target_project,
        action="Verify transplant",
        details="Check imports, syntax, and basic functionality",
        depends_on=[steps[-1].id] if steps else [],
        order=idx,
        risk="low",
    ))

    plan.steps = steps
    plan.update_stats()

    return plan


def generate_plan(
    spec: BaseSpec,
    graph: Any = None,
    knowledge: Any = None,
) -> Plan:
    """Generate an execution plan for any spec type.

    Factory function that dispatches to type-specific generators.
    """
    if isinstance(spec, TaskSpec):
        return generate_plan_for_task(spec, graph, knowledge)
    elif isinstance(spec, ProjectSpec):
        return generate_plan_for_project(spec, graph, knowledge)
    elif isinstance(spec, TransplantSpec):
        return generate_plan_for_transplant(spec, graph, knowledge)
    else:
        raise ValueError(f"Unknown spec type: {type(spec)}")


# =============================================================================
# Dependency Ordering
# =============================================================================

def order_steps_by_dependencies(steps: List[PlanStep]) -> List[PlanStep]:
    """Order steps respecting dependencies (topological sort).

    Returns a new list with steps ordered so that dependencies come first.
    """
    # Build dependency graph
    step_map = {s.id: s for s in steps}
    in_degree = {s.id: 0 for s in steps}

    for step in steps:
        for dep_id in step.depends_on:
            if dep_id in in_degree:
                in_degree[step.id] += 1

    # Kahn's algorithm
    queue = [s for s in steps if in_degree[s.id] == 0]
    ordered = []

    while queue:
        # Sort by order field for determinism among peers
        queue.sort(key=lambda s: s.order)
        step = queue.pop(0)
        ordered.append(step)

        # Decrease in-degree of dependents
        for other in steps:
            if step.id in other.depends_on:
                in_degree[other.id] -= 1
                if in_degree[other.id] == 0:
                    queue.append(other)

    # Update order field
    for i, step in enumerate(ordered):
        step.order = i

    return ordered


# =============================================================================
# Plan Storage
# =============================================================================

def get_plans_dir(project_path: str) -> str:
    """Get the plans directory for a project."""
    return os.path.join(project_path, ".eri-rpg", "plans")


def list_plans(project_path: str) -> List[str]:
    """List all plans in a project."""
    plans_dir = get_plans_dir(project_path)
    if not os.path.exists(plans_dir):
        return []

    return sorted([
        os.path.join(plans_dir, f)
        for f in os.listdir(plans_dir)
        if f.endswith(".json")
    ])


def save_plan_to_project(plan: Plan, project_path: str) -> str:
    """Save a plan to the project's plans directory."""
    plans_dir = get_plans_dir(project_path)
    os.makedirs(plans_dir, exist_ok=True)

    filename = f"{plan.id}.json"
    path = os.path.join(plans_dir, filename)

    plan.save(path)
    return path


# =============================================================================
# Spec-Driven Planner (New System)
# =============================================================================

@dataclass
class Planner:
    """Generates execution specs from goals.

    This is the NEW spec-driven planner that replaces ad-hoc goal parsing.
    It analyzes goals, project structure, and existing knowledge to produce
    ordered steps with dependencies and verification.

    Usage:
        from erirpg.planner import Planner
        from erirpg.spec import Spec

        planner = Planner(project, graph, knowledge)
        spec = planner.plan("add logging to config.py")
    """

    project: str
    graph: Any = None
    knowledge: Any = None

    def plan(self, goal: str) -> "Spec":
        """
        Generate a spec from a goal.

        Analyzes the goal, project structure, and existing
        knowledge to produce ordered steps.
        """
        from erirpg.spec import Spec, Step, generate_spec_id

        spec_id = generate_spec_id(goal)
        goal_lower = goal.lower()

        # Detect goal type and generate appropriate steps
        if self._is_transplant(goal_lower):
            steps = self._plan_transplant_steps(goal)
        elif self._is_refactor(goal_lower):
            steps = self._plan_refactor_steps(goal)
        elif self._is_create(goal_lower):
            steps = self._plan_create_steps(goal)
        elif self._is_modify(goal_lower):
            steps = self._plan_modify_steps(goal)
        elif self._is_fix(goal_lower):
            steps = self._plan_fix_steps(goal)
        else:
            steps = self._plan_generic_steps(goal)

        # Add verification based on project type
        verification = self._detect_verification()

        return Spec(
            id=spec_id,
            goal=goal,
            project=self.project,
            steps=steps,
            verification=verification,
        )

    def _is_transplant(self, goal: str) -> bool:
        return "transplant" in goal or ("from" in goal and "to" in goal)

    def _is_refactor(self, goal: str) -> bool:
        return "refactor" in goal or "restructure" in goal or "reorganize" in goal

    def _is_create(self, goal: str) -> bool:
        return "create" in goal or "add new" in goal or "implement new" in goal

    def _is_modify(self, goal: str) -> bool:
        return "modify" in goal or "update" in goal or "change" in goal or "add" in goal

    def _is_fix(self, goal: str) -> bool:
        return "fix" in goal or "bug" in goal or "error" in goal or "issue" in goal

    def _plan_transplant_steps(self, goal: str) -> List["Step"]:
        """Plan a transplant operation."""
        from erirpg.spec import Step

        return [
            Step(
                id="learn-source",
                action="learn",
                targets=[],
                description="Understand source module and its dependencies",
                verification="Knowledge stored for source files",
            ),
            Step(
                id="learn-target",
                action="learn",
                targets=[],
                description="Understand target integration points",
                depends_on=["learn-source"],
                verification="Knowledge stored for target files",
            ),
            Step(
                id="implement",
                action="create",
                targets=[],
                description="Transplant feature to target project",
                depends_on=["learn-target"],
                verification="Files created/modified as planned",
            ),
            Step(
                id="wire",
                action="modify",
                targets=[],
                description="Connect transplanted code to existing system",
                depends_on=["implement"],
                verification="Feature is accessible from existing code",
            ),
            Step(
                id="verify",
                action="verify",
                targets=[],
                description="Run tests and verify transplant works",
                depends_on=["wire"],
                verification="All tests pass",
            ),
        ]

    def _plan_refactor_steps(self, goal: str) -> List["Step"]:
        """Plan a refactoring operation."""
        from erirpg.spec import Step
        targets = self._find_targets(goal)

        return [
            Step(
                id="learn",
                action="learn",
                targets=targets,
                description="Understand current implementation",
                verification="Knowledge stored for target files",
            ),
            Step(
                id="analyze",
                action="learn",
                targets=[],
                description="Identify all affected modules",
                depends_on=["learn"],
                verification="Impact zone documented",
            ),
            Step(
                id="refactor",
                action="refactor",
                targets=[],
                description="Apply refactoring changes",
                depends_on=["analyze"],
                verification="Code refactored without changing behavior",
            ),
            Step(
                id="update-deps",
                action="modify",
                targets=[],
                description="Update dependent modules if needed",
                depends_on=["refactor"],
                verification="All imports and references updated",
            ),
            Step(
                id="verify",
                action="verify",
                targets=[],
                description="Run tests and verify behavior unchanged",
                depends_on=["update-deps"],
                verification="All tests pass",
            ),
        ]

    def _plan_create_steps(self, goal: str) -> List["Step"]:
        """Plan creating new functionality."""
        from erirpg.spec import Step
        targets = self._find_targets(goal)

        return [
            Step(
                id="learn-context",
                action="learn",
                targets=[],
                description="Understand where new code will integrate",
                verification="Integration points identified",
            ),
            Step(
                id="create",
                action="create",
                targets=targets,
                description="Create new files/functions",
                depends_on=["learn-context"],
                verification="New code created",
            ),
            Step(
                id="wire",
                action="modify",
                targets=[],
                description="Connect new code to existing system",
                depends_on=["create"],
                verification="New code is accessible",
            ),
            Step(
                id="test",
                action="create",
                targets=[],
                description="Add tests for new functionality",
                depends_on=["wire"],
                verification="Tests written and passing",
            ),
        ]

    def _plan_modify_steps(self, goal: str) -> List["Step"]:
        """Plan modifying existing code."""
        from erirpg.spec import Step
        targets = self._find_targets(goal)

        steps = []

        if targets:
            steps.append(Step(
                id="learn",
                action="learn",
                targets=targets,
                description="Understand current implementation",
                verification="Knowledge stored for target files",
            ))
            depends = ["learn"]
        else:
            depends = []

        steps.append(Step(
            id="modify",
            action="modify",
            targets=targets,
            description=f"Apply changes: {goal}",
            depends_on=depends,
            verification="Changes applied correctly",
        ))

        steps.append(Step(
            id="verify",
            action="verify",
            targets=[],
            description="Run tests and verify changes",
            depends_on=["modify"],
            verification="All tests pass",
        ))

        return steps

    def _plan_fix_steps(self, goal: str) -> List["Step"]:
        """Plan fixing a bug."""
        from erirpg.spec import Step
        targets = self._find_targets(goal)

        return [
            Step(
                id="investigate",
                action="learn",
                targets=targets,
                description="Find and understand the root cause",
                verification="Root cause identified",
            ),
            Step(
                id="fix",
                action="modify",
                targets=[],
                description="Apply the fix",
                depends_on=["investigate"],
                verification="Bug fixed",
            ),
            Step(
                id="test",
                action="verify",
                targets=[],
                description="Verify fix and add regression test",
                depends_on=["fix"],
                verification="Bug doesn't recur, tests pass",
            ),
        ]

    def _plan_generic_steps(self, goal: str) -> List["Step"]:
        """Plan a generic operation."""
        from erirpg.spec import Step
        targets = self._find_targets(goal)

        return [
            Step(
                id="execute",
                action="modify",
                targets=targets,
                description=goal,
                verification="Goal accomplished",
            ),
            Step(
                id="verify",
                action="verify",
                targets=[],
                description="Verify the result",
                depends_on=["execute"],
                verification="All tests pass",
            ),
        ]

    def _find_targets(self, goal: str) -> List[str]:
        """Extract file targets from goal text."""
        import re
        targets = []

        # Pattern: common file extensions
        file_pattern = r'[\w/.-]+\.(?:py|rs|ts|js|go|c|h|cpp|hpp)'
        matches = re.findall(file_pattern, goal)
        targets.extend(matches)

        # If we have a graph, try to find matching modules
        if self.graph and not targets:
            for module_path in self.graph.modules.keys():
                module_name = module_path.split('/')[-1].replace('.py', '')
                if module_name.lower() in goal.lower():
                    targets.append(module_path)

        return targets

    def _detect_verification(self) -> List[str]:
        """Detect project verification commands."""
        return ["pytest"]

    def _get_unknown_files(self, files: List[str]) -> List[str]:
        """Get files we don't have knowledge for."""
        if not self.knowledge:
            return files

        unknown = []
        for f in files:
            if not self.knowledge.get_learning(f):
                unknown.append(f)

        return unknown

    def _get_dependencies(self, files: List[str]) -> Set[str]:
        """Get all dependencies of given files."""
        deps = set()

        if not self.graph:
            return deps

        for f in files:
            module_deps = self.graph.get_deps(f)
            deps.update(module_deps)

            for d in module_deps:
                transitive = self.graph.get_transitive_deps(d)
                deps.update(transitive)

        return deps

    def _get_dependents(self, files: List[str]) -> Set[str]:
        """Get all modules that depend on given files."""
        dependents = set()

        if not self.graph:
            return dependents

        for f in files:
            direct = self.graph.get_dependents(f)
            dependents.update(direct)

            transitive = self.graph.get_transitive_dependents(f)
            dependents.update(transitive)

        return dependents
