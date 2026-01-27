"""
Preflight checks before any code operation.

MANDATORY before any code change. No exceptions.

This module provides pre-operation validation to ensure:
1. We understand what we're about to touch (existing learnings)
2. We know the impact zone (dependencies and dependents)
3. We've assessed the risk
4. We have all prerequisites met
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from erirpg.graph import Graph
    from erirpg.memory import StoredLearning
    from erirpg.verification import BreakingChange


@dataclass
class PreflightReport:
    """Report from preflight checks."""

    # What we're about to do
    operation: str  # "refactor" | "transplant" | "modify" | "new"
    target_files: List[str] = field(default_factory=list)

    # What we know
    existing_learnings: Dict[str, "StoredLearning"] = field(default_factory=dict)
    stale_learnings: List[str] = field(default_factory=list)
    missing_learnings: List[str] = field(default_factory=list)

    # Impact analysis
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    dependents: Dict[str, List[str]] = field(default_factory=dict)
    impact_zone: List[str] = field(default_factory=list)

    # Recommendations
    must_learn_first: List[str] = field(default_factory=list)
    should_review: List[str] = field(default_factory=list)
    high_risk: bool = False
    risk_reasons: List[str] = field(default_factory=list)

    # Contract validation (if before_graph provided)
    breaking_changes: List["BreakingChange"] = field(default_factory=list)

    # Ready to proceed?
    ready: bool = False
    blockers: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def format(self) -> str:
        """Format report for display."""
        lines = []
        lines.append(f"{'═' * 50}")
        lines.append(f" PREFLIGHT: {self.operation.upper()}")
        lines.append(f"{'═' * 50}")
        lines.append(f"Target files: {len(self.target_files)}")

        if self.existing_learnings:
            lines.append(f"\n✓ Known ({len(self.existing_learnings)}):")
            for path in self.existing_learnings:
                lines.append(f"  - {path}")

        if self.stale_learnings:
            lines.append(f"\n⚠ Stale ({len(self.stale_learnings)}):")
            for path in self.stale_learnings:
                lines.append(f"  - {path}")

        if self.missing_learnings:
            lines.append(f"\n✗ Unknown ({len(self.missing_learnings)}):")
            for path in self.missing_learnings:
                lines.append(f"  - {path}")

        if self.impact_zone:
            lines.append(f"\n◎ Impact zone ({len(self.impact_zone)}):")
            for path in self.impact_zone[:10]:  # Limit display
                lines.append(f"  - {path}")
            if len(self.impact_zone) > 10:
                lines.append(f"  ... and {len(self.impact_zone) - 10} more")

        if self.breaking_changes:
            lines.append(f"\n⚠️  CONTRACT BREAKS ({len(self.breaking_changes)}):")
            for bc in self.breaking_changes[:5]:  # Show first 5
                lines.append(f"  - {bc.module}::{bc.interface_name} ({bc.change_type})")
            if len(self.breaking_changes) > 5:
                lines.append(f"  ... and {len(self.breaking_changes) - 5} more")

        if self.high_risk:
            lines.append(f"\n🔴 HIGH RISK:")
            for reason in self.risk_reasons:
                lines.append(f"  - {reason}")

        if self.blockers:
            lines.append(f"\n🚫 BLOCKERS:")
            for blocker in self.blockers:
                lines.append(f"  - {blocker}")

        if self.must_learn_first:
            lines.append(f"\n📚 Must learn first:")
            for path in self.must_learn_first:
                lines.append(f"  eri-rpg learn <project> {path}")

        lines.append("")
        if self.ready:
            lines.append("✅ READY TO PROCEED")
        else:
            lines.append("❌ NOT READY - resolve blockers first")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "target_files": self.target_files,
            "existing_learnings": list(self.existing_learnings.keys()),
            "stale_learnings": self.stale_learnings,
            "missing_learnings": self.missing_learnings,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "impact_zone": self.impact_zone,
            "must_learn_first": self.must_learn_first,
            "should_review": self.should_review,
            "high_risk": self.high_risk,
            "risk_reasons": self.risk_reasons,
            "breaking_changes": [
                {"module": bc.module, "interface": bc.interface_name, "type": bc.change_type}
                for bc in self.breaking_changes
            ],
            "ready": self.ready,
            "blockers": self.blockers,
            "created_at": self.created_at.isoformat(),
        }


def normalize_path(path: str, project_path: str = "") -> str:
    """
    Normalize a file path for consistent comparison.

    Args:
        path: Path to normalize (can be relative or absolute)
        project_path: Project root for making paths relative

    Returns:
        Normalized path (relative to project if project_path given)
    """
    import os
    from pathlib import Path

    # Handle empty paths
    if not path:
        return path

    # Expand user and resolve
    expanded = os.path.expanduser(path)

    # If absolute, normalize it
    if os.path.isabs(expanded):
        normalized = os.path.normpath(expanded)
        # If project_path given, make relative
        if project_path:
            project_abs = os.path.normpath(os.path.abspath(project_path))
            if normalized.startswith(project_abs):
                normalized = os.path.relpath(normalized, project_abs)
    else:
        # Relative path - just normalize
        normalized = os.path.normpath(expanded)

    # Remove leading ./ if present
    if normalized.startswith("./"):
        normalized = normalized[2:]

    return normalized


def preflight(
    project_path: str,
    files: List[str],
    operation: str,
    graph: Optional["Graph"] = None,
    before_graph: Optional["Graph"] = None,
    strict: bool = True,
) -> PreflightReport:
    """
    Run preflight checks before any code operation.

    Args:
        project_path: Path to project root
        files: Files that will be touched
        operation: "refactor" | "transplant" | "modify" | "new"
        graph: Project's dependency graph (optional, loaded if available)
        before_graph: Previous graph for contract validation (optional)
        strict: If True, missing learnings block refactor/modify operations

    Returns:
        PreflightReport with findings and recommendations
    """
    from erirpg.memory import load_knowledge, KnowledgeStore, get_knowledge_path
    from erirpg.indexer import get_or_load_graph
    from erirpg.registry import Registry
    import os

    # Normalize all input paths for consistent comparison
    project_path = os.path.normpath(os.path.abspath(project_path))
    normalized_files = [normalize_path(f, project_path) for f in files]

    report = PreflightReport(
        operation=operation,
        target_files=normalized_files,
    )

    # Load knowledge store
    # Try to find project name from registry, otherwise use "unknown"
    project_name = "unknown"
    registry = Registry.get_instance()
    for proj in registry.list():
        if os.path.abspath(proj.path) == os.path.abspath(project_path):
            project_name = proj.name
            break

    knowledge_store = load_knowledge(project_path, project_name)

    # Try to load graph if not provided
    if graph is None:
        try:
            # Find project in registry
            registry = Registry.get_instance()
            for proj in registry.list():
                if os.path.abspath(proj.path) == os.path.abspath(project_path):
                    graph = get_or_load_graph(proj)
                    break
        except Exception as e:
            import sys; print(f"[EriRPG] {e}", file=sys.stderr)  # Graph not available, skip dependency analysis

    # Check learnings for each file
    for file_path in normalized_files:
        # module_key is already normalized
        module_key = file_path

        learning = knowledge_store.get_learning(module_key)

        if learning:
            report.existing_learnings[file_path] = learning

            # Check staleness
            if learning.is_stale(project_path):
                report.stale_learnings.append(file_path)
        else:
            report.missing_learnings.append(file_path)

    # Get dependencies and dependents from graph
    if graph:
        for file_path in normalized_files:
            module_key = file_path
            module = graph.get_module(module_key)

            if module:
                # What this file depends on (internal deps)
                deps = graph.get_deps(module_key)
                if deps:
                    report.dependencies[file_path] = deps

                # What depends on this file
                dependents = graph.get_dependents(module_key)
                if dependents:
                    report.dependents[file_path] = dependents

        # Calculate impact zone (all transitively affected modules)
        impact_set = set()
        for file_path in normalized_files:
            module_key = file_path
            dependents = graph.get_transitive_dependents(module_key)
            impact_set.update(dependents)

        report.impact_zone = sorted(list(impact_set))

    # Assess risk
    if len(report.impact_zone) > 10:
        report.high_risk = True
        report.risk_reasons.append(
            f"Large impact zone: {len(report.impact_zone)} modules affected"
        )

    if len(report.missing_learnings) > len(report.existing_learnings):
        report.high_risk = True
        report.risk_reasons.append("More unknown than known modules")

    if operation in ("refactor", "modify") and report.stale_learnings:
        report.high_risk = True
        report.risk_reasons.append(
            f"Stale learnings: {len(report.stale_learnings)} files may have changed"
        )

    # Contract validation (if before_graph provided)
    if before_graph and graph:
        from erirpg.verification import validate_interface_contracts
        breaking = validate_interface_contracts(before_graph, graph)
        # Filter to only breaking changes in target files
        report.breaking_changes = [
            bc for bc in breaking
            if bc.module in files or bc.module.lstrip("./") in files
        ]
        if report.breaking_changes:
            report.high_risk = True
            report.risk_reasons.append(
                f"Contract breaks: {len(report.breaking_changes)} interface changes detected"
            )

    # Determine blockers
    if strict and operation in ("refactor", "modify") and report.missing_learnings:
        report.must_learn_first = report.missing_learnings
        report.blockers.append(
            "Must learn target modules before modifying. "
            "Run preflight with strict=False to override."
        )

    if operation == "transplant" and not report.existing_learnings:
        report.blockers.append(
            "Must learn source modules before transplanting"
        )

    # Set ready status
    report.ready = len(report.blockers) == 0

    # Recommendations
    report.should_review = report.stale_learnings.copy()

    return report


def require_preflight(func):
    """Decorator to require preflight before operation."""
    def wrapper(*args, **kwargs):
        # Check if preflight was run
        if not kwargs.get('_preflight_done'):
            raise RuntimeError(
                "Preflight required. Run agent.preflight() first.\n"
                "No preflight = no code changes."
            )
        return func(*args, **kwargs)
    return wrapper
