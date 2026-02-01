"""
Library modules for clone-behavior command.

Provides:
- behavior_extractor: AST-based extraction of code behavior
- file_parity: File-level parity tracking between source and target
- behavior_verifier: Automated verification of implementation
"""

from .behavior_extractor import (
    BehaviorExtractor,
    ExtractedModule,
    ExtractedClass,
    ExtractedFunction,
    extract_module_behavior,
    generate_behavior_markdown,
)

from .file_parity import (
    FileParityReport,
    compute_file_parity,
    compute_project_parity,
    generate_parity_summary,
    format_parity_table,
    save_parity_state,
    load_parity_state,
)

from .behavior_verifier import (
    BehaviorVerifier,
    VerifyStatus,
    VerifyResult,
    FileVerificationReport,
    ModuleVerificationReport,
    verify_module_behavior,
    format_verification_table,
)

__all__ = [
    # Extractor
    "BehaviorExtractor",
    "ExtractedModule",
    "ExtractedClass",
    "ExtractedFunction",
    "extract_module_behavior",
    "generate_behavior_markdown",
    # Parity
    "FileParityReport",
    "compute_file_parity",
    "compute_project_parity",
    "generate_parity_summary",
    "format_parity_table",
    "save_parity_state",
    "load_parity_state",
    # Verifier
    "BehaviorVerifier",
    "VerifyStatus",
    "VerifyResult",
    "FileVerificationReport",
    "ModuleVerificationReport",
    "verify_module_behavior",
    "format_verification_table",
]
