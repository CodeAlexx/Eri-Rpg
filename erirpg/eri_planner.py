"""
ERI Plan Generator - Creates goal-backward plans for vibe coding.

Generates ERI Plans with:
- Tasks (what to build)
- Must-haves (truths, artifacts, key_links)
- Wave assignments (parallel execution)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib
import json
import os

from erirpg.models.plan import (
    Plan, MustHaves, Truth, Artifact, KeyLink, PlanType
)


def generate_eri_plan(
    spec: Any,
    project_path: str,
    phase: str = "implementation",
) -> Plan:
    """Generate an ERI Plan from a ProjectSpec.

    Uses goal-backward methodology:
    1. State the goal (from spec)
    2. Derive observable truths
    3. Derive required artifacts
    4. Derive tasks to achieve them

    Args:
        spec: ProjectSpec with project details
        project_path: Where the project lives
        phase: Phase name (default: implementation)

    Returns:
        ERI Plan ready for execution
    """
    # Extract info from spec
    name = getattr(spec, 'name', 'project')
    description = getattr(spec, 'description', '') or getattr(spec, 'core_feature', '')
    language = getattr(spec, 'language', 'python')

    # Generate plan ID
    plan_id = f"{phase}-01-{name}"

    # Analyze description to understand what to build
    features = _extract_features(description)

    # Create must-haves based on features
    must_haves = _generate_must_haves(name, features, project_path, language)

    # Create tasks to implement features
    tasks = _generate_tasks(name, features, project_path, language)

    # Create the plan
    plan = Plan(
        id=plan_id,
        phase=phase,
        plan_number=1,
        plan_type=PlanType.AUTONOMOUS,
        wave=1,
        objective=f"Implement {name}: {description}",
        must_haves=must_haves,
        execution_context=_build_execution_context(spec, project_path),
        tasks=tasks,
        verification=[
            f"cd {project_path} && python -m pytest tests/ -v",
            f"cd {project_path} && python -c 'from {name.replace('-', '_')} import *'",
        ],
        success_criteria=[
            "All tests pass",
            "CLI commands work as expected",
            "Code is clean and documented",
        ],
        autonomous=True,
        created_at=datetime.now().isoformat(),
    )

    return plan


def _extract_features(description: str) -> List[str]:
    """Extract features from description.

    Looks for patterns like:
    - "with X, Y, Z"
    - "add, subtract, multiply"
    - comma-separated items
    """
    description = description.lower()

    # Common feature indicators
    features = []

    # Look for "with X, Y, Z" pattern
    if " with " in description:
        after_with = description.split(" with ", 1)[1]
        # Split by comma and "and"
        parts = after_with.replace(" and ", ", ").split(",")
        features.extend([p.strip() for p in parts if p.strip()])

    # Look for operation words
    operations = ["add", "subtract", "multiply", "divide", "calculate",
                  "create", "delete", "update", "list", "search", "filter"]
    for op in operations:
        if op in description:
            features.append(op)

    # If no features found, create generic one
    if not features:
        features = ["core functionality"]

    return features[:6]  # Cap at 6 features


def _generate_must_haves(
    name: str,
    features: List[str],
    project_path: str,
    language: str,
) -> MustHaves:
    """Generate must-haves from features."""

    module_name = name.replace("-", "_")
    src_path = f"src/{module_name}"

    truths = []
    artifacts = []
    key_links = []

    # Generate truths for each feature
    for i, feature in enumerate(features):
        truths.append(Truth(
            id=f"t{i+1}",
            description=f"User can {feature} using the CLI",
            verifiable_by="test",
        ))

    # Core artifacts
    artifacts.extend([
        Artifact(
            path=f"{src_path}/__init__.py",
            provides="Package initialization",
            min_lines=5,
        ),
        Artifact(
            path=f"{src_path}/cli.py",
            provides="CLI entry point with commands",
            min_lines=30,
        ),
        Artifact(
            path=f"{src_path}/core.py",
            provides="Core logic implementation",
            min_lines=20,
        ),
        Artifact(
            path="tests/test_core.py",
            provides="Unit tests for core logic",
            min_lines=20,
        ),
    ])

    # Key links
    key_links.extend([
        KeyLink(
            from_component=f"{src_path}/cli.py",
            to_component=f"{src_path}/core.py",
            via="import",
        ),
        KeyLink(
            from_component="tests/test_core.py",
            to_component=f"{src_path}/core.py",
            via="import",
        ),
    ])

    return MustHaves(
        truths=truths,
        artifacts=artifacts,
        key_links=key_links,
    )


def _generate_tasks(
    name: str,
    features: List[str],
    project_path: str,
    language: str,
) -> List[Dict[str, Any]]:
    """Generate tasks to implement features."""

    module_name = name.replace("-", "_")
    src_path = f"src/{module_name}"

    tasks = []

    # Task 1: Implement core logic
    feature_list = ", ".join(features)
    tasks.append({
        "name": "implement-core",
        "action": f"Create {src_path}/core.py with functions for: {feature_list}",
        "type": "auto",
        "files": [f"{src_path}/core.py"],
        "verify": f"python -c 'from {module_name}.core import *'",
        "done": "Core functions exist and are importable",
        "details": _generate_core_details(features, module_name),
    })

    # Task 2: Implement CLI
    tasks.append({
        "name": "implement-cli",
        "action": f"Update {src_path}/cli.py with commands that use core functions",
        "type": "auto",
        "files": [f"{src_path}/cli.py"],
        "verify": f"python -m {module_name}.cli --help",
        "done": "CLI shows all commands",
        "details": _generate_cli_details(features, module_name),
    })

    # Task 3: Write tests
    tasks.append({
        "name": "write-tests",
        "action": "Create tests/test_core.py with unit tests for all functions",
        "type": "auto",
        "files": ["tests/test_core.py"],
        "verify": f"cd {project_path} && python -m pytest tests/ -v",
        "done": "All tests pass",
        "details": _generate_test_details(features, module_name),
    })

    return tasks


def _generate_core_details(features: List[str], module_name: str) -> str:
    """Generate detailed instructions for core implementation."""
    lines = [
        f"Create {module_name}/core.py with the following functions:",
        "",
    ]

    for feature in features:
        func_name = feature.replace(" ", "_").lower()
        lines.append(f"- {func_name}(): Implement {feature} functionality")

    lines.extend([
        "",
        "Requirements:",
        "- Each function should have proper type hints",
        "- Each function should have a docstring",
        "- Handle edge cases (division by zero, invalid input, etc.)",
        "- Return appropriate types",
    ])

    return "\n".join(lines)


def _generate_cli_details(features: List[str], module_name: str) -> str:
    """Generate detailed instructions for CLI implementation."""
    lines = [
        f"Update {module_name}/cli.py:",
        "",
        "1. Import functions from core.py",
        "2. Create a Click command for each feature:",
        "",
    ]

    for feature in features:
        cmd_name = feature.replace(" ", "-").lower()
        lines.append(f"   - @cli.command('{cmd_name}')")

    lines.extend([
        "",
        "3. Each command should:",
        "   - Accept appropriate arguments",
        "   - Call the corresponding core function",
        "   - Display the result",
        "   - Handle errors gracefully",
    ])

    return "\n".join(lines)


def _generate_test_details(features: List[str], module_name: str) -> str:
    """Generate detailed instructions for tests."""
    lines = [
        "Create tests/test_core.py with:",
        "",
        f"from {module_name}.core import *",
        "",
        "Test functions:",
    ]

    for feature in features:
        func_name = feature.replace(" ", "_").lower()
        lines.append(f"- test_{func_name}(): Test {feature} with normal inputs")
        lines.append(f"- test_{func_name}_edge_cases(): Test edge cases")

    lines.extend([
        "",
        "Use pytest assertions.",
        "Test both success and error cases.",
    ])

    return "\n".join(lines)


def _build_execution_context(spec: Any, project_path: str) -> str:
    """Build execution context for the plan."""
    name = getattr(spec, 'name', 'project')
    description = getattr(spec, 'description', '') or getattr(spec, 'core_feature', '')
    language = getattr(spec, 'language', 'python')
    framework = getattr(spec, 'framework', None)

    lines = [
        f"# Project: {name}",
        f"# Path: {project_path}",
        f"# Language: {language}",
    ]

    if framework:
        lines.append(f"# Framework: {framework}")

    lines.extend([
        "",
        "## Goal",
        description,
        "",
        "## Instructions",
        "1. Read existing scaffolded files first",
        "2. Implement each task in order",
        "3. Commit after each task",
        "4. Run tests after implementation",
    ])

    return "\n".join(lines)


def save_eri_plan(project_path: str, plan: Plan) -> str:
    """Save ERI Plan to project's phases directory.

    Args:
        project_path: Project root
        plan: ERI Plan to save

    Returns:
        Path to saved file
    """
    phases_dir = os.path.join(project_path, ".eri-rpg", "phases", plan.phase)
    os.makedirs(phases_dir, exist_ok=True)

    file_path = os.path.join(phases_dir, f"{plan.plan_number:02d}-PLAN.json")

    with open(file_path, "w") as f:
        json.dump(plan.to_dict(), f, indent=2)

    return file_path


def load_eri_plan(project_path: str, phase: str = "implementation", plan_number: int = 1) -> Optional[Plan]:
    """Load ERI Plan from project.

    Args:
        project_path: Project root
        phase: Phase name
        plan_number: Plan number

    Returns:
        Plan if found, None otherwise
    """
    file_path = os.path.join(
        project_path, ".eri-rpg", "phases", phase, f"{plan_number:02d}-PLAN.json"
    )

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return Plan.from_dict(data)


def format_plan_for_execution(plan: Plan) -> str:
    """Format plan as instructions for Claude to execute.

    Args:
        plan: ERI Plan

    Returns:
        Formatted string with execution instructions
    """
    lines = [
        "=" * 60,
        f"ERI PLAN: {plan.objective}",
        "=" * 60,
        "",
        "## Must-Haves (verify these when done)",
        "",
        "### Truths (observable outcomes):",
    ]

    for truth in plan.must_haves.truths:
        lines.append(f"  - [ ] {truth.description}")

    lines.extend([
        "",
        "### Artifacts (files that must exist):",
    ])

    for artifact in plan.must_haves.artifacts:
        lines.append(f"  - [ ] {artifact.path} (>{artifact.min_lines} lines)")

    lines.extend([
        "",
        "### Key Links (connections to verify):",
    ])

    for link in plan.must_haves.key_links:
        lines.append(f"  - [ ] {link.from_component} → {link.to_component} ({link.via})")

    lines.extend([
        "",
        "=" * 60,
        "TASKS",
        "=" * 60,
        "",
    ])

    for i, task in enumerate(plan.tasks, 1):
        lines.extend([
            f"## Task {i}: {task.get('name', f'task-{i}')}",
            "",
            f"**Action:** {task.get('action', '')}",
            "",
            f"**Files:** {', '.join(task.get('files', []))}",
            "",
            f"**Done when:** {task.get('done', '')}",
            "",
        ])

        if task.get('details'):
            lines.extend([
                "**Details:**",
                "```",
                task['details'],
                "```",
                "",
            ])

        lines.append("-" * 40)
        lines.append("")

    lines.extend([
        "",
        "## Verification Commands",
        "",
    ])

    for cmd in plan.verification:
        lines.append(f"  {cmd}")

    return "\n".join(lines)
