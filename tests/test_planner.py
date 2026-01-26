"""
Test Phase 4: Planner.

Tests for plan models, generation, dependency ordering, and CLI commands.
"""

import json
import os
import pytest
from datetime import datetime

from erirpg.planner import (
    PLAN_VERSION,
    PlanStep,
    Plan,
    StepType,
    StepStatus,
    RiskLevel,
    generate_plan,
    generate_plan_for_task,
    generate_plan_for_project,
    generate_plan_for_transplant,
    order_steps_by_dependencies,
    get_plans_dir,
    list_plans,
    save_plan_to_project,
)
from erirpg.specs import TaskSpec, ProjectSpec, TransplantSpec


class TestPlanStep:
    """Tests for PlanStep model."""

    def test_plan_step_defaults(self):
        """Step should have sensible defaults."""
        step = PlanStep()
        assert step.step_type == "read"
        assert step.status == "pending"
        assert step.risk == "low"
        assert step.depends_on == []
        assert step.order == 0

    def test_plan_step_validate_requires_id(self):
        """Validation should require id."""
        step = PlanStep(target="test", action="Test action")
        errors = step.validate()
        assert "id is required" in errors

    def test_plan_step_validate_requires_target(self):
        """Validation should require target."""
        step = PlanStep(id="step-1", action="Test action")
        errors = step.validate()
        assert "target is required" in errors

    def test_plan_step_validate_requires_action(self):
        """Validation should require action."""
        step = PlanStep(id="step-1", target="test")
        errors = step.validate()
        assert "action is required" in errors

    def test_plan_step_validate_step_type(self):
        """Validation should check step_type values."""
        step = PlanStep(id="step-1", target="test", action="Test", step_type="invalid")
        errors = step.validate()
        assert any("step_type" in e for e in errors)

    def test_plan_step_validate_status(self):
        """Validation should check status values."""
        step = PlanStep(id="step-1", target="test", action="Test", status="invalid")
        errors = step.validate()
        assert any("status" in e for e in errors)

    def test_plan_step_validate_risk(self):
        """Validation should check risk values."""
        step = PlanStep(id="step-1", target="test", action="Test", risk="invalid")
        errors = step.validate()
        assert any("risk" in e for e in errors)

    def test_plan_step_valid(self):
        """Valid step should pass validation."""
        step = PlanStep(id="step-1", target="module.py", action="Read module")
        errors = step.validate()
        assert errors == []

    def test_plan_step_mark_in_progress(self):
        """Should update status and set started_at."""
        step = PlanStep(id="step-1", target="test", action="Test")
        step.mark_in_progress()
        assert step.status == "in_progress"
        assert step.started_at is not None

    def test_plan_step_mark_completed(self):
        """Should update status and set completed_at."""
        step = PlanStep(id="step-1", target="test", action="Test")
        step.mark_completed()
        assert step.status == "completed"
        assert step.completed_at is not None

    def test_plan_step_mark_failed(self):
        """Should update status and set error."""
        step = PlanStep(id="step-1", target="test", action="Test")
        step.mark_failed("Something went wrong")
        assert step.status == "failed"
        assert step.error == "Something went wrong"
        assert step.completed_at is not None

    def test_plan_step_mark_skipped(self):
        """Should update status and optionally set notes."""
        step = PlanStep(id="step-1", target="test", action="Test")
        step.mark_skipped("Not needed")
        assert step.status == "skipped"
        assert "Skipped: Not needed" in step.notes

    def test_plan_step_serialization_roundtrip(self):
        """Step should survive serialization roundtrip."""
        step = PlanStep(
            id="step-1",
            step_type="create",
            target="module.py",
            action="Create module",
            details="Create a new module",
            depends_on=["step-0"],
            order=1,
            risk="medium",
            risk_reason="Has dependents",
            verify_command="python -c 'import module'",
            inputs=["spec.json"],
            outputs=["module.py"],
        )
        data = step.to_dict()
        restored = PlanStep.from_dict(data)

        assert restored.id == step.id
        assert restored.step_type == step.step_type
        assert restored.target == step.target
        assert restored.depends_on == step.depends_on
        assert restored.risk == step.risk


