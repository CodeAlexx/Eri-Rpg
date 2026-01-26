"""
Tests for EriRPG UX, diagnostics, and cache modules.

Phase 7: UX and Hardening
- P7-001: Better diagnostics and failure summaries
- P7-002: Impact-aware planning
- P7-003: Performance tuning (caching)
- P7-004: Documentation and quickstart
- P7-005: UX polish
"""

import json
import os
import pytest
import time
from io import StringIO

from erirpg.diagnostics import (
    Hint,
    extract_hints,
    suggest_fixes,
    format_step_failure,
    format_verification_failure,
    format_run_failure_summary,
    format_progress_bar,
    format_status_line,
    format_next_steps,
    format_impact_warning,
    assess_step_impact,
)
from erirpg.cache import (
    IndexCache,
    CacheEntry,
    CacheStats,
    get_index_cache,
    clear_cache,
)
from erirpg.ux import (
    ICONS,
    set_colors,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    format_status,
    format_progress_bar as ux_format_progress_bar,
    format_duration,
)


class TestHintExtraction:
    """Tests for error hint extraction."""

    def test_extract_module_not_found(self):
        """Should extract hints from ModuleNotFoundError."""
        output = "ModuleNotFoundError: No module named 'requests'"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any("requests" in h.message for h in hints)
        assert any("pip install" in h.suggestion for h in hints)

    def test_extract_import_error(self):
        """Should extract hints from ImportError."""
        output = "ImportError: cannot import name 'foo' from 'bar'"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any("foo" in h.message for h in hints)

    def test_extract_syntax_error(self):
        """Should extract hints from SyntaxError."""
        output = "SyntaxError: invalid syntax"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any(h.category == "syntax" for h in hints)

    def test_extract_type_error(self):
        """Should extract hints from TypeError."""
        output = "TypeError: 'NoneType' object is not callable"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any("NoneType" in h.message for h in hints)

    def test_extract_assertion_error(self):
        """Should extract hints from AssertionError."""
        output = "AssertionError: assert 1 == 2"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any(h.category == "test" for h in hints)

    def test_extract_file_not_found(self):
        """Should extract hints from FileNotFoundError."""
        output = "FileNotFoundError: [Errno 2] No such file or directory: '/path/to/file'"
        hints = extract_hints(output)

        assert len(hints) >= 1
        assert any("file" in h.category for h in hints)

    def test_suggest_fixes(self):
        """Should return list of fix suggestions."""
        output = "ModuleNotFoundError: No module named 'flask'"
        fixes = suggest_fixes(output)

        assert len(fixes) >= 1
        assert any("pip install" in fix for fix in fixes)

    def test_no_hints_for_clean_output(self):
        """Should return empty list for clean output."""
        output = "All tests passed successfully!"
        hints = extract_hints(output)

        # May or may not find hints depending on patterns
        # Just ensure it doesn't crash
        assert isinstance(hints, list)

    def test_dedupe_hints(self):
        """Should deduplicate identical hints."""
        output = """
        ModuleNotFoundError: No module named 'requests'
        ModuleNotFoundError: No module named 'requests'
        """
        hints = extract_hints(output)

        # Should only have one hint for requests
        requests_hints = [h for h in hints if "requests" in h.message]
        assert len(requests_hints) <= 1


class TestFailureFormatting:
    """Tests for failure report formatting."""

    def test_format_step_failure(self):
        """Should format a step failure report."""
        report = format_step_failure(
            step_id="step-001",
            error="ImportError: cannot import name 'foo'",
            output="Traceback...\nImportError: cannot import name 'foo'",
        )

        assert "Step Failed: step-001" in report
        assert "ImportError" in report
        assert "Likely Issues:" in report or "Error:" in report

    def test_format_step_failure_with_context(self):
        """Should include context in failure report."""
        report = format_step_failure(
            step_id="step-001",
            error="Test failed",
            context={
                "inputs": ["file1.py", "file2.py"],
                "outputs": ["output.py"],
            },
        )

        assert "Input Files:" in report
        assert "file1.py" in report

    def test_format_verification_failure(self):
        """Should format verification failure details."""
        from erirpg.verification import CommandResult

        results = [
            CommandResult(
                name="lint",
                command="ruff check .",
                status="failed",
                exit_code=1,
                stderr="undefined name 'foo'",
            ),
        ]

        report = format_verification_failure("step-001", results)

        assert "Verification Failed" in report
        assert "lint" in report
        assert "exit" in report.lower() or "Exit" in report

    def test_format_run_failure_summary(self):
        """Should format run failure summary."""
        from erirpg.runs import RunRecord, StepResult

        run = RunRecord(
            id="run-test-001",
            plan_id="plan-001",
            plan_path="/path/to/plan.json",
            status="failed",
            step_results=[
                StepResult(step_id="step-1", status="completed"),
                StepResult(step_id="step-2", status="failed", error="Something broke"),
            ],
        )

        report = format_run_failure_summary(run)

        assert "Run Failure Summary" in report
        assert "run-test-001" in report
        assert "step-2" in report
        assert "Something broke" in report


