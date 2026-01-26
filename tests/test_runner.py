"""
Test Phase 5: Runner and Checkpoints.

Tests for run records, runner orchestration, step context, and CLI commands.
"""

import json
import os
import pytest
from datetime import datetime

from erirpg.runs import (
    RunRecord,
    RunStatus,
    StepResult,
    create_run,
    save_run,
    load_run,
    delete_run,
    list_run_ids,
    get_latest_run,
    save_artifact,
    get_artifacts,
    get_runs_dir,
    get_run_dir,
)
from erirpg.runner import (
    Runner,
    StepContext,
    build_step_context,
    save_step_context,
    list_runs,
)
from erirpg.planner import Plan, PlanStep


class TestStepResult:
    """Tests for StepResult model."""

    def test_step_result_defaults(self):
        """Step result should have sensible defaults."""
        result = StepResult(step_id="step-1")
        assert result.status == "pending"
        assert result.error == ""
        assert result.artifacts == []

    def test_step_result_serialization_roundtrip(self):
        """Step result should survive serialization roundtrip."""
        result = StepResult(
            step_id="step-1",
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            output="Success",
            artifacts=["file.txt"],
        )
        data = result.to_dict()
        restored = StepResult.from_dict(data)

        assert restored.step_id == result.step_id
        assert restored.status == result.status
        assert restored.output == result.output
        assert restored.artifacts == result.artifacts

    def test_step_result_duration(self):
        """Should calculate duration correctly."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 30)

        result = StepResult(
            step_id="step-1",
            started_at=start,
            completed_at=end,
        )

        assert result.duration == 30.0


class TestRunRecord:
    """Tests for RunRecord model."""

    def test_run_record_defaults(self):
        """Run record should have sensible defaults."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path/plan.json")
        assert run.status == "pending"
        assert run.step_results == []
        assert run.current_step == ""

    def test_run_record_validate(self):
        """Validation should check required fields."""
        run = RunRecord(id="", plan_id="", plan_path="")
        errors = run.validate()
        assert "id is required" in errors
        assert "plan_id is required" in errors
        assert "plan_path is required" in errors

    def test_run_record_validate_status(self):
        """Validation should check status values."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path", status="invalid")
        errors = run.validate()
        assert any("status" in e for e in errors)

    def test_run_record_add_step_result(self):
        """Should add step results correctly."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path")

        run.add_step_result(StepResult(step_id="step-1", status="completed"))
        assert len(run.step_results) == 1
        assert run.step_results[0].step_id == "step-1"

    def test_run_record_update_step_result(self):
        """Should update existing step result."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path")

        run.add_step_result(StepResult(step_id="step-1", status="pending"))
        run.add_step_result(StepResult(step_id="step-1", status="completed"))

        assert len(run.step_results) == 1
        assert run.step_results[0].status == "completed"

    def test_run_record_get_step_result(self):
        """Should retrieve step result by ID."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path")
        run.add_step_result(StepResult(step_id="step-1", status="completed"))
        run.add_step_result(StepResult(step_id="step-2", status="pending"))

        result = run.get_step_result("step-2")
        assert result is not None
        assert result.status == "pending"

    def test_run_record_completed_steps(self):
        """Should count completed steps."""
        run = RunRecord(id="run-1", plan_id="plan-1", plan_path="/path")
        run.add_step_result(StepResult(step_id="step-1", status="completed"))
        run.add_step_result(StepResult(step_id="step-2", status="completed"))
        run.add_step_result(StepResult(step_id="step-3", status="pending"))

        assert run.completed_steps == 2

    def test_run_record_serialization_roundtrip(self):
        """Run record should survive serialization roundtrip."""
        run = RunRecord(
            id="run-1",
            plan_id="plan-1",
            plan_path="/path/plan.json",
            spec_id="spec-1",
            status="in_progress",
            current_step="step-2",
        )
        run.add_step_result(StepResult(step_id="step-1", status="completed"))

        data = run.to_dict()
        restored = RunRecord.from_dict(data)

        assert restored.id == run.id
        assert restored.plan_id == run.plan_id
        assert restored.status == run.status
        assert len(restored.step_results) == 1

    def test_run_record_format_summary(self):
        """Should format a readable summary."""
        run = RunRecord(
            id="run-test",
            plan_id="plan-1",
            plan_path="/path",
            status="in_progress",
        )
        run.add_step_result(StepResult(step_id="step-1", status="completed"))

        summary = run.format_summary()
        assert "run-test" in summary
        assert "in_progress" in summary