class TestPlan:
    """Tests for Plan model."""

    def test_plan_defaults(self):
        """Plan should have sensible defaults."""
        plan = Plan()
        assert plan.version == PLAN_VERSION
        assert plan.status == "pending"
        assert plan.steps == []
        assert plan.total_steps == 0

    def test_plan_validate_requires_id(self):
        """Validation should require id."""
        plan = Plan(spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="test", action="Test")
        ])
        errors = plan.validate()
        assert "id is required" in errors

    def test_plan_validate_requires_spec_id(self):
        """Validation should require spec_id."""
        plan = Plan(id="plan-1", steps=[
            PlanStep(id="step-1", target="test", action="Test")
        ])
        errors = plan.validate()
        assert "spec_id is required" in errors

    def test_plan_validate_requires_steps(self):
        """Validation should require at least one step."""
        plan = Plan(id="plan-1", spec_id="spec-1")
        errors = plan.validate()
        assert "plan must have at least one step" in errors

    def test_plan_validate_step_errors(self):
        """Validation should include step validation errors."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1")  # Missing target and action
        ])
        errors = plan.validate()
        assert any("step[0]" in e for e in errors)

    def test_plan_validate_dependency_references(self):
        """Validation should check dependency references exist."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="test", action="Test", depends_on=["step-0"])
        ])
        errors = plan.validate()
        assert any("unknown step" in e for e in errors)

    def test_plan_validate_circular_dependencies(self):
        """Validation should detect circular dependencies."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", depends_on=["step-2"]),
            PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"]),
        ])
        errors = plan.validate()
        assert any("circular" in e for e in errors)

    def test_plan_valid(self):
        """Valid plan should pass validation."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A"),
            PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"]),
        ])
        errors = plan.validate()
        assert errors == []

    def test_plan_get_step(self):
        """Should find step by ID."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A"),
            PlanStep(id="step-2", target="b", action="B"),
        ])
        step = plan.get_step("step-2")
        assert step is not None
        assert step.target == "b"

    def test_plan_get_step_not_found(self):
        """Should return None for unknown step."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[])
        assert plan.get_step("unknown") is None

    def test_plan_get_next_step_no_deps(self):
        """Should return first pending step when no deps."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", order=0),
            PlanStep(id="step-2", target="b", action="B", order=1),
        ])
        next_step = plan.get_next_step()
        assert next_step.id == "step-1"

    def test_plan_get_next_step_respects_deps(self):
        """Should respect dependencies when getting next step."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", order=0),
            PlanStep(id="step-2", target="b", action="B", order=1, depends_on=["step-1"]),
        ])

        # First step is available
        next_step = plan.get_next_step()
        assert next_step.id == "step-1"

        # Complete first step
        plan.steps[0].mark_completed()

        # Now second step is available
        next_step = plan.get_next_step()
        assert next_step.id == "step-2"

    def test_plan_get_next_step_blocked(self):
        """Should return None when all steps are blocked."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", depends_on=["step-2"]),
            PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"]),
        ])
        # Both steps depend on each other (shouldn't happen but testing edge case)
        assert plan.get_next_step() is None

    def test_plan_get_ready_steps(self):
        """Should return all steps that can run in parallel."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", order=0),
            PlanStep(id="step-2", target="b", action="B", order=1),
            PlanStep(id="step-3", target="c", action="C", order=2, depends_on=["step-1", "step-2"]),
        ])
        ready = plan.get_ready_steps()
        assert len(ready) == 2
        assert {s.id for s in ready} == {"step-1", "step-2"}

    def test_plan_update_stats(self):
        """Should update statistics from step statuses."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", status="completed"),
            PlanStep(id="step-2", target="b", action="B", status="pending"),
            PlanStep(id="step-3", target="c", action="C", status="failed"),
        ])
        plan.update_stats()

        assert plan.total_steps == 3
        assert plan.completed_steps == 1
        assert plan.failed_steps == 1
        assert plan.status == "failed"  # Any failure = failed

    def test_plan_update_stats_completed(self):
        """Status should be completed when all steps done."""
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[
            PlanStep(id="step-1", target="a", action="A", status="completed"),
            PlanStep(id="step-2", target="b", action="B", status="completed"),
        ])
        plan.update_stats()
        assert plan.status == "completed"

    def test_plan_serialization_roundtrip(self):
        """Plan should survive serialization roundtrip."""
        plan = Plan(
            id="plan-1",
            spec_id="spec-1",
            spec_type="task",
            name="Test Plan",
            description="A test plan",
            steps=[
                PlanStep(id="step-1", target="a", action="A"),
                PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"]),
            ],
            context_hash="abc123",
        )
        plan.update_stats()

        data = plan.to_dict()
        restored = Plan.from_dict(data)

        assert restored.id == plan.id
        assert restored.spec_id == plan.spec_id
        assert restored.name == plan.name
        assert len(restored.steps) == 2
        assert restored.steps[1].depends_on == ["step-1"]

    def test_plan_format_summary(self):
        """Should format human-readable summary."""
        plan = Plan(
            id="plan-1",
            spec_id="spec-1",
            name="Test Plan",
            steps=[
                PlanStep(id="step-1", target="a", action="Do A", order=0, status="completed"),
                PlanStep(id="step-2", target="b", action="Do B", order=1, risk="high"),
            ],
        )
        plan.update_stats()

        summary = plan.format_summary()
        assert "Test Plan" in summary
        assert "Do A" in summary
        assert "Do B" in summary
        assert "[high]" in summary
        assert "●" in summary  # completed icon


class TestPlanGeneration:
    """Tests for plan generation from specs."""

    def test_generate_plan_for_extract_task(self):
        """Should generate steps for extract task."""
        spec = TaskSpec(
            id="task-1",
            name="Extract loss function",
            task_type="extract",
            source_project="onetrainer",
            query="masked loss",
        )
        plan = generate_plan_for_task(spec)

        assert plan.spec_id == "task-1"
        assert plan.spec_type == "task"
        assert len(plan.steps) >= 3  # At least: find, understand, extract
        assert any(s.step_type == "extract" for s in plan.steps)

    def test_generate_plan_for_plan_task(self):
        """Should generate steps for plan task."""
        spec = TaskSpec(
            id="task-1",
            name="Plan transplant",
            task_type="plan",
            feature_file="/path/to/feature.json",
            target_project="eritrainer",
        )
        plan = generate_plan_for_task(spec)

        assert len(plan.steps) >= 2
        assert any("Load feature" in s.action for s in plan.steps)
        assert any("target" in s.action.lower() for s in plan.steps)

    def test_generate_plan_for_implement_task(self):
        """Should generate steps for implement task."""
        spec = TaskSpec(
            id="task-1",
            name="Implement changes",
            task_type="implement",
            target_project="eritrainer",
        )
        plan = generate_plan_for_task(spec)

        assert len(plan.steps) >= 3
        assert any(s.step_type == "modify" for s in plan.steps)
        assert any(s.step_type == "wire" for s in plan.steps)
        assert any(s.step_type == "verify" for s in plan.steps)

    def test_generate_plan_for_validate_task(self):
        """Should generate steps for validate task."""
        spec = TaskSpec(
            id="task-1",
            name="Validate implementation",
            task_type="validate",
            target_project="eritrainer",
        )
        plan = generate_plan_for_task(spec)

        assert len(plan.steps) >= 2
        assert any(s.step_type == "test" for s in plan.steps)
        assert any(s.step_type == "verify" for s in plan.steps)

    def test_generate_plan_for_generic_task(self):
        """Should generate generic steps for untyped task."""
        spec = TaskSpec(
            id="task-1",
            name="Do something",
            source_project="project",
        )
        plan = generate_plan_for_task(spec)

        assert len(plan.steps) >= 2
        assert any(s.step_type == "read" for s in plan.steps)
        assert any(s.step_type == "verify" for s in plan.steps)

    def test_generate_plan_for_project(self):
        """Should generate steps for project creation."""
        spec = ProjectSpec(
            id="proj-1",
            name="my-app",
            core_feature="CLI tool",
            directories=["src", "tests"],
            files=["src/main.py", "tests/test_main.py"],
        )
        plan = generate_plan_for_project(spec)

        assert plan.spec_type == "project"
        # Should have: create structure + create each file + verify
        assert len(plan.steps) >= 4
        assert any(s.step_type == "create" for s in plan.steps)
        assert any(s.step_type == "verify" for s in plan.steps)

    def test_generate_plan_for_transplant(self):
        """Should generate steps for transplant."""
        spec = TransplantSpec(
            id="trans-1",
            name="transplant-loss",
            source_project="onetrainer",
            target_project="eritrainer",
            feature_name="masked_loss",
            components=["util/loss.py", "training/trainer.py"],
            mappings=[{"source": "compute_loss", "target": "new"}],
        )
        plan = generate_plan_for_transplant(spec)

        assert plan.spec_type == "transplant"
        assert len(plan.steps) >= 4  # read source + create each + wire + verify
        assert any(s.step_type == "create" for s in plan.steps)
        assert any(s.step_type == "wire" for s in plan.steps)

    def test_generate_plan_factory(self):
        """Factory should dispatch to correct generator."""
        task_spec = TaskSpec(id="t1", name="Task", task_type="extract", source_project="p", query="q")
        project_spec = ProjectSpec(id="p1", name="Project", core_feature="test")
        transplant_spec = TransplantSpec(id="tr1", name="Trans", source_project="a", target_project="b", feature_name="f")

        task_plan = generate_plan(task_spec)
        project_plan = generate_plan(project_spec)
        transplant_plan = generate_plan(transplant_spec)

        assert task_plan.spec_type == "task"
        assert project_plan.spec_type == "project"
        assert transplant_plan.spec_type == "transplant"

    def test_generate_plan_deterministic(self):
        """Same spec should produce same plan structure."""
        spec = TaskSpec(
            id="task-1",
            name="Extract feature",
            task_type="extract",
            source_project="project",
            query="feature",
        )

        plan1 = generate_plan_for_task(spec)
        plan2 = generate_plan_for_task(spec)

        # Step count and types should be the same
        assert len(plan1.steps) == len(plan2.steps)
        assert [s.step_type for s in plan1.steps] == [s.step_type for s in plan2.steps]
        assert [s.action for s in plan1.steps] == [s.action for s in plan2.steps]


class TestDependencyOrdering:
    """Tests for dependency ordering."""

    def test_order_steps_simple(self):
        """Should order steps respecting dependencies."""
        steps = [
            PlanStep(id="step-3", target="c", action="C", depends_on=["step-2"], order=2),
            PlanStep(id="step-1", target="a", action="A", order=0),
            PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"], order=1),
        ]

        ordered = order_steps_by_dependencies(steps)

        # step-1 must come before step-2, step-2 before step-3
        ids = [s.id for s in ordered]
        assert ids.index("step-1") < ids.index("step-2")
        assert ids.index("step-2") < ids.index("step-3")

    def test_order_steps_parallel(self):
        """Should maintain relative order for independent steps."""
        steps = [
            PlanStep(id="step-1", target="a", action="A", order=0),
            PlanStep(id="step-2", target="b", action="B", order=1),
            PlanStep(id="step-3", target="c", action="C", depends_on=["step-1", "step-2"], order=2),
        ]

        ordered = order_steps_by_dependencies(steps)

        # step-1 and step-2 can be in any order, but step-3 must be last
        ids = [s.id for s in ordered]
        assert ids.index("step-3") > ids.index("step-1")
        assert ids.index("step-3") > ids.index("step-2")

    def test_order_steps_updates_order_field(self):
        """Should update order field after sorting."""
        steps = [
            PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"], order=99),
            PlanStep(id="step-1", target="a", action="A", order=99),
        ]

        ordered = order_steps_by_dependencies(steps)

        # Order fields should be sequential
        assert ordered[0].order == 0
        assert ordered[1].order == 1


class TestPlanStorage:
    """Tests for plan storage utilities."""

    def test_get_plans_dir(self, tmp_path):
        """Should return correct plans directory path."""
        plans_dir = get_plans_dir(str(tmp_path))
        assert plans_dir == str(tmp_path / ".eri-rpg" / "plans")

    def test_list_plans_empty(self, tmp_path):
        """Should return empty list when no plans exist."""
        plans = list_plans(str(tmp_path))
        assert plans == []

    def test_list_plans_finds_all(self, tmp_path):
        """Should find all plan files."""
        plans_dir = tmp_path / ".eri-rpg" / "plans"
        plans_dir.mkdir(parents=True)

        # Create some plan files
        (plans_dir / "plan-1.json").write_text(json.dumps({"id": "plan-1"}))
        (plans_dir / "plan-2.json").write_text(json.dumps({"id": "plan-2"}))

        plans = list_plans(str(tmp_path))
        assert len(plans) == 2

    def test_save_plan_to_project(self, tmp_path):
        """Should save plan to project's plans directory."""
        plan = Plan(
            id="my-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")]
        )
        path = save_plan_to_project(plan, str(tmp_path))

        assert os.path.exists(path)
        assert "my-plan.json" in path

        # Verify content
        with open(path) as f:
            data = json.load(f)
        assert data["id"] == "my-plan"