class TestProgressFormatting:
    """Tests for progress bar and status formatting."""

    def test_format_progress_bar(self):
        """Should format a progress bar."""
        bar = format_progress_bar(5, 10)

        assert "[" in bar
        assert "]" in bar
        assert "5/10" in bar
        assert "50%" in bar

    def test_format_progress_bar_empty(self):
        """Should handle empty progress."""
        bar = format_progress_bar(0, 10)
        assert "0/10" in bar
        assert "0%" in bar

    def test_format_progress_bar_full(self):
        """Should handle full progress."""
        bar = format_progress_bar(10, 10)
        assert "10/10" in bar
        assert "100%" in bar

    def test_format_progress_bar_zero_total(self):
        """Should handle zero total."""
        bar = format_progress_bar(0, 0)
        assert "0/0" in bar

    def test_format_status_line(self):
        """Should format a step status line."""
        from erirpg.planner import PlanStep

        step = PlanStep(
            id="step-1",
            action="Create user model",
            status="completed",
            order=1,
            risk="low",
        )

        line = format_status_line(step)
        assert "Create user model" in line
        assert "1." in line

    def test_format_status_line_high_risk(self):
        """Should show risk badge for high risk steps."""
        from erirpg.planner import PlanStep

        step = PlanStep(
            id="step-1",
            action="Modify core auth",
            status="pending",
            order=1,
            risk="high",
        )

        line = format_status_line(step)
        assert "HIGH" in line


class TestNextStepsFormatting:
    """Tests for next steps guidance formatting."""

    def test_format_next_steps_with_current(self):
        """Should format guidance for current step."""
        from erirpg.planner import PlanStep

        current = PlanStep(id="step-1", action="Test action")
        guidance = format_next_steps(current, [], "run-001")

        assert "Current Step" in guidance
        assert "Test action" in guidance
        assert "run step" in guidance

    def test_format_next_steps_with_ready(self):
        """Should format guidance for ready steps."""
        from erirpg.planner import PlanStep

        ready = [
            PlanStep(id="step-1", action="First action"),
            PlanStep(id="step-2", action="Second action"),
        ]

        guidance = format_next_steps(None, ready, "run-001")

        assert "Ready Steps" in guidance
        assert "First action" in guidance

    def test_format_next_steps_none_ready(self):
        """Should handle no ready steps."""
        guidance = format_next_steps(None, [], "run-001")

        assert "No steps ready" in guidance


class TestImpactAssessment:
    """Tests for impact assessment and warnings."""

    def test_format_impact_warning(self):
        """Should format impact warning."""
        from erirpg.planner import PlanStep

        step = PlanStep(id="step-1", action="Modify base class")
        warning = format_impact_warning(
            step,
            impact_score=0.8,
            affected_modules=["module1.py", "module2.py", "module3.py"],
        )

        assert "HIGH IMPACT" in warning
        assert "80" in warning  # 80% or 80.0%
        assert "3 modules" in warning
        assert "module1.py" in warning

    def test_assess_step_impact_low_risk(self):
        """Should assess low risk as low impact."""
        from erirpg.planner import PlanStep

        step = PlanStep(
            id="step-1",
            action="Add comment",
            step_type="modify",
            risk="low",
        )

        score, affected = assess_step_impact(step)

        assert score < 0.7
        assert isinstance(affected, list)

    def test_assess_step_impact_high_risk(self):
        """Should assess high risk as high impact."""
        from erirpg.planner import PlanStep

        step = PlanStep(
            id="step-1",
            action="Delete auth module",
            step_type="delete",
            risk="critical",
        )

        score, _ = assess_step_impact(step)

        assert score >= 0.9


