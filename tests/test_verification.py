"""
Tests for EriRPG verification system.

Phase 6: Verification
- P6-001: Verification config
- P6-002: Verification runner
- P6-003: Verification integration
- P6-004: Verification CLI
- P6-005: Verification tests
"""

import json
import os
import pytest
from datetime import datetime
from click.testing import CliRunner

from erirpg.verification import (
    VerificationStatus,
    VerificationCommand,
    CommandResult,
    VerificationResult,
    VerificationConfig,
    Verifier,
    save_verification_result,
    load_verification_result,
    list_verification_results,
    format_verification_summary,
    load_verification_config,
    save_verification_config,
    get_default_python_config,
    get_default_node_config,
)
from erirpg.cli import cli


class TestVerificationCommand:
    """Tests for VerificationCommand model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        cmd = VerificationCommand(name="test", command="pytest")
        assert cmd.name == "test"
        assert cmd.command == "pytest"
        assert cmd.working_dir == ""
        assert cmd.timeout == 300
        assert cmd.required is True
        assert cmd.run_on == []

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        cmd = VerificationCommand(
            name="lint",
            command="ruff check .",
            working_dir="src",
            timeout=60,
            required=False,
            run_on=["create", "modify"],
        )

        data = cmd.to_dict()
        restored = VerificationCommand.from_dict(data)

        assert restored.name == cmd.name
        assert restored.command == cmd.command
        assert restored.working_dir == cmd.working_dir
        assert restored.timeout == cmd.timeout
        assert restored.required == cmd.required
        assert restored.run_on == cmd.run_on


class TestCommandResult:
    """Tests for CommandResult model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        result = CommandResult(name="test", command="pytest")
        assert result.name == "test"
        assert result.command == "pytest"
        assert result.status == "pending"
        assert result.exit_code == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_passed_property(self):
        """Should correctly identify passed commands."""
        result = CommandResult(name="test", command="pytest")
        result.status = VerificationStatus.PASSED.value
        assert result.passed is True

        result.status = VerificationStatus.FAILED.value
        assert result.passed is False

    def test_duration_calculation(self):
        """Should calculate duration correctly."""
        result = CommandResult(name="test", command="pytest")
        result.started_at = datetime(2024, 1, 1, 12, 0, 0)
        result.completed_at = datetime(2024, 1, 1, 12, 0, 5)

        assert result.duration == 5.0

    def test_duration_none_when_incomplete(self):
        """Should return None for duration when not completed."""
        result = CommandResult(name="test", command="pytest")
        result.started_at = datetime.now()
        assert result.duration is None

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        result = CommandResult(
            name="test",
            command="pytest",
            status="passed",
            exit_code=0,
            stdout="All tests passed",
            stderr="",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 0, 5),
            error_message="",
        )

        data = result.to_dict()
        restored = CommandResult.from_dict(data)

        assert restored.name == result.name
        assert restored.status == result.status
        assert restored.exit_code == result.exit_code