class TestRunStorage:
    """Tests for run storage utilities."""

    def test_get_runs_dir(self, tmp_path):
        """Should return correct runs directory."""
        runs_dir = get_runs_dir(str(tmp_path))
        assert runs_dir == str(tmp_path / ".eri-rpg" / "runs")

    def test_create_run(self, tmp_path):
        """Should create a run with directory structure."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )

        run = create_run(plan, str(tmp_path))

        assert run.id.startswith("run-test-plan")
        assert run.plan_id == "test-plan"

        # Check directories were created
        run_dir = get_run_dir(str(tmp_path), run.id)
        assert os.path.exists(os.path.join(run_dir, "contexts"))
        assert os.path.exists(os.path.join(run_dir, "artifacts"))
        assert os.path.exists(os.path.join(run_dir, "logs"))

    def test_save_and_load_run(self, tmp_path):
        """Should save and load run correctly."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )

        run = create_run(plan, str(tmp_path))
        run.status = RunStatus.IN_PROGRESS.value
        run.add_step_result(StepResult(step_id="step-1", status="completed"))

        save_run(str(tmp_path), run)

        loaded = load_run(str(tmp_path), run.id)
        assert loaded is not None
        assert loaded.id == run.id
        assert loaded.status == "in_progress"
        assert len(loaded.step_results) == 1

    def test_delete_run(self, tmp_path):
        """Should delete run and all artifacts."""
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])

        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        assert delete_run(str(tmp_path), run.id)
        assert load_run(str(tmp_path), run.id) is None

    def test_list_run_ids(self, tmp_path):
        """Should list all run IDs."""
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])

        run1 = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run1)

        run2 = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run2)

        run_ids = list_run_ids(str(tmp_path))
        assert len(run_ids) == 2

    def test_get_latest_run(self, tmp_path):
        """Should get most recent run."""
        import time
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])

        run1 = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run1)

        # Small delay to ensure mtime differs
        time.sleep(0.01)

        run2 = create_run(plan, str(tmp_path))
        run2.status = "in_progress"
        save_run(str(tmp_path), run2)

        latest = get_latest_run(str(tmp_path))
        assert latest is not None
        # Latest should be run2 (created second)
        assert latest.id == run2.id

    def test_save_and_get_artifacts(self, tmp_path):
        """Should save and retrieve artifacts."""
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])
        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        path = save_artifact(str(tmp_path), run.id, "step-1", "output.txt", "Hello!")

        assert os.path.exists(path)

        artifacts = get_artifacts(str(tmp_path), run.id, "step-1")
        assert len(artifacts) == 1
        assert artifacts[0].endswith("output.txt")


