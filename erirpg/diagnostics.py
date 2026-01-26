"""
Diagnostics module for EriRPG.

Provides better error reporting, failure summaries, and actionable hints
for debugging failed runs and verification.

Usage:
    from erirpg.diagnostics import format_failure_report, suggest_fixes

    report = format_failure_report(run, verification_results)
    hints = suggest_fixes(error_output)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re


@dataclass
class Hint:
    """An actionable hint for fixing an issue."""
    category: str  # e.g., "import", "syntax", "test", "lint"
    message: str
    suggestion: str
    confidence: float = 0.8  # 0.0 to 1.0


# =============================================================================
# Error Pattern Matching
# =============================================================================

# Common error patterns and their hints
ERROR_PATTERNS = [
    # Import errors
    (
        r"ModuleNotFoundError: No module named '(\w+)'",
        "import",
        "Module '{0}' is not installed",
        "Install with: pip install {0}",
    ),
    (
        r"ImportError: cannot import name '(\w+)' from '(\w+)'",
        "import",
        "Cannot import '{0}' from '{1}'",
        "Check if '{0}' exists in '{1}' or update import path",
    ),
    # Syntax errors
    (
        r"SyntaxError: invalid syntax",
        "syntax",
        "Invalid Python syntax",
        "Check for missing colons, parentheses, or indentation",
    ),
    (
        r"IndentationError: (.*)",
        "syntax",
        "Indentation error: {0}",
        "Fix indentation to use consistent spaces/tabs",
    ),
    # Type errors
    (
        r"TypeError: '(\w+)' object is not (callable|iterable|subscriptable)",
        "type",
        "Type error: '{0}' is not {1}",
        "Check variable type or add type conversion",
    ),
    (
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
        "type",
        "'{0}' has no attribute '{1}'",
        "Check spelling or ensure object has the expected attribute",
    ),
    # Test failures
    (
        r"AssertionError: assert (.+) == (.+)",
        "test",
        "Assertion failed: {0} != {1}",
        "Check expected vs actual values and update test or code",
    ),
    (
        r"FAILED (.+)::(.+) - (.+)",
        "test",
        "Test failed: {1} in {0}",
        "Review the test and fix the underlying issue",
    ),
    # Lint errors
    (
        r"(E\d+) (.+)",
        "lint",
        "Lint error {0}: {1}",
        "Fix according to PEP 8 style guide",
    ),
    (
        r"undefined name '(\w+)'",
        "lint",
        "Undefined name: '{0}'",
        "Import or define '{0}' before using it",
    ),
    # File errors
    (
        r"FileNotFoundError: \[Errno 2\] No such file or directory: '(.+)'",
        "file",
        "File not found: {0}",
        "Create the file or fix the path",
    ),
    (
        r"PermissionError: \[Errno 13\] Permission denied: '(.+)'",
        "file",
        "Permission denied: {0}",
        "Check file permissions or run with appropriate access",
    ),
    # Git errors
    (
        r"fatal: not a git repository",
        "git",
        "Not in a git repository",
        "Initialize git with: git init",
    ),
    (
        r"error: pathspec '(.+)' did not match any file",
        "git",
        "Git pathspec error: {0}",
        "Check if the file exists or is staged",
    ),
]


def extract_hints(output: str) -> List[Hint]:
    """Extract hints from error output.

    Args:
        output: Combined stdout/stderr from failed command

    Returns:
        List of Hint objects with suggestions
    """
    hints = []
    seen = set()  # Avoid duplicate hints

    for pattern, category, message_template, suggestion_template in ERROR_PATTERNS:
        for match in re.finditer(pattern, output):
            groups = match.groups()

            # Format message and suggestion with captured groups
            try:
                message = message_template.format(*groups)
                suggestion = suggestion_template.format(*groups)
            except (IndexError, KeyError):
                message = message_template
                suggestion = suggestion_template

            # Dedupe by message
            if message not in seen:
                seen.add(message)
                hints.append(Hint(
                    category=category,
                    message=message,
                    suggestion=suggestion,
                ))

    return hints


def suggest_fixes(output: str) -> List[str]:
    """Get list of fix suggestions from error output.

    Args:
        output: Combined stdout/stderr from failed command

    Returns:
        List of actionable suggestion strings
    """
    hints = extract_hints(output)
    return [f"{h.message} -> {h.suggestion}" for h in hints]


# =============================================================================
# Failure Report Formatting
# =============================================================================

def format_step_failure(
    step_id: str,
    error: str,
    output: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Format a detailed failure report for a single step.

    Args:
        step_id: ID of the failed step
        error: Error message
        output: Full command output
        context: Optional step context

    Returns:
        Formatted failure report
    """
    lines = [
        f"Step Failed: {step_id}",
        "=" * 50,
        "",
        "Error:",
        f"  {error}",
        "",
    ]

    # Extract hints
    hints = extract_hints(output or error)
    if hints:
        lines.append("Likely Issues:")
        for hint in hints[:5]:  # Top 5 hints
            lines.append(f"  [{hint.category}] {hint.message}")
            lines.append(f"    Fix: {hint.suggestion}")
        lines.append("")

    # Add relevant output
    if output:
        lines.append("Output (last 20 lines):")
        output_lines = output.strip().split("\n")[-20:]
        for line in output_lines:
            lines.append(f"  {line}")
        lines.append("")

    # Add context hints
    if context:
        if context.get("inputs"):
            lines.append("Input Files:")
            for f in context["inputs"][:5]:
                lines.append(f"  - {f}")
        if context.get("outputs"):
            lines.append("Expected Outputs:")
            for f in context["outputs"][:5]:
                lines.append(f"  - {f}")

    return "\n".join(lines)


