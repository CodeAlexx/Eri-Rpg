"""
Three-level verification orchestration.

Level 1 (Existence): File exists, not empty
Level 2 (Substantive): Real code, not stub
Level 3 (Wired): Connected to the system
"""

import os
from datetime import datetime
from typing import List, Optional

from erirpg.models.plan import Plan, MustHaves
from erirpg.models.verification_models import (
    VerificationReport,
    VerificationStatus,
    TruthVerification,
    ArtifactVerification,
    LinkVerification,
    VerificationLevel,
)
from erirpg.verification.existence import verify_artifact_existence
from erirpg.verification.substantive import verify_artifact_substantive
from erirpg.verification.wired import verify_artifact_wired, verify_key_link


def verify_plan_must_haves(
    project_path: str,
    plan: Plan,
    level: VerificationLevel = VerificationLevel.WIRED,
) -> VerificationReport:
    """Verify all must-haves for a plan.

    Args:
        project_path: Path to project root
        plan: Plan to verify
        level: Verification level to perform (default: all levels)

    Returns:
        VerificationReport with results
    """
    report = VerificationReport(phase=plan.phase)

    # Verify truths (requires human verification for most)
    report.truths = verify_truths(plan.must_haves.truths)

    # Verify artifacts at requested level
    report.artifacts = verify_artifacts(
        project_path,
        plan.must_haves.artifacts,
        level,
    )

    # Verify key links (only at WIRED level)
    if level == VerificationLevel.WIRED:
        report.links = verify_key_links(
            project_path,
            plan.must_haves.key_links,
        )

    # Compute gaps
    _compute_gaps(report)

    # Compute overall status
    report.compute_status()

    return report


def verify_truths(truths: List) -> List[TruthVerification]:
    """Verify observable truths.

    Most truths require human verification. We can only auto-verify
    truths that have explicit test commands.

    Args:
        truths: List of Truth objects from plan

    Returns:
        List of TruthVerification results
    """
    results = []

    for truth in truths:
        verification = TruthVerification(
            truth_id=truth.id,
            description=truth.description,
        )

        # Check if truth has a verifiable_by method
        if truth.verifiable_by == "test":
            # Could run test here
            verification.mark_human_needed()
        elif truth.verifiable_by == "manual":
            verification.mark_human_needed()
        elif truth.verifiable_by == "observation":
            verification.mark_human_needed()
        else:
            # Default to human verification
            verification.mark_human_needed()

        results.append(verification)

    return results


def verify_artifacts(
    project_path: str,
    artifacts: List,
    level: VerificationLevel = VerificationLevel.WIRED,
) -> List[ArtifactVerification]:
    """Verify required artifacts at specified level.

    Args:
        project_path: Path to project root
        artifacts: List of Artifact objects from plan
        level: Verification level

    Returns:
        List of ArtifactVerification results
    """
    results = []

    for artifact in artifacts:
        verification = ArtifactVerification(
            path=artifact.path,
            provides=artifact.provides,
        )

        file_path = os.path.join(project_path, artifact.path)

        # Level 1: Existence
        verify_artifact_existence(file_path, verification)

        # Level 2: Substantive (if exists)
        if verification.exists and level.value in ("substantive", "wired"):
            verify_artifact_substantive(file_path, verification)

        # Level 3: Wired (if substantive)
        if not verification.is_stub and level == VerificationLevel.WIRED:
            verify_artifact_wired(project_path, artifact.path, verification)

        # Determine overall status
        if level == VerificationLevel.EXISTENCE:
            verification.status = "passed" if verification.exists and not verification.is_empty else "failed"
        elif level == VerificationLevel.SUBSTANTIVE:
            verification.status = "passed" if not verification.is_stub else "failed"
        else:  # WIRED
            verification.status = "passed" if verification.is_wired else "failed"

        verification.verified_at = datetime.now().isoformat()
        results.append(verification)

    return results


def verify_key_links(
    project_path: str,
    key_links: List,
) -> List[LinkVerification]:
    """Verify key links between components.

    Args:
        project_path: Path to project root
        key_links: List of KeyLink objects from plan

    Returns:
        List of LinkVerification results
    """
    results = []

    for link in key_links:
        verification = LinkVerification(
            from_component=link.from_component,
            to_component=link.to_component,
            via=link.via,
        )

        # Verify the connection
        verify_key_link(project_path, link, verification)

        verification.verified_at = datetime.now().isoformat()
        results.append(verification)

    return results


def _compute_gaps(report: VerificationReport) -> None:
    """Compute gaps from verification results."""
    gaps = []
    human_needed = []

    # Check truths
    for t in report.truths:
        if t.status == "failed":
            gaps.append(f"Truth not verified: {t.description}")
        elif t.status == "human_needed":
            human_needed.append(f"Truth needs human verification: {t.description}")

    # Check artifacts
    for a in report.artifacts:
        if not a.exists:
            gaps.append(f"Artifact missing: {a.path}")
        elif a.is_empty:
            gaps.append(f"Artifact is empty: {a.path}")
        elif a.is_stub:
            gaps.append(f"Artifact is stub: {a.path} - {', '.join(a.stub_indicators)}")
        elif not a.is_wired:
            gaps.append(f"Artifact not wired: {a.path}")

    # Check links
    for l in report.links:
        if not l.connected:
            gaps.append(f"Link not verified: {l.from_component} → {l.to_component} via {l.via}")

    report.gaps = gaps
    report.human_verification_needed = human_needed


def quick_verify(
    project_path: str,
    files: List[str],
    level: VerificationLevel = VerificationLevel.SUBSTANTIVE,
) -> dict:
    """Quick verification of a list of files.

    Useful for verifying files after edits.

    Args:
        project_path: Path to project root
        files: List of file paths (relative to project)
        level: Verification level

    Returns:
        Dict with results per file
    """
    results = {}

    for file_path in files:
        full_path = os.path.join(project_path, file_path)

        result = {
            "exists": os.path.exists(full_path),
            "is_empty": True,
            "line_count": 0,
            "is_stub": True,
            "passed": False,
        }

        if result["exists"]:
            with open(full_path, "r", errors="replace") as f:
                content = f.read()

            result["is_empty"] = len(content.strip()) == 0
            result["line_count"] = len(content.split("\n"))

            if not result["is_empty"]:
                from erirpg.verification.substantive import is_stub
                result["is_stub"] = is_stub(content)

        # Determine if passed
        if level == VerificationLevel.EXISTENCE:
            result["passed"] = result["exists"] and not result["is_empty"]
        else:
            result["passed"] = result["exists"] and not result["is_stub"]

        results[file_path] = result

    return results