class TestStepContext:
    """Tests for StepContext."""

    def test_step_context_defaults(self):
        """Step context should have sensible defaults."""
        ctx = StepContext(
            step_id="step-1",
            step_type="read",
            target="module.py",
            action="Read module",
            details="Read and understand",
        )
        assert ctx.input_files == []
        assert ctx.learnings == []
        assert ctx.constraints == []

    def test_step_context_serialization_roundtrip(self):
        """Step context should survive serialization roundtrip."""
        ctx = StepContext(
            step_id="step-1",
            step_type="create",
            target="new.py",
            action="Create file",
            details="Create a new file",
            input_files=["old.py"],
            output_files=["new.py"],
            constraints=["No overwrites"],
        )

        data = ctx.to_dict()
        restored = StepContext.from_dict(data)

        assert restored.step_id == ctx.step_id
        assert restored.input_files == ctx.input_files
        assert restored.constraints == ctx.constraints

    def test_step_context_format_for_claude(self):
        """Should format readable markdown for Claude."""
        ctx = StepContext(
            step_id="step-1",
            step_type="modify",
            target="module.py",
            action="Update module",
            details="Add new function",
            input_files=["helper.py"],
            output_files=["module.py"],
            constraints=["Keep existing code"],
            verify_command="python -c 'import module'",
        )

        md = ctx.format_for_claude()

        assert "# Step: Update module" in md
        assert "**Type:** modify" in md
        assert "helper.py" in md
        assert "Keep existing code" in md
        assert "python -c 'import module'" in md

    def test_build_step_context(self, tmp_path):
        """Should build context from step and plan."""
        step = PlanStep(
            id="step-1",
            step_type="create",
            target="new.py",
            action="Create new file",
            details="Create a new Python file",
            inputs=["old.py"],
            outputs=["new.py"],
            risk="high",
            risk_reason="Many dependents",
        )
        plan = Plan(id="plan-1", spec_id="spec-1", steps=[step])

        ctx = build_step_context(step, plan, str(tmp_path))

        assert ctx.step_id == "step-1"
        assert ctx.input_files == ["old.py"]
        assert ctx.output_files == ["new.py"]
        assert any("HIGH RISK" in c for c in ctx.constraints)

    def test_save_step_context(self, tmp_path):
        """Should save context files to run directory."""
        ctx = StepContext(
            step_id="step-1",
            step_type="read",
            target="test.py",
            action="Read file",
            details="Details here",
        )

        run_dir = str(tmp_path / "run-test")
        os.makedirs(run_dir)

        path = save_step_context(ctx, run_dir)

        assert os.path.exists(path)
        assert path.endswith(".md")

        # Also check JSON was created
        json_path = path.replace(".md", ".json")
        assert os.path.exists(json_path)


class TestRunner:
    """Tests for Runner orchestration."""

    def test_runner_start(self, tmp_path):
        """Should start a new run."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )

        runner = Runner(plan, str(tmp_path))
        run = runner.start()

        assert run.id is not None
        assert run.status == "pending"

    def test_runner_get_next_step(self, tmp_path):
        """Should get next executable step."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", target="a", action="A", order=0),
                PlanStep(id="step-2", target="b", action="B", order=1, depends_on=["step-1"]),
            ],
        )

        runner = Runner(plan, str(tmp_path))
        runner.start()

        next_step = runner.get_next_step()
        assert next_step.id == "step-1"

    def test_runner_mark_step_lifecycle(self, tmp_path):
        """Should track step through lifecycle."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )

        runner = Runner(plan, str(tmp_path))
        runner.start()

        step = runner.get_next_step()

        # Start
        runner.mark_step_started(step)
        assert runner.run.current_step == "step-1"
        assert step.status == "in_progress"

        # Complete
        runner.mark_step_completed(step, output="Done!")
        assert step.status == "completed"

        result = runner.run.get_step_result("step-1")
        assert result.output == "Done!"

    def test_runner_mark_step_failed(self, tmp_path):
        """Should handle step failure."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )

        runner = Runner(plan, str(tmp_path))
        runner.start()

        step = runner.get_next_step()
        runner.mark_step_failed(step, "Something went wrong")

        assert step.status == "failed"
        assert runner.run.status == "failed"

    def test_runner_progress(self, tmp_path):
        """Should track progress correctly."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", target="a", action="A"),
                PlanStep(id="step-2", target="b", action="B"),
            ],
        )

        runner = Runner(plan, str(tmp_path))
        runner.start()

        progress = runner.get_progress()
        assert progress['total_steps'] == 2
        assert progress['completed_steps'] == 0

        step = runner.get_next_step()
        runner.mark_step_completed(step)

        progress = runner.get_progress()
        assert progress['completed_steps'] == 1
        assert progress['progress_pct'] == 50.0

    def test_runner_resume(self, tmp_path):
        """Should resume a paused run."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", target="a", action="A"),
                PlanStep(id="step-2", target="b", action="B"),
            ],
        )

        # Start and complete first step
        runner = Runner(plan, str(tmp_path))
        run = runner.start()
        step = runner.get_next_step()
        runner.mark_step_completed(step)
        runner.pause()

        # Resume
        runner2 = Runner.resume(run.id, str(tmp_path))

        progress = runner2.get_progress()
        assert progress['completed_steps'] == 1

        next_step = runner2.get_next_step()
        assert next_step.id == "step-2"

    def test_runner_get_report(self, tmp_path):
        """Should generate readable report."""
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            name="Test Plan",
            steps=[PlanStep(id="step-1", target="a", action="Do A")],
        )

        runner = Runner(plan, str(tmp_path))
        runner.start()
        step = runner.get_next_step()
        runner.mark_step_completed(step)

        report = runner.get_report()

        assert "Test Plan" in report
        assert "Do A" in report
        assert "●" in report  # completed icon

    def test_list_runs(self, tmp_path):
        """Should list all runs."""
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])

        runner1 = Runner(plan, str(tmp_path))
        runner1.start()

        runner2 = Runner(plan, str(tmp_path))
        runner2.start()

        runs = list_runs(str(tmp_path))
        assert len(runs) == 2