def format_verification_failure(
    step_id: str,
    command_results: List[Any],
) -> str:
    """Format verification failure details.

    Args:
        step_id: ID of the step
        command_results: List of CommandResult objects

    Returns:
        Formatted failure report
    """
    lines = [
        f"Verification Failed: {step_id}",
        "=" * 50,
        "",
    ]

    for result in command_results:
        if result.status != "passed":
            lines.append(f"Command: {result.name}")
            lines.append(f"  Status: {result.status}")
            lines.append(f"  Exit Code: {result.exit_code}")

            if result.error_message:
                lines.append(f"  Error: {result.error_message}")

            # Extract hints from output
            combined_output = f"{result.stdout}\n{result.stderr}"
            hints = extract_hints(combined_output)

            if hints:
                lines.append("  Issues Found:")
                for hint in hints[:3]:
                    lines.append(f"    - {hint.message}")
                    lines.append(f"      Fix: {hint.suggestion}")

            # Show stderr if not empty
            if result.stderr.strip():
                lines.append("  Errors:")
                for line in result.stderr.strip().split("\n")[:10]:
                    lines.append(f"    {line}")

            lines.append("")

    return "\n".join(lines)


def format_run_failure_summary(
    run: Any,
    verification_results: Optional[List[Any]] = None,
) -> str:
    """Format a comprehensive failure summary for a run.

    Args:
        run: RunRecord object
        verification_results: Optional list of VerificationResult objects

    Returns:
        Formatted failure summary
    """
    lines = [
        "Run Failure Summary",
        "=" * 50,
        f"Run ID: {run.id}",
        f"Plan: {run.plan_id}",
        f"Status: {run.status}",
        "",
    ]

    # Count failures
    step_failures = [r for r in run.step_results if r.status == "failed"]
    verification_failures = []
    if verification_results:
        verification_failures = [r for r in verification_results if not r.passed]

    lines.append(f"Step Failures: {len(step_failures)}")
    lines.append(f"Verification Failures: {len(verification_failures)}")
    lines.append("")

    # Step failure details
    if step_failures:
        lines.append("Failed Steps:")
        for result in step_failures:
            lines.append(f"  - {result.step_id}")
            if result.error:
                lines.append(f"    Error: {result.error}")
            hints = extract_hints(result.error + (result.output or ""))
            for hint in hints[:2]:
                lines.append(f"    -> {hint.suggestion}")
        lines.append("")

    # Verification failure details
    if verification_failures:
        lines.append("Failed Verifications:")
        for result in verification_failures:
            lines.append(f"  - {result.step_id}")
            for cmd_result in result.failed_commands:
                lines.append(f"    {cmd_result.name}: exit {cmd_result.exit_code}")
        lines.append("")

    # Overall recommendations
    lines.append("Recommended Actions:")
    if step_failures:
        lines.append("  1. Review the failed step output above")
        lines.append("  2. Fix the underlying issue")
        lines.append(f"  3. Resume with: eri-rpg run resume {run.id}")
    if verification_failures:
        lines.append("  4. Run tests locally to reproduce")
        lines.append("  5. Fix failing tests before continuing")

    return "\n".join(lines)


# =============================================================================
# Progress and Status Formatting
# =============================================================================

def format_progress_bar(
    current: int,
    total: int,
    width: int = 30,
    fill: str = "█",
    empty: str = "░",
) -> str:
    """Format a text-based progress bar.

    Args:
        current: Current progress value
        total: Total value
        width: Bar width in characters
        fill: Fill character
        empty: Empty character

    Returns:
        Formatted progress bar string
    """
    if total == 0:
        pct = 0
    else:
        pct = current / total

    filled = int(width * pct)
    bar = fill * filled + empty * (width - filled)
    return f"[{bar}] {current}/{total} ({pct:.0%})"


