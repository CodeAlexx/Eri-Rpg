"""
Three-Level Code Verifier for ERI-Coder.

Verifies that code ACHIEVES goals, not just that tasks were COMPLETED.

Three Levels:
1. Existence - Does the file exist?
2. Substantive - Has real implementation (not stub)?
3. Wired - Connected to the system?

Usage:
    from erirpg.code_verifier import verify_artifact, verify_must_haves

    result = verify_artifact("src/auth.py", min_lines=30)
    results = verify_must_haves(must_haves, project_path)
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class VerificationLevel(Enum):
    """Verification levels."""
    EXISTENCE = 1
    SUBSTANTIVE = 2
    WIRED = 3


class VerificationStatus(Enum):
    """Status of a verification check."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


# Stub detection patterns
STUB_PATTERNS = [
    # Comment-based stubs
    r"TODO|FIXME|XXX|HACK|PLACEHOLDER|NOT IMPLEMENTED",
    # Placeholder text
    r"placeholder|coming soon|will be here|lorem ipsum",
    # Empty implementations (Python)
    r"^\s*pass\s*$",
    r"^\s*\.\.\.\s*$",
    r"return None\s*$",
    r"return \{\}\s*$",
    r"return \[\]\s*$",
    # Empty implementations (JS/TS)
    r"return null;?\s*$",
    r"return \{\};?\s*$",
    r"return \[\];?\s*$",
    # Throw not implemented
    r"throw.*not implemented",
    r"raise NotImplementedError",
    # Console-only implementations
    r"console\.log.*only",
    r"print.*stub",
]


@dataclass
class ArtifactCheck:
    """Result of checking a single artifact."""
    path: str
    exists: bool
    line_count: int = 0
    min_lines_required: int = 0
    is_substantive: bool = False
    is_wired: bool = False
    stub_matches: List[str] = field(default_factory=list)
    wiring_evidence: List[str] = field(default_factory=list)
    level_1_status: VerificationStatus = VerificationStatus.SKIPPED
    level_2_status: VerificationStatus = VerificationStatus.SKIPPED
    level_3_status: VerificationStatus = VerificationStatus.SKIPPED

    @property
    def overall_status(self) -> VerificationStatus:
        """Get overall status based on all levels."""
        if self.level_1_status == VerificationStatus.FAILED:
            return VerificationStatus.FAILED
        if self.level_2_status == VerificationStatus.FAILED:
            return VerificationStatus.FAILED
        if self.level_3_status == VerificationStatus.FAILED:
            return VerificationStatus.WARNING  # Wiring failure is warning
        if self.level_3_status == VerificationStatus.WARNING:
            return VerificationStatus.WARNING
        return VerificationStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "line_count": self.line_count,
            "min_lines_required": self.min_lines_required,
            "is_substantive": self.is_substantive,
            "is_wired": self.is_wired,
            "stub_matches": self.stub_matches,
            "wiring_evidence": self.wiring_evidence,
            "level_1": self.level_1_status.value,
            "level_2": self.level_2_status.value,
            "level_3": self.level_3_status.value,
            "overall": self.overall_status.value,
        }


@dataclass
class TruthCheck:
    """Result of checking an observable truth."""
    truth_id: str
    description: str
    status: VerificationStatus
    evidence: str
    artifacts_checked: List[str] = field(default_factory=list)
    key_links_checked: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "description": self.description,
            "status": self.status.value,
            "evidence": self.evidence,
            "artifacts_checked": self.artifacts_checked,
            "key_links_checked": self.key_links_checked,
        }


@dataclass
class KeyLinkCheck:
    """Result of checking a key link (wiring)."""
    from_component: str
    to_component: str
    via: str
    status: VerificationStatus
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_component,
            "to": self.to_component,
            "via": self.via,
            "status": self.status.value,
            "evidence": self.evidence,
        }


