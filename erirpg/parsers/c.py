"""
C/C++ parser using regex (no external deps).

Extracts:
- #include statements (for dependencies)
- Function definitions (for interfaces)
- Struct/typedef definitions (for interfaces)
- Macro definitions (for interfaces)
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_c_file(path: str) -> Dict[str, Any]:
    """Parse C/C++ file, extract interfaces and includes.

    Args:
        path: Path to .c/.h/.cpp/.hpp file

    Returns:
        Dict with keys:
        - docstring: First block comment or empty
        - imports: List of include dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    result = {
        "docstring": _extract_file_comment(source),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    # Extract includes
    for match in re.finditer(r'#include\s*[<"]([^>"]+)[>"]', source):
        include = match.group(1)
        result["imports"].append({
            "type": "include",
            "name": include,
            "is_system": "<" in match.group(0),
        })

    # Extract function definitions (not declarations - must have body)
    # Pattern: return_type name(params) { ... }
    func_pattern = r'''
        (?:^|[\n;{}])                       # Start of line or after statement
        \s*
        (?:static\s+|inline\s+|extern\s+)*  # Optional modifiers
        ([\w\s\*]+?)                         # Return type
        \s+
        (\w+)                                # Function name
        \s*\(([^)]*)\)                       # Parameters
        \s*\{                                # Opening brace
    '''
    for match in re.finditer(func_pattern, source, re.VERBOSE | re.MULTILINE):
        ret_type = match.group(1).strip()
        name = match.group(2).strip()
        params = match.group(3).strip()

        # Skip if it looks like a control structure
        if name in ("if", "while", "for", "switch", "catch"):
            continue

        # Find line number
        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "function",
            "signature": f"{ret_type} {name}({params})",
            "docstring": _extract_preceding_comment(source, match.start()),
            "line": line_num,
        })

    # Extract struct definitions
    struct_pattern = r'''
        (?:typedef\s+)?                      # Optional typedef
        struct\s+
        (\w+)?                               # Struct name (optional for typedef)
        \s*\{([^}]*)\}                       # Body
        \s*(\w+)?                            # Typedef alias
        \s*;
    '''
    for match in re.finditer(struct_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1) or match.group(3)  # Use struct name or typedef name
        if not name:
            continue

        # Extract field names
        body = match.group(2)
        fields = []
        for field_match in re.finditer(r'(\w+)\s*[;\[]', body):
            fields.append(field_match.group(1))

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "struct",
            "signature": f"struct {name}",
            "docstring": _extract_preceding_comment(source, match.start()),
            "methods": fields,  # Use methods field for fields
            "line": line_num,
        })

    # Extract enum definitions
    enum_pattern = r'''
        (?:typedef\s+)?
        enum\s+
        (\w+)?
        \s*\{([^}]*)\}
        \s*(\w+)?
        \s*;
    '''
    for match in re.finditer(enum_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1) or match.group(3)
        if not name:
            continue

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "enum",
            "signature": f"enum {name}",
            "docstring": "",
            "line": line_num,
        })

    # Extract #define macros (function-like and constants)
    for match in re.finditer(r'^#define\s+(\w+)(?:\([^)]*\))?\s+(.*)$', source, re.MULTILINE):
        name = match.group(1)
        # Skip include guards
        if name.endswith("_H") or name.endswith("_H_"):
            continue

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "macro",
            "signature": f"#define {name}",
            "docstring": "",
            "line": line_num,
        })

    return result


def _extract_file_comment(source: str) -> str:
    """Extract first block comment as file docstring."""
    # Look for /* ... */ at start
    match = re.match(r'\s*/\*\s*(.*?)\s*\*/', source, re.DOTALL)
    if match:
        comment = match.group(1)
        # Get first meaningful line
        for line in comment.split("\n"):
            line = line.strip().lstrip("*").strip()
            if line and not line.startswith("Copyright"):
                return line[:100]
    return ""


def _extract_preceding_comment(source: str, pos: int) -> str:
    """Extract comment immediately before a position."""
    # Look backwards for /* */ or // comments
    before = source[:pos].rstrip()

    # Check for block comment
    if before.endswith("*/"):
        start = before.rfind("/*")
        if start != -1:
            comment = before[start+2:-2].strip()
            # Get first line
            lines = [l.strip().lstrip("*").strip() for l in comment.split("\n")]
            for line in lines:
                if line:
                    return line[:100]

    # Check for line comment
    lines = before.split("\n")
    if lines and lines[-1].strip().startswith("//"):
        return lines[-1].strip()[2:].strip()[:100]

    return ""


def resolve_include_to_module(
    include_info: dict,
    project_headers: List[str],
) -> Optional[str]:
    """Resolve an include to a project header.

    Args:
        include_info: Dict from parse_c_file imports
        project_headers: List of known header paths in the project

    Returns:
        Header path if internal, None if system/external
    """
    if include_info.get("is_system"):
        return None

    name = include_info["name"]

    # Try exact match
    for header in project_headers:
        if header.endswith(name) or header.endswith("/" + name):
            return header

    return None