class TestPlanFilePersistence:
    """Tests for plan file save/load."""

    def test_plan_save_load(self, tmp_path):
        """Plan should persist to file correctly."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            spec_type="task",
            name="Test Plan",
            steps=[
                PlanStep(id="step-1", target="a", action="A"),
                PlanStep(id="step-2", target="b", action="B", depends_on=["step-1"]),
            ],
        )
        plan.update_stats()

        path = str(tmp_path / "plan.json")
        plan.save(path)

        loaded = Plan.load(path)
        assert loaded.id == "test-plan"
        assert loaded.spec_type == "task"
        assert len(loaded.steps) == 2
        assert loaded.steps[1].depends_on == ["step-1"]


class TestPlanCLI:
    """Tests for plan CLI commands."""

    def test_plan_generate_creates_file(self, tmp_path):
        """plan generate should create a plan file."""
        from click.testing import CliRunner
        from erirpg.cli import cli
        from erirpg.specs import TaskSpec

        # Create a spec first
        spec = TaskSpec(
            id="test-task",
            name="Test Task",
            task_type="extract",
            source_project="project",
            query="feature"
        )
        spec_path = str(tmp_path / "spec.json")
        spec.save(spec_path)

        output_path = str(tmp_path / "plan.json")

        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "generate", spec_path, "-o", output_path])

        assert result.exit_code == 0
        assert os.path.exists(output_path)
        assert "Generated plan" in result.output

    def test_plan_show_displays_content(self, tmp_path):
        """plan show should display plan content."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="show-test",
            spec_id="spec-1",
            name="Show Test Plan",
            steps=[
                PlanStep(id="step-1", target="test", action="Test Action"),
            ],
        )
        plan.update_stats()
        path = str(tmp_path / "plan.json")
        plan.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "show", path])

        assert result.exit_code == 0
        assert "Show Test Plan" in result.output
        assert "Test Action" in result.output

    def test_plan_show_json_output(self, tmp_path):
        """plan show --json should output valid JSON."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="json-test",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )
        path = str(tmp_path / "plan.json")
        plan.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "show", path, "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "json-test"

    def test_plan_list_shows_plans(self, tmp_path):
        """plan list should show all plans."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        # Create plans directory and a plan
        plans_dir = tmp_path / ".eri-rpg" / "plans"
        plans_dir.mkdir(parents=True)

        plan = Plan(
            id="list-test",
            spec_id="spec-1",
            name="List Test Plan",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )
        plan.update_stats()
        plan.save(str(plans_dir / "list-test.json"))

        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "list", "-p", str(tmp_path)])

        assert result.exit_code == 0
        assert "List Test Plan" in result.output

    def test_plan_next_shows_next_step(self, tmp_path):
        """plan next should show next executable step."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="next-test",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", target="a", action="First Action", order=0),
                PlanStep(id="step-2", target="b", action="Second Action", order=1, depends_on=["step-1"]),
            ],
        )
        path = str(tmp_path / "plan.json")
        plan.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "next", path])

        assert result.exit_code == 0
        assert "First Action" in result.output

    def test_plan_step_updates_status(self, tmp_path):
        """plan step should update step status."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="step-test",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="Test Action")],
        )
        path = str(tmp_path / "plan.json")
        plan.save(path)

        runner = CliRunner()

        # Mark step as complete
        result = runner.invoke(cli, ["plan", "step", path, "step-1", "complete"])
        assert result.exit_code == 0
        assert "Completed" in result.output

        # Verify it was saved
        loaded = Plan.load(path)
        assert loaded.steps[0].status == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
