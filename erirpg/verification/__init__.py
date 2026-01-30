"""
EriRPG Three-Level Verification System.

Three levels of verification:
1. Existence - File exists, not empty
2. Substantive - Real code, not stub
3. Wired - Connected to the system

Usage:
    from erirpg.verification import verify_plan_must_haves

    report = verify_plan_must_haves(project_path, plan)
    if report.status == VerificationStatus.PASSED:
        print("All checks passed!")
    else:
        print(report.format_display())
"""

from erirpg.verification.levels import (
    verify_plan_must_haves,
    verify_truths,
    verify_artifacts,
    verify_key_links,
)
from erirpg.verification.existence import (
    check_file_exists,
    check_file_not_empty,
    verify_artifact_existence,
)
from erirpg.verification.substantive import (
    is_stub,
    get_substantive_score,
    verify_artifact_substantive,
    STUB_PATTERNS,
)
from erirpg.verification.wired import (
    find_imports_of,
    find_usages_of,
    verify_key_link,
    verify_artifact_wired,
)
from erirpg.verification.stub_detection import (
    detect_stub_indicators,
    StubIndicator,
)
from erirpg.verification.key_links import (
    KEY_LINK_PATTERNS,
    detect_link_type,
    verify_component_connection,
)

__all__ = [
    # Main API
    "verify_plan_must_haves",
    "verify_truths",
    "verify_artifacts",
    "verify_key_links",
    # Existence
    "check_file_exists",
    "check_file_not_empty",
    "verify_artifact_existence",
    # Substantive
    "is_stub",
    "get_substantive_score",
    "verify_artifact_substantive",
    "STUB_PATTERNS",
    # Wired
    "find_imports_of",
    "find_usages_of",
    "verify_key_link",
    "verify_artifact_wired",
    # Stub detection
    "detect_stub_indicators",
    "StubIndicator",
    # Key links
    "KEY_LINK_PATTERNS",
    "detect_link_type",
    "verify_component_connection",
]