@dataclass
class VerificationReport:
    """Complete verification report for a phase."""
    phase: str
    verified_at: str
    status: str  # passed, gaps_found, human_needed
    score: Tuple[int, int]  # (verified, total)
    truth_checks: List[TruthCheck] = field(default_factory=list)
    artifact_checks: List[ArtifactCheck] = field(default_factory=list)
    key_link_checks: List[KeyLinkCheck] = field(default_factory=list)
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    human_verification_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "verified_at": self.verified_at,
            "status": self.status,
            "score": f"{self.score[0]}/{self.score[1]}",
            "truth_checks": [t.to_dict() for t in self.truth_checks],
            "artifact_checks": [a.to_dict() for a in self.artifact_checks],
            "key_link_checks": [k.to_dict() for k in self.key_link_checks],
            "gaps": self.gaps,
            "human_verification_needed": self.human_verification_needed,
        }


def check_file_exists(path: str, project_path: str = ".") -> bool:
    """Level 1: Check if file exists."""
    full_path = Path(project_path) / path
    return full_path.exists() and full_path.is_file()


def count_lines(path: str, project_path: str = ".") -> int:
    """Count non-empty, non-comment lines in a file."""
    full_path = Path(project_path) / path
    if not full_path.exists():
        return 0

    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        # Count non-empty, non-comment lines
        count = 0
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Handle multiline comments
            if "'''" in stripped or '"""' in stripped:
                in_multiline_comment = not in_multiline_comment
                continue
            if in_multiline_comment:
                continue

            # Skip single-line comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            count += 1

        return count
    except Exception:
        return 0


def detect_stubs(path: str, project_path: str = ".") -> List[str]:
    """Level 2: Detect stub patterns in a file."""
    full_path = Path(project_path) / path
    if not full_path.exists():
        return []

    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        matches = []

        for pattern in STUB_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for match in regex.finditer(content):
                # Get the line containing the match
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end].strip()

                # Add line number
                line_num = content[:match.start()].count("\n") + 1
                matches.append(f"L{line_num}: {line[:60]}...")

        return matches[:10]  # Limit to 10 matches
    except Exception:
        return []


def check_wiring(
    from_path: str,
    to_path: str,
    via: str,
    project_path: str = "."
) -> Tuple[bool, str]:
    """Level 3: Check if two components are wired together.

    Args:
        from_path: Path to the component that should import/use
        to_path: Path to the component being imported/used
        via: Expected mechanism (import, fetch, etc.)
        project_path: Project root

    Returns:
        Tuple of (is_wired, evidence)
    """
    from_full = Path(project_path) / from_path
    if not from_full.exists():
        return False, f"Source file {from_path} does not exist"

    try:
        content = from_full.read_text(encoding="utf-8", errors="ignore")

        # Extract the module/component name from to_path
        to_name = Path(to_path).stem
        to_name_variants = [
            to_name,
            to_name.replace("_", "-"),
            to_name.replace("-", "_"),
            to_name.replace("_", ""),
        ]

        # Check based on 'via' mechanism
        via_lower = via.lower()

        if "import" in via_lower:
            # Check for import statements
            for variant in to_name_variants:
                patterns = [
                    rf"import.*{variant}",
                    rf"from.*{variant}.*import",
                    rf"require\(['\"].*{variant}",
                    rf"from ['\"].*{variant}",
                ]
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        match = re.search(pattern, content, re.IGNORECASE)
                        return True, f"Found: {match.group()}"

        elif "fetch" in via_lower or "api" in via_lower:
            # Check for fetch/axios/request calls
            patterns = [
                r"fetch\(['\"]",
                r"axios\.",
                r"\.get\(['\"]",
                r"\.post\(['\"]",
                r"request\(",
            ]
            for pattern in patterns:
                if re.search(pattern, content):
                    match = re.search(pattern, content)
                    return True, f"Found API call: {match.group()}"

        elif "call" in via_lower or "invoke" in via_lower:
            # Check for function calls
            for variant in to_name_variants:
                if re.search(rf"{variant}\s*\(", content, re.IGNORECASE):
                    return True, f"Found call to {variant}()"

        elif "use" in via_lower:
            # Generic usage check
            for variant in to_name_variants:
                if variant.lower() in content.lower():
                    return True, f"Found reference to {variant}"

        # Fallback: just check if to_name appears in content
        for variant in to_name_variants:
            if variant in content:
                return True, f"Found reference to {variant}"

        return False, f"No reference to {to_name} found in {from_path}"

    except Exception as e:
        return False, f"Error checking wiring: {e}"


