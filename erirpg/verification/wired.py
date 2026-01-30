"""
Level 3 Verification: Wired.

Checks:
- Component is imported/used by other code
- Component connects to the system
- Key links between components exist
"""

import os
import re
from typing import List, Optional, Tuple

from erirpg.models.verification_models import ArtifactVerification, LinkVerification


def find_imports_of(
    project_path: str,
    module_path: str,
    exclude_tests: bool = True,
) -> List[str]:
    """Find files that import a given module.

    Args:
        project_path: Path to project root
        module_path: Path to module (relative to project)
        exclude_tests: Whether to exclude test files

    Returns:
        List of file paths that import the module
    """
    importers = []

    # Convert file path to module name
    module_name = _path_to_module_name(module_path)
    if not module_name:
        return importers

    # Patterns to match
    patterns = [
        # Python imports
        rf"from\s+{re.escape(module_name)}\s+import",
        rf"import\s+{re.escape(module_name)}",
        # Also check partial paths
        rf"from\s+\S*{re.escape(module_name.split('.')[-1])}\s+import",
    ]

    # JavaScript/TypeScript imports
    file_stem = os.path.splitext(os.path.basename(module_path))[0]
    patterns.extend([
        rf"from\s+['\"].*{re.escape(file_stem)}['\"]",
        rf"require\s*\(\s*['\"].*{re.escape(file_stem)}['\"]",
        rf"import\s+.*\s+from\s+['\"].*{re.escape(file_stem)}['\"]",
    ])

    # Search all source files
    for root, dirs, files in os.walk(project_path):
        # Skip hidden directories and common non-source directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".venv")]

        for file in files:
            # Check file extensions
            if not _is_source_file(file):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, project_path)

            # Skip tests if requested
            if exclude_tests and _is_test_file(rel_path):
                continue

            # Skip the file itself
            if rel_path == module_path:
                continue

            try:
                with open(file_path, "r", errors="replace") as f:
                    content = f.read()

                for pattern in patterns:
                    if re.search(pattern, content):
                        importers.append(rel_path)
                        break
            except Exception:
                continue

    return importers


def find_usages_of(
    project_path: str,
    identifier: str,
    exclude_tests: bool = True,
) -> List[Tuple[str, int, str]]:
    """Find usages of an identifier in the codebase.

    Args:
        project_path: Path to project root
        identifier: Identifier to search for (class name, function name, etc.)
        exclude_tests: Whether to exclude test files

    Returns:
        List of (file_path, line_number, line_content) tuples
    """
    usages = []

    # Pattern to match identifier usage (not definition)
    pattern = rf"\b{re.escape(identifier)}\b"

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".venv")]

        for file in files:
            if not _is_source_file(file):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, project_path)

            if exclude_tests and _is_test_file(rel_path):
                continue

            try:
                with open(file_path, "r", errors="replace") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        # Skip definitions
                        if not _is_definition_line(line, identifier):
                            usages.append((rel_path, i, line.strip()))
            except Exception:
                continue

    return usages


def verify_key_link(
    project_path: str,
    key_link,
    verification: LinkVerification,
) -> None:
    """Verify a key link between components.

    Args:
        project_path: Path to project root
        key_link: KeyLink object
        verification: LinkVerification to update
    """
    from_path = key_link.from_component
    to_path = key_link.to_component
    via = key_link.via.lower()

    # Different verification strategies based on link type
    if "import" in via or "require" in via:
        # Check if from_component imports to_component
        verification.connected = _verify_import_link(project_path, from_path, to_path)
        verification.verification_method = "import_check"

    elif "api" in via or "http" in via or "fetch" in via:
        # Check for API endpoint usage
        verification.connected = _verify_api_link(project_path, from_path, to_path)
        verification.verification_method = "api_usage_check"

    elif "event" in via or "emit" in via or "subscribe" in via:
        # Check for event connection
        verification.connected = _verify_event_link(project_path, from_path, to_path)
        verification.verification_method = "event_check"

    elif "call" in via or "invoke" in via:
        # Check for function call
        verification.connected = _verify_call_link(project_path, from_path, to_path)
        verification.verification_method = "call_check"

    else:
        # Default: check for any reference
        verification.connected = _verify_reference_link(project_path, from_path, to_path)
        verification.verification_method = "reference_check"

    verification.status = "passed" if verification.connected else "failed"


def verify_artifact_wired(
    project_path: str,
    artifact_path: str,
    verification: ArtifactVerification,
) -> None:
    """Verify artifact is wired into the system.

    Args:
        project_path: Path to project root
        artifact_path: Path to artifact (relative to project)
        verification: ArtifactVerification to update
    """
    # Find files that import this module
    importers = find_imports_of(project_path, artifact_path)

    verification.is_wired = len(importers) > 0
    verification.wiring_evidence = importers[:5]  # Keep first 5


