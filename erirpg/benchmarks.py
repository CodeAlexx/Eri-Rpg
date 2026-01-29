"""
Benchmarking system for EriRPG.

Provides tools for measuring performance, comparing with baselines,
and generating benchmark reports.

Usage:
    from erirpg.benchmarks import Benchmark, BenchmarkReport

    bench = Benchmark(name="transplant-feature")
    bench.start()
    # ... do work ...
    bench.record_step("planning", duration=1.5, success=True)
    bench.finish()

    report = bench.generate_report()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import os
import time


@dataclass
class BenchmarkStep:
    """A single step in a benchmark run."""
    name: str
    duration: float  # seconds
    success: bool
    error: str = ""
    manual_fixes: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "manual_fixes": self.manual_fixes,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkStep":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            duration=data.get("duration", 0.0),
            success=data.get("success", False),
            error=data.get("error", ""),
            manual_fixes=data.get("manual_fixes", 0),
            notes=data.get("notes", ""),
        )


@dataclass
class Benchmark:
    """A benchmark run measuring performance of a workflow."""
    name: str
    tool: str = "erirpg"  # "erirpg" or "baseline"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List[BenchmarkStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark benchmark as started."""
        self.started_at = datetime.now()

    def finish(self) -> None:
        """Mark benchmark as completed."""
        self.completed_at = datetime.now()

    def record_step(
        self,
        name: str,
        duration: float,
        success: bool,
        error: str = "",
        manual_fixes: int = 0,
        notes: str = "",
    ) -> BenchmarkStep:
        """Record a benchmark step.

        Args:
            name: Step name
            duration: Duration in seconds
            success: Whether step succeeded
            error: Error message if failed
            manual_fixes: Number of manual interventions
            notes: Additional notes

        Returns:
            The recorded step
        """
        step = BenchmarkStep(
            name=name,
            duration=duration,
            success=success,
            error=error,
            manual_fixes=manual_fixes,
            notes=notes,
        )
        self.steps.append(step)
        return step

    @property
    def total_duration(self) -> float:
        """Get total duration of all steps."""
        return sum(s.duration for s in self.steps)

    @property
    def success_rate(self) -> float:
        """Get success rate of steps."""
        if not self.steps:
            return 0.0
        return sum(1 for s in self.steps if s.success) / len(self.steps)

    @property
    def total_manual_fixes(self) -> int:
        """Get total manual interventions."""
        return sum(s.manual_fixes for s in self.steps)

    @property
    def failed_steps(self) -> List[BenchmarkStep]:
        """Get list of failed steps."""
        return [s for s in self.steps if not s.success]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "tool": self.tool,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
            "summary": {
                "total_duration": self.total_duration,
                "success_rate": self.success_rate,
                "total_manual_fixes": self.total_manual_fixes,
                "total_steps": len(self.steps),
                "failed_steps": len(self.failed_steps),
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Benchmark":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            tool=data.get("tool", "erirpg"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            steps=[BenchmarkStep.from_dict(s) for s in data.get("steps", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark runs."""
    erirpg: Benchmark
    baseline: Benchmark
    improvement_metrics: Dict[str, float] = field(default_factory=dict)

    def calculate_improvements(self) -> None:
        """Calculate improvement metrics."""
        # Duration improvement (negative = faster)
        if self.baseline.total_duration > 0:
            duration_pct = (self.erirpg.total_duration - self.baseline.total_duration) / self.baseline.total_duration * 100
        else:
            duration_pct = 0

        # Success rate improvement
        success_diff = self.erirpg.success_rate - self.baseline.success_rate

        # Manual fix reduction (negative = fewer fixes needed)
        manual_fix_diff = self.erirpg.total_manual_fixes - self.baseline.total_manual_fixes

        self.improvement_metrics = {
            "duration_pct": duration_pct,
            "success_rate_diff": success_diff,
            "manual_fix_diff": manual_fix_diff,
        }

    def format_report(self) -> str:
        """Format a comparison report."""
        self.calculate_improvements()

        lines = [
            "Benchmark Comparison Report",
            "=" * 50,
            f"Workflow: {self.erirpg.name}",
            "",
            "                    EriRPG      Baseline    Change",
            "-" * 50,
        ]

        # Duration
        eri_dur = f"{self.erirpg.total_duration:.1f}s"
        baseline_dur = f"{self.baseline.total_duration:.1f}s"
        dur_change = self.improvement_metrics["duration_pct"]
        dur_indicator = "↓" if dur_change < 0 else "↑" if dur_change > 0 else "→"
        lines.append(f"Duration:           {eri_dur:11} {baseline_dur:11} {dur_indicator} {abs(dur_change):.1f}%")

        # Success rate
        eri_sr = f"{self.erirpg.success_rate:.0%}"
        baseline_sr = f"{self.baseline.success_rate:.0%}"
        sr_change = self.improvement_metrics["success_rate_diff"] * 100
        sr_indicator = "↑" if sr_change > 0 else "↓" if sr_change < 0 else "→"
        lines.append(f"Success Rate:       {eri_sr:11} {baseline_sr:11} {sr_indicator} {abs(sr_change):.1f}%")

        # Manual fixes
        eri_fixes = str(self.erirpg.total_manual_fixes)
        baseline_fixes = str(self.baseline.total_manual_fixes)
        fix_change = self.improvement_metrics["manual_fix_diff"]
        fix_indicator = "↓" if fix_change < 0 else "↑" if fix_change > 0 else "→"
        lines.append(f"Manual Fixes:       {eri_fixes:11} {baseline_fixes:11} {fix_indicator} {abs(fix_change)}")

        lines.extend([
            "",
            "Summary:",
        ])

        if dur_change < -10:
            lines.append(f"  ✓ EriRPG is {abs(dur_change):.0f}% faster")
        elif dur_change > 10:
            lines.append(f"  ✗ EriRPG is {dur_change:.0f}% slower")

        if sr_change > 5:
            lines.append(f"  ✓ {sr_change:.0f}% higher success rate")
        elif sr_change < -5:
            lines.append(f"  ✗ {abs(sr_change):.0f}% lower success rate")

        if fix_change < 0:
            lines.append(f"  ✓ {abs(fix_change)} fewer manual interventions")
        elif fix_change > 0:
            lines.append(f"  ✗ {fix_change} more manual interventions")

        return "\n".join(lines)


# =============================================================================
# Backlog Management
# =============================================================================

@dataclass
class BacklogItem:
    """An item in the improvement backlog."""
    id: str
    category: str  # "planning", "memory", "verification", "other"
    title: str
    description: str
    priority: int = 3  # 1=highest, 5=lowest
    source_benchmark: str = ""
    source_step: str = ""
    status: str = "open"  # "open", "in_progress", "done"
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "source_benchmark": self.source_benchmark,
            "source_step": self.source_step,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacklogItem":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            category=data.get("category", "other"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=data.get("priority", 3),
            source_benchmark=data.get("source_benchmark", ""),
            source_step=data.get("source_step", ""),
            status=data.get("status", "open"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


@dataclass
class Backlog:
    """Collection of improvement backlog items."""
    items: List[BacklogItem] = field(default_factory=list)
    _next_id: int = 1

    def add(
        self,
        category: str,
        title: str,
        description: str,
        priority: int = 3,
        source_benchmark: str = "",
        source_step: str = "",
    ) -> BacklogItem:
        """Add a new backlog item.

        Args:
            category: Issue category
            title: Short title
            description: Detailed description
            priority: Priority (1-5)
            source_benchmark: Benchmark that revealed the issue
            source_step: Step that failed

        Returns:
            Created BacklogItem
        """
        item = BacklogItem(
            id=f"BL-{self._next_id:03d}",
            category=category,
            title=title,
            description=description,
            priority=priority,
            source_benchmark=source_benchmark,
            source_step=source_step,
        )
        self.items.append(item)
        self._next_id += 1
        return item

    def get_by_priority(self) -> List[BacklogItem]:
        """Get items sorted by priority (highest first)."""
        return sorted(self.items, key=lambda x: x.priority)

    def get_by_category(self, category: str) -> List[BacklogItem]:
        """Get items in a specific category."""
        return [i for i in self.items if i.category == category]

    def get_open(self) -> List[BacklogItem]:
        """Get all open items."""
        return [i for i in self.items if i.status == "open"]

    def categorize_from_benchmark(self, benchmark: Benchmark) -> int:
        """Create backlog items from benchmark failures.

        Args:
            benchmark: Benchmark with failures to analyze

        Returns:
            Number of items created
        """
        created = 0

        for step in benchmark.failed_steps:
            # Categorize based on step name and error
            if "plan" in step.name.lower():
                category = "planning"
            elif "memory" in step.name.lower() or "knowledge" in step.name.lower():
                category = "memory"
            elif "verify" in step.name.lower() or "test" in step.name.lower():
                category = "verification"
            else:
                category = "other"

            # Determine priority based on manual fixes needed
            if step.manual_fixes > 3:
                priority = 1
            elif step.manual_fixes > 1:
                priority = 2
            else:
                priority = 3

            self.add(
                category=category,
                title=f"Failed: {step.name}",
                description=step.error or step.notes or "Step failed during benchmark",
                priority=priority,
                source_benchmark=benchmark.name,
                source_step=step.name,
            )
            created += 1

        return created

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "items": [i.to_dict() for i in self.items],
            "next_id": self._next_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Backlog":
        """Deserialize from dictionary."""
        backlog = cls(
            items=[BacklogItem.from_dict(i) for i in data.get("items", [])],
            _next_id=data.get("next_id", 1),
        )
        return backlog

    def format_summary(self) -> str:
        """Format a summary of the backlog."""
        by_category = {}
        by_priority = {}

        for item in self.items:
            by_category.setdefault(item.category, []).append(item)
            by_priority.setdefault(item.priority, []).append(item)

        lines = [
            "Backlog Summary",
            "=" * 40,
            f"Total Items: {len(self.items)}",
            f"Open: {len(self.get_open())}",
            "",
            "By Category:",
        ]

        for cat, items in sorted(by_category.items()):
            lines.append(f"  {cat}: {len(items)}")

        lines.extend([
            "",
            "By Priority:",
        ])

        for pri, items in sorted(by_priority.items()):
            lines.append(f"  P{pri}: {len(items)}")

        return "\n".join(lines)


# =============================================================================
# Storage
# =============================================================================

def get_benchmarks_dir(project_path: str) -> str:
    """Get the benchmarks directory for a project."""
    return os.path.join(project_path, ".eri-rpg", "benchmarks")


def save_benchmark(project_path: str, benchmark: Benchmark) -> str:
    """Save a benchmark to disk.

    Args:
        project_path: Path to the project
        benchmark: Benchmark to save

    Returns:
        Path to saved file
    """
    benchmarks_dir = get_benchmarks_dir(project_path)
    os.makedirs(benchmarks_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{benchmark.tool}-{benchmark.name}-{timestamp}.json"
    filepath = os.path.join(benchmarks_dir, filename)

    with open(filepath, "w") as f:
        json.dump(benchmark.to_dict(), f, indent=2)

    return filepath


def load_benchmark(filepath: str) -> Benchmark:
    """Load a benchmark from disk.

    Args:
        filepath: Path to benchmark file

    Returns:
        Loaded Benchmark
    """
    with open(filepath, "r") as f:
        data = json.load(f)
    return Benchmark.from_dict(data)


def list_benchmarks(project_path: str) -> List[str]:
    """List all benchmark files for a project.

    Args:
        project_path: Path to the project

    Returns:
        List of benchmark file paths
    """
    benchmarks_dir = get_benchmarks_dir(project_path)

    if not os.path.exists(benchmarks_dir):
        return []

    return [
        os.path.join(benchmarks_dir, f)
        for f in os.listdir(benchmarks_dir)
        if f.endswith(".json")
    ]


def save_backlog(project_path: str, backlog: Backlog) -> str:
    """Save a backlog to disk.

    Args:
        project_path: Path to the project
        backlog: Backlog to save

    Returns:
        Path to saved file
    """
    erirpg_dir = os.path.join(project_path, ".eri-rpg")
    os.makedirs(erirpg_dir, exist_ok=True)

    filepath = os.path.join(erirpg_dir, "backlog.json")
    with open(filepath, "w") as f:
        json.dump(backlog.to_dict(), f, indent=2)

    return filepath


def load_backlog(project_path: str) -> Optional[Backlog]:
    """Load a backlog from disk.

    Args:
        project_path: Path to the project

    Returns:
        Loaded Backlog or None if not found
    """
    filepath = os.path.join(project_path, ".eri-rpg", "backlog.json")

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r") as f:
        data = json.load(f)

    return Backlog.from_dict(data)