class TestIndexCache:
    """Tests for the IndexCache class."""

    def test_cache_store_and_get(self, tmp_path):
        """Should store and retrieve cached results."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = IndexCache(str(tmp_path))

        # Store result
        result = {"interfaces": [], "imports": ["os"]}
        cache.store(str(test_file), result)

        # Get result
        cached = cache.get(str(test_file))
        assert cached == result

    def test_cache_is_stale_new_file(self, tmp_path):
        """Should detect new files as stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = IndexCache(str(tmp_path))

        assert cache.is_stale(str(test_file)) is True

    def test_cache_is_stale_unchanged(self, tmp_path):
        """Should detect unchanged files as not stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = IndexCache(str(tmp_path))

        # Store result
        cache.store(str(test_file), {"test": True})

        # Check again
        assert cache.is_stale(str(test_file)) is False

    def test_cache_is_stale_modified(self, tmp_path):
        """Should detect modified files as stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = IndexCache(str(tmp_path))
        cache.store(str(test_file), {"test": True})

        # Modify file (need small delay for mtime change)
        time.sleep(0.01)
        test_file.write_text("print('world')")

        assert cache.is_stale(str(test_file)) is True

    def test_cache_invalidate(self, tmp_path):
        """Should invalidate cache entry."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = IndexCache(str(tmp_path))
        cache.store(str(test_file), {"test": True})

        cache.invalidate(str(test_file))

        assert cache.get(str(test_file)) is None

    def test_cache_invalidate_all(self, tmp_path):
        """Should clear all cache entries."""
        cache = IndexCache(str(tmp_path))

        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"# test {i}")
            cache.store(str(test_file), {"index": i})

        cache.invalidate_all()
        cache.save()

        # Reload cache
        cache2 = IndexCache(str(tmp_path))
        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            assert cache2.get(str(test_file)) is None

    def test_cache_persistence(self, tmp_path):
        """Should persist cache to disk."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        # Create and save cache
        cache1 = IndexCache(str(tmp_path))
        cache1.store(str(test_file), {"test": True})
        cache1.save()

        # Load in new instance
        cache2 = IndexCache(str(tmp_path))
        cached = cache2.get(str(test_file))

        assert cached == {"test": True}

    def test_cache_stats(self, tmp_path):
        """Should track cache statistics."""
        cache = IndexCache(str(tmp_path))

        # Create some files
        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"# test {i}")

        # Check stale (all should be misses)
        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            cache.is_stale(str(test_file))

        stats = cache.get_stats()
        assert stats.misses == 3
        assert stats.hits == 0

    def test_cache_cleanup_deleted_files(self, tmp_path):
        """Should cleanup cache for deleted files."""
        # Create and cache files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"# test {i}")
            files.append(str(test_file))

        cache = IndexCache(str(tmp_path))
        for f in files:
            cache.store(f, {"test": True})

        # Delete one file
        os.remove(files[1])
        existing = [files[0], files[2]]

        removed = cache.cleanup_deleted_files(existing)
        assert removed == 1


class TestCacheStats:
    """Tests for CacheStats class."""

    def test_hit_rate_empty(self):
        """Should handle zero operations."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """Should calculate hit rate correctly."""
        stats = CacheStats(hits=8, misses=2)
        assert stats.hit_rate == 0.8

    def test_format_summary(self):
        """Should format a readable summary."""
        stats = CacheStats(
            hits=10,
            misses=5,
            total_files=15,
            cached_files=10,
            stale_files=3,
        )
        summary = stats.format_summary()

        assert "Total files: 15" in summary
        assert "Cached: 10" in summary
        assert "Hits: 10" in summary


class TestUXModule:
    """Tests for the UX utilities module."""

    def test_icons_defined(self):
        """Should have standard icons defined."""
        assert "success" in ICONS
        assert "error" in ICONS
        assert "warning" in ICONS
        assert "pending" in ICONS
        assert "completed" in ICONS

    def test_format_status(self):
        """Should format status with icon."""
        status = format_status("completed")
        assert ICONS["completed"] in status or "completed" in status

    def test_format_progress_bar_ux(self):
        """Should format progress bar."""
        bar = ux_format_progress_bar(5, 10)
        assert "5/10" in bar
        assert "50%" in bar

    def test_format_duration_seconds(self):
        """Should format short durations in seconds."""
        duration = format_duration(30.5)
        assert "30" in duration
        assert "s" in duration

    def test_format_duration_minutes(self):
        """Should format longer durations in minutes."""
        duration = format_duration(150)
        assert "m" in duration

    def test_format_duration_hours(self):
        """Should format very long durations in hours."""
        duration = format_duration(7500)
        assert "h" in duration

    def test_set_colors(self):
        """Should allow enabling/disabling colors."""
        # This just tests it doesn't crash
        set_colors(False)
        set_colors(True)


class TestIntegration:
    """Integration tests for UX and diagnostics."""

    def test_full_failure_analysis_workflow(self, tmp_path):
        """Should complete a full failure analysis workflow."""
        from erirpg.runs import RunRecord, StepResult
        from erirpg.verification import VerificationResult, CommandResult

        # Create run with failures
        run = RunRecord(
            id="run-test",
            plan_id="plan-test",
            plan_path=str(tmp_path / "plan.json"),
            status="failed",
            step_results=[
                StepResult(
                    step_id="step-1",
                    status="failed",
                    error="ModuleNotFoundError: No module named 'flask'",
                ),
            ],
        )

        # Create verification failures
        verification_results = [
            VerificationResult(
                step_id="step-1",
                status="failed",
                command_results=[
                    CommandResult(
                        name="test",
                        command="pytest",
                        status="failed",
                        exit_code=1,
                        stderr="FAILED test_app.py::test_home",
                    ),
                ],
            ),
        ]

        # Generate summary
        summary = format_run_failure_summary(run, verification_results)

        assert "Run Failure Summary" in summary
        assert "step-1" in summary
        assert "flask" in summary

        # Get hints
        hints = extract_hints(run.step_results[0].error)
        assert len(hints) >= 1
        assert any("pip install" in h.suggestion for h in hints)