class TestVerificationResult:
    """Tests for VerificationResult model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        result = VerificationResult(step_id="step-1")
        assert result.step_id == "step-1"
        assert result.status == "pending"
        assert result.command_results == []

    def test_passed_property(self):
        """Should correctly identify passed verifications."""
        result = VerificationResult(step_id="step-1")
        result.status = VerificationStatus.PASSED.value
        assert result.passed is True

        result.status = VerificationStatus.FAILED.value
        assert result.passed is False

    def test_failed_commands_property(self):
        """Should correctly list failed commands."""
        result = VerificationResult(step_id="step-1")
        result.command_results = [
            CommandResult(name="lint", command="ruff", status="passed"),
            CommandResult(name="test", command="pytest", status="failed"),
            CommandResult(name="type", command="mypy", status="failed"),
        ]

        failed = result.failed_commands
        assert len(failed) == 2
        assert failed[0].name == "test"
        assert failed[1].name == "type"

    def test_format_report(self):
        """Should format a readable report."""
        result = VerificationResult(
            step_id="step-1",
            status="passed",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 0, 5),
        )
        result.command_results = [
            CommandResult(
                name="test",
                command="pytest",
                status="passed",
                exit_code=0,
                stdout="All tests passed",
            ),
        ]

        report = result.format_report()
        assert "Verification Report: step-1" in report
        assert "Status: passed" in report
        assert "test" in report
        assert "Exit code: 0" in report

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        result = VerificationResult(
            step_id="step-1",
            status="passed",
            command_results=[
                CommandResult(name="test", command="pytest", status="passed"),
            ],
        )

        data = result.to_dict()
        restored = VerificationResult.from_dict(data)

        assert restored.step_id == result.step_id
        assert restored.status == result.status
        assert len(restored.command_results) == 1


class TestVerificationConfig:
    """Tests for VerificationConfig model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        config = VerificationConfig()
        assert config.commands == []
        assert config.run_after_each_step is False
        assert config.run_at_checkpoints is True
        assert config.stop_on_failure is True

    def test_validate_empty_name(self):
        """Should catch empty command names."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="", command="pytest"),
            ]
        )
        errors = config.validate()
        assert any("name is required" in e for e in errors)

    def test_validate_empty_command(self):
        """Should catch empty commands."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="test", command=""),
            ]
        )
        errors = config.validate()
        assert any("command is required" in e for e in errors)

    def test_validate_invalid_timeout(self):
        """Should catch invalid timeouts."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="test", command="pytest", timeout=0),
            ]
        )
        errors = config.validate()
        assert any("timeout must be positive" in e for e in errors)

    def test_get_commands_for_step_all(self):
        """Should return all commands when run_on is empty."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="lint", command="ruff"),
                VerificationCommand(name="test", command="pytest"),
            ]
        )
        commands = config.get_commands_for_step("create")
        assert len(commands) == 2

    def test_get_commands_for_step_filtered(self):
        """Should filter commands by step type."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="lint", command="ruff", run_on=["create", "modify"]),
                VerificationCommand(name="test", command="pytest", run_on=["test"]),
            ]
        )
        commands = config.get_commands_for_step("create")
        assert len(commands) == 1
        assert commands[0].name == "lint"

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="test", command="pytest"),
            ],
            run_after_each_step=True,
            stop_on_failure=False,
        )

        data = config.to_dict()
        restored = VerificationConfig.from_dict(data)

        assert len(restored.commands) == 1
        assert restored.run_after_each_step is True
        assert restored.stop_on_failure is False


class TestVerifier:
    """Tests for Verifier class."""

    def test_run_command_success(self, tmp_path):
        """Should run successful commands."""
        config = VerificationConfig()
        verifier = Verifier(config, str(tmp_path))

        cmd = VerificationCommand(name="echo", command="echo hello")
        result = verifier.run_command(cmd)

        assert result.status == VerificationStatus.PASSED.value
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_run_command_failure(self, tmp_path):
        """Should capture failed commands."""
        config = VerificationConfig()
        verifier = Verifier(config, str(tmp_path))

        # Use false command which returns exit code 1 (or shell mode for exit)
        cmd = VerificationCommand(name="false", command="exit 1", allow_shell=True)
        result = verifier.run_command(cmd)

        assert result.status == VerificationStatus.FAILED.value
        assert result.exit_code == 1

    def test_run_command_timeout(self, tmp_path):
        """Should handle command timeouts."""
        config = VerificationConfig()
        verifier = Verifier(config, str(tmp_path))

        cmd = VerificationCommand(name="sleep", command="sleep 10", timeout=1)
        result = verifier.run_command(cmd)

        assert result.status == VerificationStatus.ERROR.value
        assert "timed out" in result.error_message

    def test_run_command_working_dir(self, tmp_path):
        """Should use specified working directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "marker.txt").write_text("found")

        config = VerificationConfig()
        verifier = Verifier(config, str(tmp_path))

        cmd = VerificationCommand(
            name="cat",
            command="cat marker.txt",
            working_dir="subdir",
        )
        result = verifier.run_command(cmd)

        assert result.status == VerificationStatus.PASSED.value
        assert "found" in result.stdout

    def test_run_verification_all_pass(self, tmp_path):
        """Should pass when all commands pass."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="echo1", command="echo one"),
                VerificationCommand(name="echo2", command="echo two"),
            ]
        )
        verifier = Verifier(config, str(tmp_path))

        result = verifier.run_verification("step-1")

        assert result.passed is True
        assert result.status == VerificationStatus.PASSED.value
        assert len(result.command_results) == 2

    def test_run_verification_required_fail(self, tmp_path):
        """Should fail when required command fails."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="pass", command="echo ok"),
                VerificationCommand(name="fail", command="exit 1", required=True),
            ],
            stop_on_failure=True,
        )
        verifier = Verifier(config, str(tmp_path))

        result = verifier.run_verification("step-1")

        assert result.passed is False
        assert result.status == VerificationStatus.FAILED.value

    def test_run_verification_optional_fail(self, tmp_path):
        """Should pass when only optional commands fail."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="pass", command="echo ok", required=True),
                VerificationCommand(name="warn", command="exit 1", required=False),
            ],
            stop_on_failure=False,
        )
        verifier = Verifier(config, str(tmp_path))

        result = verifier.run_verification("step-1")

        # Pass because required passed (optional failure doesn't block)
        assert result.passed is True

    def test_run_verification_stop_on_failure(self, tmp_path):
        """Should stop on first failure when configured."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="fail", command="exit 1"),
                VerificationCommand(name="never", command="echo never"),
            ],
            stop_on_failure=True,
        )
        verifier = Verifier(config, str(tmp_path))

        result = verifier.run_verification("step-1")

        # Should have stopped after first failure
        assert len(result.command_results) == 1

    def test_run_verification_no_commands(self, tmp_path):
        """Should skip when no commands configured."""
        config = VerificationConfig(commands=[])
        verifier = Verifier(config, str(tmp_path))

        result = verifier.run_verification("step-1")

        assert result.status == VerificationStatus.SKIPPED.value

    def test_should_run_for_step(self, tmp_path):
        """Should determine when to run based on config."""
        config = VerificationConfig(
            run_after_each_step=False,
            run_at_checkpoints=True,
        )
        verifier = Verifier(config, str(tmp_path))

        assert verifier.should_run_for_step(is_checkpoint=False) is False
        assert verifier.should_run_for_step(is_checkpoint=True) is True

        config.run_after_each_step = True
        assert verifier.should_run_for_step(is_checkpoint=False) is True


