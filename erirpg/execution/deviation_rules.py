"""
Deviation rules for execution.

Four rules, in priority order:
1. Auto-fix bugs (logic errors, type errors, security vulns)
2. Auto-add missing critical (error handling, validation, auth checks)
3. Auto-fix blocking issues (missing deps, wrong imports, config errors)
4. ASK about architectural changes (new DB table, switching libs, API changes)

If Rule 4 applies → STOP and checkpoint
If Rules 1-3 apply → Fix automatically and track in Summary
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import re


class DeviationType(Enum):
    """Type of deviation from plan."""
    BUG = "bug"                    # Logic, type, security errors
    MISSING_CRITICAL = "critical"  # Missing error handling, validation
    BLOCKING = "blocking"          # Missing deps, imports, config
    ARCHITECTURAL = "architectural"  # DB changes, lib switches, API changes


class DeviationAction(Enum):
    """Action to take for a deviation."""
    AUTO_FIX = "auto_fix"      # Fix immediately, track in Summary
    CHECKPOINT = "checkpoint"  # Stop and ask user


@dataclass
class DeviationRule:
    """A rule for handling deviations."""
    name: str
    deviation_type: DeviationType
    action: DeviationAction
    patterns: List[str]  # Regex patterns to match
    description: str


# Deviation rules in priority order
DEVIATION_RULES: List[DeviationRule] = [
    # Rule 4: Architectural changes → CHECKPOINT (highest priority, check first)
    DeviationRule(
        name="architectural_db",
        deviation_type=DeviationType.ARCHITECTURAL,
        action=DeviationAction.CHECKPOINT,
        patterns=[
            r"CREATE\s+TABLE",
            r"ALTER\s+TABLE",
            r"DROP\s+TABLE",
            r"add.*migration",
            r"new.*model",
            r"schema.*change",
        ],
        description="Database schema changes require human approval",
    ),
    DeviationRule(
        name="architectural_lib",
        deviation_type=DeviationType.ARCHITECTURAL,
        action=DeviationAction.CHECKPOINT,
        patterns=[
            r"switch.*to\s+\w+",
            r"replace.*with\s+\w+",
            r"migrate.*from.*to",
            r"new\s+dependency",
            r"add.*package",
        ],
        description="Library/framework changes require human approval",
    ),
    DeviationRule(
        name="architectural_api",
        deviation_type=DeviationType.ARCHITECTURAL,
        action=DeviationAction.CHECKPOINT,
        patterns=[
            r"change.*api",
            r"modify.*endpoint",
            r"breaking.*change",
            r"remove.*parameter",
            r"change.*response",
        ],
        description="API changes require human approval",
    ),

    # Rule 1: Bugs → AUTO_FIX
    DeviationRule(
        name="bug_logic",
        deviation_type=DeviationType.BUG,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"logic\s+error",
            r"wrong\s+condition",
            r"incorrect\s+calculation",
            r"off.by.one",
            r"null\s+pointer",
            r"undefined\s+reference",
        ],
        description="Logic errors should be fixed immediately",
    ),
    DeviationRule(
        name="bug_type",
        deviation_type=DeviationType.BUG,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"type\s+error",
            r"type\s+mismatch",
            r"wrong\s+type",
            r"incompatible\s+type",
            r"cannot\s+assign",
        ],
        description="Type errors should be fixed immediately",
    ),
    DeviationRule(
        name="bug_security",
        deviation_type=DeviationType.BUG,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"security\s+vulnerability",
            r"sql\s+injection",
            r"xss",
            r"csrf",
            r"authentication\s+bypass",
            r"insecure",
        ],
        description="Security vulnerabilities should be fixed immediately",
    ),

    # Rule 2: Missing critical → AUTO_FIX
    DeviationRule(
        name="critical_error_handling",
        deviation_type=DeviationType.MISSING_CRITICAL,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"missing\s+error\s+handling",
            r"no\s+try.catch",
            r"unhandled\s+exception",
            r"need.*error.*handling",
        ],
        description="Missing error handling should be added",
    ),
    DeviationRule(
        name="critical_validation",
        deviation_type=DeviationType.MISSING_CRITICAL,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"missing\s+validation",
            r"no\s+input\s+validation",
            r"need.*validation",
            r"unchecked\s+input",
        ],
        description="Missing input validation should be added",
    ),
    DeviationRule(
        name="critical_auth",
        deviation_type=DeviationType.MISSING_CRITICAL,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"missing\s+auth",
            r"no\s+authentication",
            r"unauthorized\s+access",
            r"need.*auth.*check",
        ],
        description="Missing auth checks should be added",
    ),

    # Rule 3: Blocking issues → AUTO_FIX
    DeviationRule(
        name="blocking_dependency",
        deviation_type=DeviationType.BLOCKING,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"missing\s+dependency",
            r"module\s+not\s+found",
            r"import\s+error",
            r"cannot\s+find\s+module",
            r"no\s+module\s+named",
        ],
        description="Missing dependencies should be added",
    ),
    DeviationRule(
        name="blocking_import",
        deviation_type=DeviationType.BLOCKING,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"wrong\s+import",
            r"incorrect\s+import",
            r"import\s+path",
            r"circular\s+import",
        ],
        description="Import issues should be fixed",
    ),
    DeviationRule(
        name="blocking_config",
        deviation_type=DeviationType.BLOCKING,
        action=DeviationAction.AUTO_FIX,
        patterns=[
            r"config\s+error",
            r"missing\s+config",
            r"invalid\s+config",
            r"environment\s+variable",
        ],
        description="Configuration errors should be fixed",
    ),
]


def classify_deviation(
    description: str,
    context: str = "",
) -> Tuple[Optional[DeviationRule], DeviationAction]:
    """Classify a deviation and determine the action.

    Args:
        description: Description of the deviation
        context: Additional context (optional)

    Returns:
        Tuple of (matching rule, action to take)
    """
    combined = f"{description} {context}".lower()

    # Check rules in order (architectural first to ensure they take priority)
    for rule in DEVIATION_RULES:
        for pattern in rule.patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return rule, rule.action

    # Default: treat as auto-fix if unclear
    return None, DeviationAction.AUTO_FIX


def should_auto_fix(description: str, context: str = "") -> bool:
    """Check if a deviation should be auto-fixed.

    Args:
        description: Description of the deviation
        context: Additional context

    Returns:
        True if should auto-fix
    """
    _, action = classify_deviation(description, context)
    return action == DeviationAction.AUTO_FIX


def should_checkpoint(description: str, context: str = "") -> bool:
    """Check if a deviation requires a checkpoint.

    Args:
        description: Description of the deviation
        context: Additional context

    Returns:
        True if should checkpoint
    """
    _, action = classify_deviation(description, context)
    return action == DeviationAction.CHECKPOINT


@dataclass
class DeviationRecord:
    """Record of a deviation that occurred during execution."""
    deviation_type: DeviationType
    description: str
    rule_matched: Optional[str]
    action_taken: DeviationAction
    files_affected: List[str]
    resolution: str = ""

    def to_dict(self):
        return {
            "type": self.deviation_type.value,
            "description": self.description,
            "rule": self.rule_matched,
            "action": self.action_taken.value,
            "files": self.files_affected,
            "resolution": self.resolution,
        }


def create_deviation_record(
    description: str,
    files_affected: List[str],
    resolution: str = "",
    context: str = "",
) -> DeviationRecord:
    """Create a deviation record for tracking in Summary.

    Args:
        description: What deviated
        files_affected: Files that were modified
        resolution: How it was resolved
        context: Additional context

    Returns:
        DeviationRecord
    """
    rule, action = classify_deviation(description, context)

    return DeviationRecord(
        deviation_type=rule.deviation_type if rule else DeviationType.BUG,
        description=description,
        rule_matched=rule.name if rule else None,
        action_taken=action,
        files_affected=files_affected,
        resolution=resolution,
    )


def format_deviation_for_summary(record: DeviationRecord) -> str:
    """Format a deviation record for the Summary file.

    Args:
        record: DeviationRecord

    Returns:
        Formatted string
    """
    action_icon = "🔧" if record.action_taken == DeviationAction.AUTO_FIX else "⏸️"
    return (
        f"- {action_icon} [{record.deviation_type.value}] {record.description}\n"
        f"  Files: {', '.join(record.files_affected)}\n"
        f"  Resolution: {record.resolution}"
    )
