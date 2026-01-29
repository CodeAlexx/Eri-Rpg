"""
Tests for EriRPG benchmarking system.

Phase 8: Evaluation and Iteration
- P8-001: Benchmark against baseline
- P8-002: Failure analysis backlog
- P8-003: Iterate and retest
"""

import json
import os
import pytest
from datetime import datetime

from erirpg.benchmarks import (
    BenchmarkStep,
    Benchmark,
    BenchmarkComparison,
    BacklogItem,
    Backlog,
    save_benchmark,
    load_benchmark,
    list_benchmarks,
    save_backlog,
    load_backlog,
)


class TestBenchmarkStep:
    """Tests for BenchmarkStep model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        step = BenchmarkStep(name="test", duration=1.0, success=True)
        assert step.name == "test"
        assert step.duration == 1.0
        assert step.success is True
        assert step.error == ""
        assert step.manual_fixes == 0

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        step = BenchmarkStep(
            name="planning",
            duration=5.5,
            success=False,
            error="Plan generation failed",
            manual_fixes=2,
            notes="Had to fix imports manually",
        )

        data = step.to_dict()
        restored = BenchmarkStep.from_dict(data)

        assert restored.name == step.name
        assert restored.duration == step.duration
        assert restored.success == step.success
        assert restored.error == step.error
        assert restored.manual_fixes == step.manual_fixes


class TestBenchmark:
    """Tests for Benchmark model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        bench = Benchmark(name="test-workflow")
        assert bench.name == "test-workflow"
        assert bench.tool == "erirpg"
        assert bench.steps == []
        assert bench.started_at is None

    def test_start_and_finish(self):
        """Should track start and finish times."""
        bench = Benchmark(name="test")
        bench.start()
        assert bench.started_at is not None

        bench.finish()
        assert bench.completed_at is not None
        assert bench.completed_at >= bench.started_at

    def test_record_step(self):
        """Should record benchmark steps."""
        bench = Benchmark(name="test")
        step = bench.record_step(
            name="planning",
            duration=5.0,
            success=True,
        )

        assert step.name == "planning"
        assert len(bench.steps) == 1
        assert bench.steps[0] == step

    def test_total_duration(self):
        """Should calculate total duration."""
        bench = Benchmark(name="test")
        bench.record_step("step1", 5.0, True)
        bench.record_step("step2", 3.0, True)
        bench.record_step("step3", 2.0, False)

        assert bench.total_duration == 10.0

    def test_success_rate(self):
        """Should calculate success rate."""
        bench = Benchmark(name="test")
        bench.record_step("step1", 1.0, True)
        bench.record_step("step2", 1.0, True)
        bench.record_step("step3", 1.0, False)
        bench.record_step("step4", 1.0, True)

        assert bench.success_rate == 0.75

    def test_success_rate_empty(self):
        """Should handle empty steps."""
        bench = Benchmark(name="test")
        assert bench.success_rate == 0.0

    def test_total_manual_fixes(self):
        """Should sum manual fixes."""
        bench = Benchmark(name="test")
        bench.record_step("step1", 1.0, True, manual_fixes=2)
        bench.record_step("step2", 1.0, False, manual_fixes=3)

        assert bench.total_manual_fixes == 5

    def test_failed_steps(self):
        """Should list failed steps."""
        bench = Benchmark(name="test")
        bench.record_step("pass1", 1.0, True)
        bench.record_step("fail1", 1.0, False)
        bench.record_step("pass2", 1.0, True)
        bench.record_step("fail2", 1.0, False)

        failed = bench.failed_steps
        assert len(failed) == 2
        assert failed[0].name == "fail1"
        assert failed[1].name == "fail2"

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        bench = Benchmark(name="transplant-feature", tool="erirpg")
        bench.start()
        bench.record_step("planning", 5.0, True)
        bench.record_step("execution", 10.0, True)
        bench.finish()

        data = bench.to_dict()
        restored = Benchmark.from_dict(data)

        assert restored.name == bench.name
        assert restored.tool == bench.tool
        assert len(restored.steps) == 2
        assert restored.total_duration == 15.0


class TestBenchmarkComparison:
    """Tests for BenchmarkComparison model."""

    def test_calculate_improvements(self):
        """Should calculate improvement metrics."""
        eri = Benchmark(name="test", tool="erirpg")
        eri.record_step("step1", 3.0, True)
        eri.record_step("step2", 2.0, True, manual_fixes=1)

        baseline = Benchmark(name="test", tool="baseline")
        baseline.record_step("step1", 5.0, True)
        baseline.record_step("step2", 3.0, False, manual_fixes=3)

        comparison = BenchmarkComparison(erirpg=eri, baseline=baseline)
        comparison.calculate_improvements()

        # EriRPG should be faster (5s vs 8s = -37.5%)
        assert comparison.improvement_metrics["duration_pct"] < 0

        # EriRPG should have higher success rate (100% vs 50%)
        assert comparison.improvement_metrics["success_rate_diff"] > 0

        # EriRPG should have fewer manual fixes (1 vs 3)
        assert comparison.improvement_metrics["manual_fix_diff"] < 0

    def test_format_report(self):
        """Should format a comparison report."""
        eri = Benchmark(name="test-workflow", tool="erirpg")
        eri.record_step("planning", 3.0, True)

        baseline = Benchmark(name="test-workflow", tool="baseline")
        baseline.record_step("planning", 5.0, True)

        comparison = BenchmarkComparison(erirpg=eri, baseline=baseline)
        report = comparison.format_report()

        assert "Benchmark Comparison Report" in report
        assert "test-workflow" in report
        assert "EriRPG" in report
        assert "Baseline" in report