class TestVerificationStorage:
    """Tests for verification result storage."""

    def test_save_and_load_result(self, tmp_path):
        """Should save and load verification results."""
        from erirpg.planner import Plan
        from erirpg.runs import create_run, save_run

        # Create a run
        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])
        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        # Create verification result
        result = VerificationResult(
            step_id="step-1",
            status="passed",
            command_results=[
                CommandResult(name="test", command="pytest", status="passed"),
            ],
        )

        # Save and load
        save_verification_result(str(tmp_path), run.id, result)
        loaded = load_verification_result(str(tmp_path), run.id, "step-1")

        assert loaded is not None
        assert loaded.step_id == result.step_id
        assert loaded.status == result.status
        assert len(loaded.command_results) == 1

    def test_list_verification_results(self, tmp_path):
        """Should list all verification results for a run."""
        from erirpg.planner import Plan
        from erirpg.runs import create_run, save_run

        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])
        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        # Save multiple results
        for i in range(3):
            result = VerificationResult(step_id=f"step-{i}", status="passed")
            save_verification_result(str(tmp_path), run.id, result)

        results = list_verification_results(str(tmp_path), run.id)
        assert len(results) == 3

    def test_format_verification_summary(self):
        """Should format a summary of results."""
        results = [
            VerificationResult(step_id="step-1", status="passed"),
            VerificationResult(step_id="step-2", status="failed"),
            VerificationResult(step_id="step-3", status="skipped"),
        ]

        summary = format_verification_summary(results)
        assert "Total: 3" in summary
        assert "Passed: 1" in summary
        assert "Failed: 1" in summary
        assert "Skipped: 1" in summary


class TestVerificationConfigStorage:
    """Tests for verification config storage."""

    def test_save_and_load_config(self, tmp_path):
        """Should save and load verification config."""
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="test", command="pytest"),
            ],
            run_after_each_step=True,
        )

        save_verification_config(str(tmp_path), config)
        loaded = load_verification_config(str(tmp_path))

        assert loaded is not None
        assert len(loaded.commands) == 1
        assert loaded.run_after_each_step is True

    def test_load_config_not_found(self, tmp_path):
        """Should return None when config not found."""
        loaded = load_verification_config(str(tmp_path))
        assert loaded is None


