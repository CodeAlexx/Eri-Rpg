"""
Language-specific parsers for code analysis.

Each parser extracts:
- Imports/dependencies
- Interfaces (classes, functions, exports)
- Module docstrings/summaries

Supported languages:
- Python (.py) - uses stdlib ast
- C/C++ (.c, .h, .cpp, .hpp) - regex-based
- Rust (.rs) - regex-based
- Dart (.dart) - regex-based
- Mojo (.mojo, .🔥) - regex-based
"""

from erirpg.parsers.python import parse_python_file, resolve_import_to_module
from erirpg.parsers.c import parse_c_file, resolve_include_to_module
from erirpg.parsers.rust import parse_rust_file, resolve_use_to_module, classify_external_crate
from erirpg.parsers.dart import parse_dart_file, resolve_import_to_module as resolve_dart_import, classify_external_package
from erirpg.parsers.mojo import (
    parse_mojo_file,
    resolve_import_to_module as resolve_mojo_import,
    classify_external_package as classify_mojo_package,
    is_mojo_file,
)

__all__ = [
    "parse_python_file",
    "resolve_import_to_module",
    "parse_c_file",
    "resolve_include_to_module",
    "parse_rust_file",
    "resolve_use_to_module",
    "classify_external_crate",
    "parse_dart_file",
    "resolve_dart_import",
    "classify_external_package",
    "parse_mojo_file",
    "resolve_mojo_import",
    "classify_mojo_package",
    "is_mojo_file",
]


def get_parser_for_file(path: str):
    """Get appropriate parser function for a file path.

    Returns:
        Parser function or None if unsupported
    """
    if path.endswith(".py"):
        return parse_python_file
    elif path.endswith((".c", ".h", ".cpp", ".hpp", ".cc", ".hh")):
        return parse_c_file
    elif path.endswith(".rs"):
        return parse_rust_file
    elif path.endswith(".dart"):
        return parse_dart_file
    elif is_mojo_file(path):
        return parse_mojo_file
    return None


def detect_language(path: str) -> str:
    """Detect language from file extension.

    Returns:
        Language string: 'python', 'c', 'rust', 'dart', 'mojo', or 'unknown'
    """
    if path.endswith(".py"):
        return "python"
    elif path.endswith((".c", ".h", ".cpp", ".hpp", ".cc", ".hh")):
        return "c"
    elif path.endswith(".rs"):
        return "rust"
    elif path.endswith(".dart"):
        return "dart"
    elif is_mojo_file(path):
        return "mojo"
    return "unknown"