class TestBacklogItem:
    """Tests for BacklogItem model."""

    def test_defaults(self):
        """Should have sensible defaults."""
        item = BacklogItem(
            id="BL-001",
            category="planning",
            title="Fix plan generation",
            description="Plans fail on complex specs",
        )

        assert item.id == "BL-001"
        assert item.priority == 3
        assert item.status == "open"

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        item = BacklogItem(
            id="BL-001",
            category="verification",
            title="Test failures",
            description="Tests failing due to imports",
            priority=1,
            source_benchmark="bench-001",
            source_step="verify",
            status="in_progress",
        )

        data = item.to_dict()
        restored = BacklogItem.from_dict(data)

        assert restored.id == item.id
        assert restored.category == item.category
        assert restored.priority == item.priority
        assert restored.status == item.status


class TestBacklog:
    """Tests for Backlog model."""

    def test_add_item(self):
        """Should add new items with IDs."""
        backlog = Backlog()

        item1 = backlog.add("planning", "Issue 1", "Description 1")
        item2 = backlog.add("memory", "Issue 2", "Description 2")

        assert item1.id == "BL-001"
        assert item2.id == "BL-002"
        assert len(backlog.items) == 2

    def test_get_by_priority(self):
        """Should sort by priority."""
        backlog = Backlog()
        backlog.add("a", "Low", "Low priority", priority=5)
        backlog.add("b", "High", "High priority", priority=1)
        backlog.add("c", "Medium", "Medium priority", priority=3)

        sorted_items = backlog.get_by_priority()
        assert sorted_items[0].priority == 1
        assert sorted_items[1].priority == 3
        assert sorted_items[2].priority == 5

    def test_get_by_category(self):
        """Should filter by category."""
        backlog = Backlog()
        backlog.add("planning", "Plan issue 1", "")
        backlog.add("memory", "Memory issue", "")
        backlog.add("planning", "Plan issue 2", "")

        planning = backlog.get_by_category("planning")
        assert len(planning) == 2

    def test_get_open(self):
        """Should get only open items."""
        backlog = Backlog()
        item1 = backlog.add("a", "Open 1", "")
        item2 = backlog.add("b", "Done", "")
        item3 = backlog.add("c", "Open 2", "")

        item2.status = "done"

        open_items = backlog.get_open()
        assert len(open_items) == 2

    def test_categorize_from_benchmark(self):
        """Should create items from benchmark failures."""
        bench = Benchmark(name="test")
        bench.record_step("planning phase", 5.0, False, error="Plan failed")
        bench.record_step("memory lookup", 2.0, False, error="Not found", manual_fixes=4)
        bench.record_step("execution", 10.0, True)

        backlog = Backlog()
        created = backlog.categorize_from_benchmark(bench)

        assert created == 2  # Two failed steps
        assert len(backlog.items) == 2

        # Check category detection
        categories = {i.category for i in backlog.items}
        assert "planning" in categories
        assert "memory" in categories

        # Check priority based on manual fixes
        memory_item = next(i for i in backlog.items if i.category == "memory")
        assert memory_item.priority == 1  # High priority due to 4 manual fixes

    def test_format_summary(self):
        """Should format a summary."""
        backlog = Backlog()
        backlog.add("planning", "Issue 1", "", priority=1)
        backlog.add("planning", "Issue 2", "", priority=2)
        backlog.add("memory", "Issue 3", "", priority=1)

        summary = backlog.format_summary()

        assert "Backlog Summary" in summary
        assert "Total Items: 3" in summary
        assert "planning" in summary
        assert "memory" in summary

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        backlog = Backlog()
        backlog.add("planning", "Issue 1", "Desc 1")
        backlog.add("memory", "Issue 2", "Desc 2")

        data = backlog.to_dict()
        restored = Backlog.from_dict(data)

        assert len(restored.items) == 2
        assert restored._next_id == 3