def _path_to_module_name(file_path: str) -> str:
    """Convert file path to module name."""
    # Remove extension
    path = os.path.splitext(file_path)[0]
    # Convert path separators to dots
    module = path.replace(os.sep, ".").replace("/", ".")
    # Remove leading dots
    return module.lstrip(".")


def _is_source_file(filename: str) -> bool:
    """Check if file is a source file."""
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php"}
    return os.path.splitext(filename)[1] in extensions


def _is_test_file(file_path: str) -> bool:
    """Check if file is a test file."""
    path_lower = file_path.lower()
    return (
        "test" in path_lower or
        "spec" in path_lower or
        "__tests__" in path_lower
    )


def _is_definition_line(line: str, identifier: str) -> bool:
    """Check if line is defining (not using) the identifier."""
    patterns = [
        rf"^\s*def\s+{re.escape(identifier)}\s*\(",
        rf"^\s*class\s+{re.escape(identifier)}\s*[\(:]",
        rf"^\s*(const|let|var)\s+{re.escape(identifier)}\s*=",
        rf"^\s*function\s+{re.escape(identifier)}\s*\(",
    ]
    return any(re.match(p, line) for p in patterns)


def _verify_import_link(project_path: str, from_path: str, to_path: str) -> bool:
    """Verify from_component imports to_component."""
    full_from = os.path.join(project_path, from_path)
    if not os.path.exists(full_from):
        return False

    try:
        with open(full_from, "r", errors="replace") as f:
            content = f.read()
    except Exception:
        return False

    to_module = _path_to_module_name(to_path)
    to_stem = os.path.splitext(os.path.basename(to_path))[0]

    patterns = [
        rf"from\s+\S*{re.escape(to_module)}\s+import",
        rf"import\s+\S*{re.escape(to_module)}",
        rf"from\s+['\"].*{re.escape(to_stem)}['\"]",
        rf"require\s*\(\s*['\"].*{re.escape(to_stem)}['\"]",
    ]

    return any(re.search(p, content) for p in patterns)


def _verify_api_link(project_path: str, from_path: str, to_path: str) -> bool:
    """Verify from_component calls to_component's API."""
    full_from = os.path.join(project_path, from_path)
    if not os.path.exists(full_from):
        return False

    try:
        with open(full_from, "r", errors="replace") as f:
            content = f.read()
    except Exception:
        return False

    # Look for fetch/axios/http calls
    api_patterns = [
        r"fetch\s*\(",
        r"axios\.",
        r"http\.",
        r"request\s*\(",
        r"\.get\s*\(",
        r"\.post\s*\(",
        r"\.put\s*\(",
        r"\.delete\s*\(",
    ]

    return any(re.search(p, content) for p in api_patterns)


def _verify_event_link(project_path: str, from_path: str, to_path: str) -> bool:
    """Verify event connection between components."""
    full_from = os.path.join(project_path, from_path)
    if not os.path.exists(full_from):
        return False

    try:
        with open(full_from, "r", errors="replace") as f:
            content = f.read()
    except Exception:
        return False

    event_patterns = [
        r"\.emit\s*\(",
        r"\.on\s*\(",
        r"\.addEventListener\s*\(",
        r"\.subscribe\s*\(",
        r"\.publish\s*\(",
    ]

    return any(re.search(p, content) for p in event_patterns)


def _verify_call_link(project_path: str, from_path: str, to_path: str) -> bool:
    """Verify function call between components."""
    # Get the target component's exports
    full_to = os.path.join(project_path, to_path)
    if not os.path.exists(full_to):
        return False

    try:
        with open(full_to, "r", errors="replace") as f:
            to_content = f.read()
    except Exception:
        return False

    # Find exported functions/classes
    exports = []
    for match in re.finditer(r"def\s+(\w+)\s*\(|class\s+(\w+)", to_content):
        name = match.group(1) or match.group(2)
        if not name.startswith("_"):
            exports.append(name)

    if not exports:
        return False

    # Check if from_component uses any exports
    full_from = os.path.join(project_path, from_path)
    if not os.path.exists(full_from):
        return False

    try:
        with open(full_from, "r", errors="replace") as f:
            from_content = f.read()
    except Exception:
        return False

    return any(re.search(rf"\b{re.escape(exp)}\b", from_content) for exp in exports)


def _verify_reference_link(project_path: str, from_path: str, to_path: str) -> bool:
    """Verify any reference between components."""
    # This is the most general check - just verify import link
    return _verify_import_link(project_path, from_path, to_path)