def format_status_line(
    step: Any,
    max_width: int = 60,
) -> str:
    """Format a single-line status for a step.

    Args:
        step: PlanStep object
        max_width: Maximum line width

    Returns:
        Formatted status line
    """
    status_icons = {
        "pending": "○",
        "in_progress": "◐",
        "completed": "●",
        "failed": "✗",
        "skipped": "○",
    }

    icon = status_icons.get(step.status, "?")

    # Truncate action if needed
    action = step.action
    if len(action) > max_width - 10:
        action = action[:max_width - 13] + "..."

    risk_badge = ""
    if step.risk in ("high", "critical"):
        risk_badge = f" [{step.risk.upper()}]"

    return f"{icon} {step.order:2}. {action}{risk_badge}"


def format_next_steps(
    current_step: Optional[Any],
    ready_steps: List[Any],
    run_id: str,
) -> str:
    """Format next steps guidance.

    Args:
        current_step: Currently active step
        ready_steps: Steps ready for execution
        run_id: Current run ID

    Returns:
        Formatted next steps guidance
    """
    lines = []

    if current_step:
        lines.extend([
            "Current Step:",
            f"  {current_step.action}",
            "",
            "Next Actions:",
            f"  1. Complete the step using Claude Code",
            f"  2. Mark complete: eri-rpg run step {run_id} {current_step.id} complete",
            f"     Or if failed: eri-rpg run step {run_id} {current_step.id} fail --error 'message'",
        ])
    elif ready_steps:
        lines.extend([
            "Ready Steps:",
        ])
        for step in ready_steps[:3]:
            lines.append(f"  - {step.action}")
        if len(ready_steps) > 3:
            lines.append(f"  ... and {len(ready_steps) - 3} more")
        lines.extend([
            "",
            "Start the next step:",
            f"  eri-rpg run step {run_id} {ready_steps[0].id} start",
        ])
    else:
        lines.extend([
            "No steps ready.",
            "Either all steps are complete or there are blocking dependencies.",
        ])

    return "\n".join(lines)


# =============================================================================
# Impact Warnings
# =============================================================================

def format_impact_warning(
    step: Any,
    impact_score: float,
    affected_modules: List[str],
) -> str:
    """Format a warning for high-impact steps.

    Args:
        step: PlanStep object
        impact_score: Impact score (0-1)
        affected_modules: List of modules that would be affected

    Returns:
        Formatted warning string
    """
    lines = [
        "⚠️  HIGH IMPACT WARNING",
        "=" * 40,
        f"Step: {step.action}",
        f"Impact Score: {impact_score:.1%}",
        "",
        f"This change affects {len(affected_modules)} modules:",
    ]

    for module in affected_modules[:10]:
        lines.append(f"  - {module}")

    if len(affected_modules) > 10:
        lines.append(f"  ... and {len(affected_modules) - 10} more")

    lines.extend([
        "",
        "Recommendations:",
        "  1. Create a backup or commit before proceeding",
        "  2. Review the full impact with: eri-rpg impact <module>",
        "  3. Consider breaking into smaller changes",
    ])

    return "\n".join(lines)


def assess_step_impact(
    step: Any,
    graph: Optional[Any] = None,
) -> Tuple[float, List[str]]:
    """Assess the impact of a step.

    Args:
        step: PlanStep object
        graph: Optional Graph for dependency analysis

    Returns:
        Tuple of (impact_score, affected_modules)
    """
    affected = []
    base_score = 0.0

    # Risk contributes to impact
    risk_scores = {
        "low": 0.1,
        "medium": 0.3,
        "high": 0.6,
        "critical": 0.9,
    }
    base_score = risk_scores.get(step.risk, 0.1)

    # Step type contributes to impact
    type_scores = {
        "create": 0.2,
        "modify": 0.4,
        "delete": 0.6,
        "wire": 0.3,
        "read": 0.0,
        "verify": 0.0,
    }
    base_score += type_scores.get(step.step_type, 0.2)

    # Normalize
    base_score = min(1.0, base_score)

    # Get affected modules from graph
    if graph and step.target:
        # Find modules that depend on the target
        target_name = step.target.rstrip(".py")
        for name, data in graph.modules.items():
            if step.target in data.get("imports", []):
                affected.append(name)

        # More dependents = higher impact
        if len(affected) > 10:
            base_score = min(1.0, base_score + 0.2)
        elif len(affected) > 5:
            base_score = min(1.0, base_score + 0.1)

    return base_score, affected
