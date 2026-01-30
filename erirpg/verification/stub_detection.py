"""
Stub detection patterns and utilities.

Detects common stub patterns in code that indicate
incomplete implementations.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class StubSeverity(Enum):
    """Severity of stub indicator."""
    CRITICAL = "critical"  # Definitely a stub
    HIGH = "high"          # Very likely a stub
    MEDIUM = "medium"      # Possibly a stub
    LOW = "low"           # Minor indicator


@dataclass
class StubIndicator:
    """A detected stub indicator."""
    name: str
    severity: StubSeverity
    line_number: int
    line_content: str
    description: str


# Pattern definitions with severity
STUB_PATTERN_DEFS = [
    # Critical - definitely stubs
    ("NotImplementedError", StubSeverity.CRITICAL, r"raise\s+NotImplementedError"),
    ("pass_only_function", StubSeverity.CRITICAL, r"^\s*def\s+\w+[^:]*:\s*\n\s+pass\s*$"),
    ("TODO_marker", StubSeverity.CRITICAL, r"\bTODO\b.*(?:implement|finish|complete)"),
    ("not_implemented_error_js", StubSeverity.CRITICAL, r"throw\s+new\s+Error\(['\"]Not\s+implemented"),

    # High - very likely stubs
    ("FIXME_marker", StubSeverity.HIGH, r"\bFIXME\b"),
    ("placeholder_text", StubSeverity.HIGH, r"\bplaceholder\b"),
    ("stub_comment", StubSeverity.HIGH, r"#\s*stub|//\s*stub"),
    ("todo_generic", StubSeverity.HIGH, r"\bTODO\b"),
    ("empty_implementation", StubSeverity.HIGH, r"^\s*{\s*}\s*$"),

    # Medium - possibly stubs
    ("return_none_only", StubSeverity.MEDIUM, r"^\s*return\s*None?\s*$"),
    ("return_empty_string", StubSeverity.MEDIUM, r"^\s*return\s*['\"]['\"]?\s*$"),
    ("return_zero", StubSeverity.MEDIUM, r"^\s*return\s*0\s*$"),
    ("return_false", StubSeverity.MEDIUM, r"^\s*return\s*False\s*$"),
    ("return_empty_list", StubSeverity.MEDIUM, r"^\s*return\s*\[\]\s*$"),
    ("return_empty_dict", StubSeverity.MEDIUM, r"^\s*return\s*\{\}\s*$"),
    ("console_log_only", StubSeverity.MEDIUM, r"^\s*console\.log\s*\("),
    ("print_only", StubSeverity.MEDIUM, r"^\s*print\s*\("),

    # Low - minor indicators
    ("xxx_marker", StubSeverity.LOW, r"\bXXX\b"),
    ("hack_marker", StubSeverity.LOW, r"\bHACK\b"),
    ("temp_marker", StubSeverity.LOW, r"\bTEMP\b"),
]


def detect_stub_indicators(content: str) -> List[StubIndicator]:
    """Detect all stub indicators in content.

    Args:
        content: File content

    Returns:
        List of StubIndicator objects
    """
    indicators = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for name, severity, pattern in STUB_PATTERN_DEFS:
            if re.search(pattern, line, re.IGNORECASE):
                indicators.append(StubIndicator(
                    name=name,
                    severity=severity,
                    line_number=i,
                    line_content=line.strip()[:80],  # Truncate long lines
                    description=_get_indicator_description(name),
                ))

    # Also check for function-level stubs
    indicators.extend(_detect_function_stubs(content))

    return indicators


def _get_indicator_description(name: str) -> str:
    """Get human-readable description for indicator."""
    descriptions = {
        "NotImplementedError": "Function raises NotImplementedError",
        "pass_only_function": "Function body is just 'pass'",
        "TODO_marker": "TODO marker indicates incomplete work",
        "not_implemented_error_js": "JavaScript throws 'Not implemented' error",
        "FIXME_marker": "FIXME marker indicates broken code",
        "placeholder_text": "Contains placeholder text",
        "stub_comment": "Explicit stub comment",
        "todo_generic": "Contains TODO marker",
        "empty_implementation": "Empty implementation block",
        "return_none_only": "Returns None without doing work",
        "return_empty_string": "Returns empty string without doing work",
        "return_zero": "Returns 0 without doing work",
        "return_false": "Returns False without doing work",
        "return_empty_list": "Returns empty list without doing work",
        "return_empty_dict": "Returns empty dict without doing work",
        "console_log_only": "Only logs to console, no real implementation",
        "print_only": "Only prints, no real implementation",
        "xxx_marker": "XXX marker indicates temporary code",
        "hack_marker": "HACK marker indicates workaround",
        "temp_marker": "TEMP marker indicates temporary code",
    }
    return descriptions.get(name, f"Stub indicator: {name}")


def _detect_function_stubs(content: str) -> List[StubIndicator]:
    """Detect function-level stub patterns.

    Returns indicators for functions that are stubs.
    """
    indicators = []

    # Python functions
    py_pattern = r"(def\s+(\w+)\s*\([^)]*\)\s*(?:->[^:]+)?:)\s*\n((?:\s+.*\n)*)"
    for match in re.finditer(py_pattern, content):
        func_def = match.group(1)
        func_name = match.group(2)
        body = match.group(3)

        # Get line number
        line_num = content[:match.start()].count("\n") + 1

        # Analyze body
        body_lines = [l.strip() for l in body.split("\n") if l.strip()]

        if not body_lines:
            indicators.append(StubIndicator(
                name="empty_function",
                severity=StubSeverity.CRITICAL,
                line_number=line_num,
                line_content=func_def.strip(),
                description=f"Function '{func_name}' has empty body",
            ))
        elif len(body_lines) == 1:
            single = body_lines[0]
            if single == "pass":
                indicators.append(StubIndicator(
                    name="pass_only",
                    severity=StubSeverity.CRITICAL,
                    line_number=line_num,
                    line_content=func_def.strip(),
                    description=f"Function '{func_name}' only contains 'pass'",
                ))
            elif single.startswith("return None") or single == "return":
                indicators.append(StubIndicator(
                    name="return_none_function",
                    severity=StubSeverity.MEDIUM,
                    line_number=line_num,
                    line_content=func_def.strip(),
                    description=f"Function '{func_name}' only returns None",
                ))
            elif "NotImplementedError" in single:
                indicators.append(StubIndicator(
                    name="not_implemented_function",
                    severity=StubSeverity.CRITICAL,
                    line_number=line_num,
                    line_content=func_def.strip(),
                    description=f"Function '{func_name}' raises NotImplementedError",
                ))

    return indicators


def calculate_stub_score(indicators: List[StubIndicator]) -> float:
    """Calculate overall stub score from indicators.

    Args:
        indicators: List of detected indicators

    Returns:
        Score from 0.0 (definitely stub) to 1.0 (not a stub)
    """
    if not indicators:
        return 1.0

    # Weight by severity
    severity_weights = {
        StubSeverity.CRITICAL: 0.4,
        StubSeverity.HIGH: 0.2,
        StubSeverity.MEDIUM: 0.1,
        StubSeverity.LOW: 0.05,
    }

    total_penalty = sum(severity_weights[i.severity] for i in indicators)
    return max(0.0, 1.0 - total_penalty)


def format_stub_report(indicators: List[StubIndicator]) -> str:
    """Format stub indicators as a report.

    Args:
        indicators: List of detected indicators

    Returns:
        Formatted report string
    """
    if not indicators:
        return "No stub indicators detected."

    lines = [
        "Stub Indicators Detected",
        "=" * 40,
    ]

    # Group by severity
    by_severity = {}
    for indicator in indicators:
        sev = indicator.severity.value
        if sev not in by_severity:
            by_severity[sev] = []
        by_severity[sev].append(indicator)

    severity_icons = {
        "critical": "🚫",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️",
    }

    for severity in ["critical", "high", "medium", "low"]:
        if severity in by_severity:
            lines.append(f"\n{severity_icons[severity]} {severity.upper()}:")
            for indicator in by_severity[severity]:
                lines.append(f"  Line {indicator.line_number}: {indicator.description}")
                lines.append(f"    {indicator.line_content}")

    score = calculate_stub_score(indicators)
    lines.append(f"\nSubstantive Score: {score * 100:.1f}%")

    return "\n".join(lines)
