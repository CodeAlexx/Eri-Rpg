"""
Level 2 Verification: Substantive.

Checks:
- File contains real code, not stubs
- Code has meaningful implementation
- No placeholder content
"""

import re
from typing import List, Tuple

from erirpg.models.verification_models import ArtifactVerification


# Patterns that indicate stub code
STUB_PATTERNS = {
    # Explicit markers
    "todo": r"\bTODO\b",
    "fixme": r"\bFIXME\b",
    "placeholder": r"\bplaceholder\b",
    "not_implemented": r"\bNotImplementedError\b",
    "pass_only": r"^\s*(def|class)\s+\w+[^:]*:\s*\n\s+pass\s*$",

    # Empty returns
    "return_none": r"^\s*return\s*None?\s*$",
    "return_empty": r"^\s*return\s*['\"]['\"]?\s*$",
    "return_zero": r"^\s*return\s*0\s*$",
    "return_false": r"^\s*return\s*False\s*$",
    "return_empty_list": r"^\s*return\s*\[\]\s*$",
    "return_empty_dict": r"^\s*return\s*\{\}\s*$",

    # Console-only implementations
    "console_only": r"^\s*(print|console\.log)\s*\(['\"].*['\"].*\)\s*$",

    # Raise-only implementations
    "raise_only": r"^\s*raise\s+\w+Error\s*\(",

    # Comment-only bodies
    "comment_only": r"^\s*#.*$",

    # JavaScript/TypeScript stubs
    "js_todo": r"//\s*TODO",
    "js_throw": r"throw\s+new\s+Error\(['\"]Not implemented",
    "js_empty_return": r"return\s*;\s*$",
}

# Minimum thresholds for "real" code
MIN_MEANINGFUL_LINES = 5  # Non-comment, non-empty lines
MIN_FUNCTION_BODY_LINES = 2  # Lines inside function bodies


def is_stub(content: str) -> bool:
    """Check if content appears to be stub code.

    Args:
        content: File content

    Returns:
        True if content appears to be a stub
    """
    indicators, score = detect_stub_indicators(content)
    return score < 0.5  # Less than 50% substantive


def get_substantive_score(content: str) -> float:
    """Get a score for how "substantive" code is.

    Args:
        content: File content

    Returns:
        Score from 0.0 (pure stub) to 1.0 (fully substantive)
    """
    _, score = detect_stub_indicators(content)
    return score


def detect_stub_indicators(content: str) -> Tuple[List[str], float]:
    """Detect indicators that code is a stub.

    Args:
        content: File content

    Returns:
        Tuple of (list of indicators found, substantive score 0-1)
    """
    indicators = []
    lines = content.split("\n")

    # Count line types
    total_lines = len(lines)
    empty_lines = sum(1 for line in lines if not line.strip())
    comment_lines = sum(1 for line in lines if _is_comment_line(line))
    code_lines = total_lines - empty_lines - comment_lines

    # Check for explicit stub markers
    for name, pattern in STUB_PATTERNS.items():
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            indicators.append(name)

    # Check line counts
    if code_lines < MIN_MEANINGFUL_LINES:
        indicators.append(f"too_few_code_lines ({code_lines})")

    # Check function bodies
    function_issues = _check_function_bodies(content)
    indicators.extend(function_issues)

    # Calculate score
    # Start at 1.0, subtract for each issue
    score = 1.0

    # Severe indicators (each subtracts 0.3)
    severe = ["not_implemented", "placeholder", "pass_only", "raise_only"]
    for indicator in indicators:
        if any(s in indicator for s in severe):
            score -= 0.3

    # Moderate indicators (each subtracts 0.15)
    moderate = ["todo", "fixme", "console_only", "empty_function"]
    for indicator in indicators:
        if any(m in indicator for m in moderate):
            score -= 0.15

    # Minor indicators (each subtracts 0.05)
    for indicator in indicators:
        if indicator not in severe and not any(m in indicator for m in moderate):
            score -= 0.05

    # Line count factor
    if code_lines > 0:
        line_factor = min(1.0, code_lines / 20)  # Full credit at 20+ lines
        score = score * 0.7 + line_factor * 0.3

    return indicators, max(0.0, min(1.0, score))


def _is_comment_line(line: str) -> bool:
    """Check if a line is a comment."""
    stripped = line.strip()
    return (
        stripped.startswith("#") or
        stripped.startswith("//") or
        stripped.startswith("/*") or
        stripped.startswith("*") or
        stripped.startswith("'''") or
        stripped.startswith('"""')
    )


def _check_function_bodies(content: str) -> List[str]:
    """Check function bodies for stub patterns.

    Returns list of issues found.
    """
    issues = []

    # Python function pattern
    py_func_pattern = r"def\s+(\w+)\s*\([^)]*\)\s*(?:->[^:]+)?:\s*\n((?:\s+.*\n)*)"
    for match in re.finditer(py_func_pattern, content):
        func_name = match.group(1)
        body = match.group(2)

        body_lines = [l for l in body.split("\n") if l.strip() and not _is_comment_line(l)]

        if len(body_lines) == 0:
            issues.append(f"empty_function:{func_name}")
        elif len(body_lines) == 1:
            single_line = body_lines[0].strip()
            if single_line == "pass":
                issues.append(f"pass_only_function:{func_name}")
            elif single_line.startswith("return None") or single_line == "return":
                issues.append(f"return_none_function:{func_name}")
            elif "NotImplementedError" in single_line:
                issues.append(f"not_implemented_function:{func_name}")

    # JavaScript function pattern
    js_func_pattern = r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)\s*\{([^}]*)\}"
    for match in re.finditer(js_func_pattern, content):
        func_name = match.group(1) or match.group(2)
        body = match.group(3)

        body_lines = [l for l in body.split("\n") if l.strip() and not _is_comment_line(l)]

        if len(body_lines) == 0:
            issues.append(f"empty_function:{func_name}")
        elif len(body_lines) == 1:
            single_line = body_lines[0].strip()
            if "throw" in single_line and "Not implemented" in single_line:
                issues.append(f"not_implemented_function:{func_name}")

    return issues


def verify_artifact_substantive(
    file_path: str,
    verification: ArtifactVerification,
) -> None:
    """Verify artifact is substantive and update verification result.

    Args:
        file_path: Absolute path to file
        verification: ArtifactVerification to update
    """
    try:
        with open(file_path, "r", errors="replace") as f:
            content = f.read()
    except Exception:
        verification.is_stub = True
        verification.stub_indicators = ["unreadable"]
        verification.substantive_score = 0.0
        return

    indicators, score = detect_stub_indicators(content)

    verification.is_stub = score < 0.5
    verification.stub_indicators = indicators
    verification.substantive_score = score