class TestBenchmarkStorage:
    """Tests for benchmark storage functions."""

    def test_save_and_load_benchmark(self, tmp_path):
        """Should save and load benchmark."""
        bench = Benchmark(name="test-workflow", tool="erirpg")
        bench.start()
        bench.record_step("planning", 5.0, True)
        bench.finish()

        filepath = save_benchmark(str(tmp_path), bench)
        assert os.path.exists(filepath)

        loaded = load_benchmark(filepath)
        assert loaded.name == bench.name
        assert len(loaded.steps) == 1

    def test_list_benchmarks(self, tmp_path):
        """Should list all benchmarks."""
        # Save multiple benchmarks
        for i in range(3):
            bench = Benchmark(name=f"workflow-{i}", tool="erirpg")
            bench.record_step("step", 1.0, True)
            save_benchmark(str(tmp_path), bench)

        files = list_benchmarks(str(tmp_path))
        assert len(files) == 3

    def test_list_benchmarks_empty(self, tmp_path):
        """Should handle empty directory."""
        files = list_benchmarks(str(tmp_path))
        assert files == []


class TestBacklogStorage:
    """Tests for backlog storage functions."""

    def test_save_and_load_backlog(self, tmp_path):
        """Should save and load backlog."""
        backlog = Backlog()
        backlog.add("planning", "Issue 1", "Description")
        backlog.add("memory", "Issue 2", "Description")

        save_backlog(str(tmp_path), backlog)
        loaded = load_backlog(str(tmp_path))

        assert loaded is not None
        assert len(loaded.items) == 2

    def test_load_backlog_not_found(self, tmp_path):
        """Should return None when backlog doesn't exist."""
        loaded = load_backlog(str(tmp_path))
        assert loaded is None


class TestIntegration:
    """Integration tests for the full benchmarking workflow."""

    def test_full_benchmark_workflow(self, tmp_path):
        """Should complete a full benchmark and comparison workflow."""
        # 1. Run EriRPG benchmark
        eri_bench = Benchmark(name="transplant-auth", tool="erirpg")
        eri_bench.start()
        eri_bench.record_step("index", 2.0, True)
        eri_bench.record_step("extract", 3.0, True)
        eri_bench.record_step("plan", 1.5, True)
        eri_bench.record_step("execute", 10.0, True, manual_fixes=1)
        eri_bench.record_step("verify", 2.0, True)
        eri_bench.finish()

        # 2. Run baseline benchmark (simulated)
        baseline_bench = Benchmark(name="transplant-auth", tool="baseline")
        baseline_bench.start()
        baseline_bench.record_step("index", 3.0, True)
        baseline_bench.record_step("extract", 5.0, True)
        baseline_bench.record_step("plan", 2.0, False, error="Context limit", manual_fixes=2)
        baseline_bench.record_step("execute", 15.0, True, manual_fixes=3)
        baseline_bench.record_step("verify", 3.0, False, error="Tests failed")
        baseline_bench.finish()

        # 3. Save both benchmarks
        save_benchmark(str(tmp_path), eri_bench)
        save_benchmark(str(tmp_path), baseline_bench)

        # 4. Compare results
        comparison = BenchmarkComparison(erirpg=eri_bench, baseline=baseline_bench)
        comparison.calculate_improvements()

        # EriRPG should be better
        assert comparison.improvement_metrics["duration_pct"] < 0  # Faster
        assert comparison.improvement_metrics["success_rate_diff"] > 0  # Higher success
        assert comparison.improvement_metrics["manual_fix_diff"] < 0  # Fewer fixes

        # 5. Generate backlog from baseline failures
        backlog = Backlog()
        created = backlog.categorize_from_benchmark(baseline_bench)
        assert created == 2  # Two failed steps

        # 6. Save and reload backlog
        save_backlog(str(tmp_path), backlog)
        loaded_backlog = load_backlog(str(tmp_path))

        assert loaded_backlog is not None
        assert len(loaded_backlog.items) == 2

        # 7. Generate comparison report
        report = comparison.format_report()
        assert "Benchmark Comparison Report" in report
        assert "transplant-auth" in report

    def test_benchmark_to_backlog_conversion(self, tmp_path):
        """Should convert benchmark failures to prioritized backlog."""
        # Simulate a benchmark with various failure types
        bench = Benchmark(name="complex-transplant", tool="erirpg")

        # Success
        bench.record_step("index project", 2.0, True)

        # Planning failure - critical
        bench.record_step("generate plan", 3.0, False,
                         error="Circular dependency detected",
                         manual_fixes=5)

        # Memory failure - high priority
        bench.record_step("memory recall", 1.0, False,
                         error="Learning not found",
                         manual_fixes=2)

        # Verification failure - medium priority
        bench.record_step("verify tests", 5.0, False,
                         error="2 tests failed")

        # Success
        bench.record_step("cleanup", 0.5, True)

        # Create backlog from failures
        backlog = Backlog()
        backlog.categorize_from_benchmark(bench)

        # Should have 3 items
        assert len(backlog.items) == 3

        # Check priority assignment
        by_priority = backlog.get_by_priority()

        # First should be critical (5 manual fixes = P1)
        assert by_priority[0].priority == 1
        assert "plan" in by_priority[0].title.lower()

        # Save backlog
        save_backlog(str(tmp_path), backlog)

        # Verify summary
        summary = backlog.format_summary()
        assert "Total Items: 3" in summary