class TestDefaultConfigs:
    """Tests for default verification configs."""

    def test_python_config(self):
        """Should have sensible Python defaults."""
        config = get_default_python_config()

        assert len(config.commands) > 0
        names = [c.name for c in config.commands]
        assert "lint" in names or "test" in names

    def test_node_config(self):
        """Should have sensible Node.js defaults."""
        config = get_default_node_config()

        assert len(config.commands) > 0
        # Should use npm commands
        assert any("npm" in c.command for c in config.commands)


class TestRunnerVerificationIntegration:
    """Tests for verification integration with Runner."""

    def test_runner_verify_step(self, tmp_path):
        """Should run verification through runner."""
        from erirpg.planner import Plan, PlanStep
        from erirpg.runner import Runner

        # Create verification config
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="echo", command="echo verified"),
            ],
            run_after_each_step=True,
        )

        # Create plan and runner
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", action="Test step"),
            ],
        )
        runner = Runner(plan, str(tmp_path), verification_config=config)
        runner.start()

        step = plan.steps[0]
        result = runner.verify_step(step)

        assert result is not None
        assert result.passed is True

    def test_runner_no_verification_config(self, tmp_path):
        """Should return None when no verification configured."""
        from erirpg.planner import Plan, PlanStep
        from erirpg.runner import Runner

        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", action="Test step"),
            ],
        )
        runner = Runner(plan, str(tmp_path))
        runner.start()

        step = plan.steps[0]
        result = runner.verify_step(step)

        assert result is None


class TestVerificationCLI:
    """Tests for verification CLI commands."""

    def test_verify_config_init(self, tmp_path):
        """Should initialize verification config."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", "config",
            "--init",
            "-p", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Created verification config" in result.output

        # Verify file exists
        config_path = tmp_path / ".eri-rpg" / "verification.json"
        assert config_path.exists()

    def test_verify_config_show(self, tmp_path):
        """Should show verification config."""
        # Create config first
        config = get_default_python_config()
        save_verification_config(str(tmp_path), config)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", "config",
            "-p", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Verification Config" in result.output

    def test_verify_config_not_found(self, tmp_path):
        """Should handle missing config gracefully."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", "config",
            "-p", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "No verification config found" in result.output

    def test_verify_results_no_results(self, tmp_path):
        """Should handle missing results gracefully."""
        from erirpg.planner import Plan
        from erirpg.runs import create_run, save_run

        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])
        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", "results", run.id,
            "-p", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "No verification results found" in result.output

    def test_verify_run_no_config(self, tmp_path):
        """Should error when no config for verify run."""
        from erirpg.planner import Plan
        from erirpg.runs import create_run, save_run

        plan = Plan(id="test-plan", spec_id="spec-1", steps=[])
        run = create_run(plan, str(tmp_path))
        save_run(str(tmp_path), run)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "verify", "run", run.id,
            "-p", str(tmp_path),
        ])

        assert result.exit_code == 1
        assert "No verification config found" in result.output


class TestIntegration:
    """Integration tests for the full verification workflow."""

    def test_full_verification_workflow(self, tmp_path):
        """Should complete a full verification workflow."""
        from erirpg.planner import Plan, PlanStep
        from erirpg.runs import create_run, save_run, StepResult
        from erirpg.runner import Runner

        # 1. Create verification config
        config = VerificationConfig(
            commands=[
                VerificationCommand(name="check", command="echo 'all good'"),
            ],
        )
        save_verification_config(str(tmp_path), config)

        # 2. Create plan and run
        plan = Plan(
            id="test-plan",
            spec_id="spec-1",
            steps=[
                PlanStep(id="step-1", action="Step one"),
                PlanStep(id="step-2", action="Step two"),
            ],
        )

        runner = Runner(plan, str(tmp_path), verification_config=config)
        run = runner.start()

        # 3. Complete steps
        for step in plan.steps:
            runner.mark_step_started(step)
            runner.mark_step_completed(step)

        # 4. Run verification
        verifier = Verifier(config, str(tmp_path))
        for step in plan.steps:
            result = verifier.run_verification(step.id)
            save_verification_result(str(tmp_path), run.id, result)

        # 5. Check results
        results = list_verification_results(str(tmp_path), run.id)
        assert len(results) == 2
        assert all(r.passed for r in results)

        # 6. Summary should show all passed
        summary = format_verification_summary(results)
        assert "Passed: 2" in summary
        assert "Failed: 0" in summary