def verify_artifact(
    path: str,
    min_lines: int = 10,
    project_path: str = "."
) -> ArtifactCheck:
    """Verify a single artifact through all three levels.

    Args:
        path: Path to the artifact (relative to project)
        min_lines: Minimum lines for substantive check
        project_path: Project root

    Returns:
        ArtifactCheck with results
    """
    check = ArtifactCheck(
        path=path,
        exists=False,
        min_lines_required=min_lines,
    )

    # Level 1: Existence
    check.exists = check_file_exists(path, project_path)
    if check.exists:
        check.level_1_status = VerificationStatus.PASSED
    else:
        check.level_1_status = VerificationStatus.FAILED
        return check  # Can't continue without file

    # Level 2: Substantive
    check.line_count = count_lines(path, project_path)
    check.stub_matches = detect_stubs(path, project_path)

    if check.line_count >= min_lines and not check.stub_matches:
        check.is_substantive = True
        check.level_2_status = VerificationStatus.PASSED
    elif check.line_count >= min_lines and check.stub_matches:
        check.is_substantive = False
        check.level_2_status = VerificationStatus.WARNING
    else:
        check.is_substantive = False
        check.level_2_status = VerificationStatus.FAILED

    # Level 3: Wired (checked separately with key_links)
    check.level_3_status = VerificationStatus.SKIPPED

    return check


def verify_key_link(
    from_component: str,
    to_component: str,
    via: str,
    project_path: str = "."
) -> KeyLinkCheck:
    """Verify a key link between components.

    Args:
        from_component: Path to source component
        to_component: Path to target component (or API endpoint)
        via: Connection mechanism
        project_path: Project root

    Returns:
        KeyLinkCheck with results
    """
    is_wired, evidence = check_wiring(from_component, to_component, via, project_path)

    return KeyLinkCheck(
        from_component=from_component,
        to_component=to_component,
        via=via,
        status=VerificationStatus.PASSED if is_wired else VerificationStatus.FAILED,
        evidence=evidence,
    )


def verify_must_haves(
    must_haves: Dict[str, Any],
    project_path: str = ".",
    phase: str = "unknown"
) -> VerificationReport:
    """Verify all must_haves for a phase.

    Args:
        must_haves: Dict with truths, artifacts, key_links
        project_path: Project root
        phase: Phase name for report

    Returns:
        VerificationReport with all results
    """
    report = VerificationReport(
        phase=phase,
        verified_at=datetime.now().isoformat(),
        status="passed",
        score=(0, 0),
    )

    total_checks = 0
    passed_checks = 0

    # Verify artifacts
    artifacts = must_haves.get("artifacts", [])
    for artifact in artifacts:
        path = artifact.get("path", "")
        min_lines = artifact.get("min_lines", 10)

        check = verify_artifact(path, min_lines, project_path)
        report.artifact_checks.append(check)

        total_checks += 1
        if check.overall_status == VerificationStatus.PASSED:
            passed_checks += 1
        elif check.overall_status == VerificationStatus.FAILED:
            report.gaps.append({
                "type": "artifact",
                "path": path,
                "issue": "Missing or stub",
                "details": check.to_dict(),
            })

    # Verify key links
    key_links = must_haves.get("key_links", [])
    for link in key_links:
        from_comp = link.get("from", "")
        to_comp = link.get("to", "")
        via = link.get("via", "")

        check = verify_key_link(from_comp, to_comp, via, project_path)
        report.key_link_checks.append(check)

        total_checks += 1
        if check.status == VerificationStatus.PASSED:
            passed_checks += 1
        else:
            report.gaps.append({
                "type": "key_link",
                "from": from_comp,
                "to": to_comp,
                "via": via,
                "issue": "Not wired",
                "evidence": check.evidence,
            })

    # Check truths (based on artifact and link results)
    truths = must_haves.get("truths", [])
    for i, truth in enumerate(truths):
        truth_desc = truth.get("description", truth) if isinstance(truth, dict) else truth
        truth_id = truth.get("id", f"T{i+1}") if isinstance(truth, dict) else f"T{i+1}"

        # A truth passes if related artifacts and links pass
        # This is a simplified check - could be enhanced
        truth_check = TruthCheck(
            truth_id=truth_id,
            description=truth_desc,
            status=VerificationStatus.PASSED,
            evidence="Inferred from artifact/link checks",
        )

        total_checks += 1

        # If we have gaps, some truths may be affected
        if report.gaps:
            # Simple heuristic: if any gap exists, mark truths as needing human verification
            truth_check.status = VerificationStatus.WARNING
            truth_check.evidence = "Requires manual verification due to gaps"
            report.human_verification_needed.append(truth_desc)
        else:
            passed_checks += 1

        report.truth_checks.append(truth_check)

    # Set overall status
    report.score = (passed_checks, total_checks)

    if report.gaps:
        report.status = "gaps_found"
    elif report.human_verification_needed:
        report.status = "human_needed"
    else:
        report.status = "passed"

    return report


