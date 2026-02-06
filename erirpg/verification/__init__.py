"""
EriRPG Verification System.

Two subsystems:
1. Three-Level Structural Verification (existence → substantive → wired)
2. Command Runner Verification (lint, test, type-check execution)

Usage (structural):
    from erirpg.verification import verify_plan_must_haves

    report = verify_plan_must_haves(project_path, plan)
    if report.status == VerificationStatus.PASSED:
        print("All checks passed!")

Usage (command runner):
    from erirpg.verification import Verifier, VerificationConfig

    verifier = Verifier(config)
    result = verifier.run_step_verification(step)
"""

# Three-level structural verification
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

# Command runner verification (moved from verification.py monolith)
from erirpg.verification.runner import (
    VerificationStatus,
    VerificationCommand,
    CommandResult,
    VerificationResult,
    VerificationConfig,
    Verifier,
    SmartVerifier,
    save_verification_result,
    load_verification_result,
    list_verification_results,
    format_verification_summary,
    load_verification_config,
    save_verification_config,
    get_default_python_config,
    get_default_node_config,
    find_relevant_tests,
    build_smart_test_command,
    BreakingChange,
    signatures_compatible,
    validate_interface_contracts,
    format_breaking_changes,
)

__all__ = [
    # Structural verification
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
    # Command runner
    "VerificationStatus",
    "VerificationCommand",
    "CommandResult",
    "VerificationResult",
    "VerificationConfig",
    "Verifier",
    "SmartVerifier",
    "save_verification_result",
    "load_verification_result",
    "list_verification_results",
    "format_verification_summary",
    "load_verification_config",
    "save_verification_config",
    "get_default_python_config",
    "get_default_node_config",
    "find_relevant_tests",
    "build_smart_test_command",
    "BreakingChange",
    "signatures_compatible",
    "validate_interface_contracts",
    "format_breaking_changes",
]