class TestRunnerCLI:
    """Tests for run CLI commands."""

    def test_run_start_creates_run(self, tmp_path):
        """run start should create a run."""
        from click.testing import CliRunner
        from erirpg.cli import cli
        from erirpg.planner import Plan, PlanStep

        # Create a plan first
        plan = Plan(
            id="cli-plan",
            spec_id="spec-1",
            name="CLI Test Plan",
            steps=[PlanStep(id="step-1", target="a", action="First step")],
        )
        plan_path = str(tmp_path / "plan.json")
        plan.save(plan_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "start", plan_path, "-p", str(tmp_path)])

        assert result.exit_code == 0
        assert "Started run" in result.output
        assert "First step" in result.output

    def test_run_list_shows_runs(self, tmp_path):
        """run list should show all runs."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        # Create a run
        plan = Plan(
            id="list-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )
        runner_obj = Runner(plan, str(tmp_path))
        runner_obj.start()

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "list", "-p", str(tmp_path)])

        assert result.exit_code == 0
        assert "list-plan" in result.output

    def test_run_show_displays_run(self, tmp_path):
        """run show should display run details."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="show-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="A")],
        )
        runner_obj = Runner(plan, str(tmp_path))
        run = runner_obj.start()

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "show", run.id, "-p", str(tmp_path)])

        assert result.exit_code == 0
        assert run.id in result.output

    def test_run_step_updates_status(self, tmp_path):
        """run step should update step status."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        plan = Plan(
            id="step-plan",
            spec_id="spec-1",
            steps=[PlanStep(id="step-1", target="a", action="Test action")],
        )
        runner_obj = Runner(plan, str(tmp_path))
        run = runner_obj.start()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", "step", run.id, "step-1", "complete", "-p", str(tmp_path)
        ])

        assert result.exit_code == 0
        assert "Completed" in result.output

        # Verify it was saved
        loaded = load_run(str(tmp_path), run.id)
        step_result = loaded.get_step_result("step-1")
        assert step_result.status == "completed"


class TestIntegration:
    """Integration tests for full run workflow."""

    def test_full_run_workflow(self, tmp_path):
        """Test complete workflow: create -> start -> execute -> complete."""
        from erirpg.specs import TaskSpec
        from erirpg.planner import generate_plan

        # Create spec
        spec = TaskSpec(
            id="integ-task",
            name="Integration Test",
            task_type="extract",
            source_project="project",
            query="feature",
        )

        # Generate plan
        plan = generate_plan(spec)
        assert len(plan.steps) > 0

        # Start run
        runner = Runner(plan, str(tmp_path))
        run = runner.start()
        assert run.status == "pending"

        # Execute all steps
        while True:
            step = runner.get_next_step()
            if not step:
                break

            # Prepare context
            ctx = runner.prepare_step(step)
            assert ctx.step_id == step.id
            assert os.path.exists(ctx.context_file)

            # Mark complete
            runner.mark_step_started(step)
            runner.mark_step_completed(step, output=f"Completed {step.action}")

        # Verify completion
        progress = runner.get_progress()
        assert progress['status'] == 'completed'
        assert progress['completed_steps'] == progress['total_steps']

        # Generate report
        report = runner.get_report()
        assert "completed" in report.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