def format_verification_report(report: VerificationReport) -> str:
    """Format verification report for display.

    Args:
        report: The verification report

    Returns:
        Formatted string
    """
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append(f" VERIFICATION REPORT: Phase {report.phase}")
    lines.append("=" * 60)
    lines.append("")

    # Status
    status_icons = {
        "passed": "✅",
        "gaps_found": "❌",
        "human_needed": "👤",
    }
    icon = status_icons.get(report.status, "?")
    lines.append(f"Status: {icon} {report.status.upper()}")
    lines.append(f"Score: {report.score[0]}/{report.score[1]} checks passed")
    lines.append(f"Verified: {report.verified_at}")
    lines.append("")

    # Artifact checks
    if report.artifact_checks:
        lines.append("-" * 60)
        lines.append("ARTIFACT CHECKS")
        lines.append("-" * 60)
        for check in report.artifact_checks:
            status_icon = {
                VerificationStatus.PASSED: "✅",
                VerificationStatus.FAILED: "❌",
                VerificationStatus.WARNING: "⚠️",
            }.get(check.overall_status, "?")

            lines.append(f"{status_icon} {check.path}")
            lines.append(f"   L1 Exists: {check.level_1_status.value}")
            lines.append(f"   L2 Substantive: {check.level_2_status.value} ({check.line_count} lines)")
            if check.stub_matches:
                lines.append(f"   Stubs found: {len(check.stub_matches)}")
            lines.append(f"   L3 Wired: {check.level_3_status.value}")
        lines.append("")

    # Key link checks
    if report.key_link_checks:
        lines.append("-" * 60)
        lines.append("KEY LINK CHECKS")
        lines.append("-" * 60)
        for check in report.key_link_checks:
            status_icon = "✅" if check.status == VerificationStatus.PASSED else "❌"
            lines.append(f"{status_icon} {check.from_component} → {check.to_component}")
            lines.append(f"   Via: {check.via}")
            lines.append(f"   Evidence: {check.evidence}")
        lines.append("")

    # Truth checks
    if report.truth_checks:
        lines.append("-" * 60)
        lines.append("TRUTH CHECKS")
        lines.append("-" * 60)
        for check in report.truth_checks:
            status_icon = {
                VerificationStatus.PASSED: "✅",
                VerificationStatus.FAILED: "❌",
                VerificationStatus.WARNING: "⚠️",
            }.get(check.status, "?")
            lines.append(f"{status_icon} {check.truth_id}: {check.description}")
            lines.append(f"   Evidence: {check.evidence}")
        lines.append("")

    # Gaps
    if report.gaps:
        lines.append("-" * 60)
        lines.append("GAPS FOUND")
        lines.append("-" * 60)
        for i, gap in enumerate(report.gaps, 1):
            lines.append(f"Gap {i}: {gap.get('type', 'unknown')}")
            if gap.get("path"):
                lines.append(f"   Path: {gap['path']}")
            if gap.get("from"):
                lines.append(f"   Link: {gap['from']} → {gap['to']}")
            lines.append(f"   Issue: {gap.get('issue', 'Unknown')}")
        lines.append("")

    # Human verification needed
    if report.human_verification_needed:
        lines.append("-" * 60)
        lines.append("REQUIRES MANUAL VERIFICATION")
        lines.append("-" * 60)
        for item in report.human_verification_needed:
            lines.append(f"  • {item}")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
