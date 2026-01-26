"""
Rust parser using regex (no external deps).

Extracts:
- use statements (for dependencies)
- fn definitions (for interfaces)
- struct/enum definitions (for interfaces)
- impl blocks (for interfaces)
- mod declarations (for dependencies)
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_rust_file(path: str) -> Dict[str, Any]:
    """Parse Rust file, extract interfaces and imports.

    Args:
        path: Path to .rs file

    Returns:
        Dict with keys:
        - docstring: Module doc comment (//! or /*!)
        - imports: List of use/mod dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    result = {
        "docstring": _extract_module_doc(source),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    # Extract use statements
    # use foo::bar::{baz, qux};
    for match in re.finditer(r'use\s+([\w:]+(?:::\{[^}]+\})?)\s*;', source):
        path = match.group(1)
        # Extract crate name
        parts = path.split("::")
        crate_name = parts[0] if parts else path

        result["imports"].append({
            "type": "use",
            "name": path,
            "crate": crate_name,
        })

    # Extract mod declarations (both inline and external)
    for match in re.finditer(r'(?:pub\s+)?mod\s+(\w+)\s*[{;]', source):
        name = match.group(1)
        result["imports"].append({
            "type": "mod",
            "name": name,
        })

    # Extract function definitions
    fn_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?           # Optional pub/pub(crate)
        (?:async\s+)?                        # Optional async
        (?:unsafe\s+)?                       # Optional unsafe
        (?:const\s+)?                        # Optional const
        fn\s+
        (\w+)                                # Function name
        (?:<[^>]+>)?                         # Optional generics
        \s*\(([^)]*)\)                       # Parameters
        (?:\s*->\s*([^\{]+?))?               # Optional return type
        \s*(?:where[^{]+)?\s*\{              # Optional where clause + opening brace
    '''
    for match in re.finditer(fn_pattern, source, re.VERBOSE):
        name = match.group(1)
        params = match.group(2).strip()
        ret_type = match.group(3).strip() if match.group(3) else "()"

        line_num = source[:match.start()].count("\n") + 1

        # Get doc comment
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "function",
            "signature": f"fn {name}({_summarize_params(params)}) -> {ret_type}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract struct definitions
    struct_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        struct\s+
        (\w+)                                # Struct name
        (?:<[^>]+>)?                         # Optional generics
        \s*(?:\{([^}]*)\}|\([^)]*\)\s*;|;)   # Body or tuple struct or unit struct
    '''
    for match in re.finditer(struct_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1)
        body = match.group(2) or ""

        # Extract field names
        fields = []
        for field_match in re.finditer(r'(\w+)\s*:', body):
            fields.append(field_match.group(1))

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "struct",
            "signature": f"struct {name}",
            "docstring": doc,
            "methods": fields,
            "line": line_num,
        })

    # Extract enum definitions
    enum_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        enum\s+
        (\w+)                                # Enum name
        (?:<[^>]+>)?                         # Optional generics
        \s*\{([^}]*)\}
    '''
    for match in re.finditer(enum_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1)
        body = match.group(2)

        # Extract variant names
        variants = []
        for var_match in re.finditer(r'(\w+)(?:\s*\{|\s*\(|,|\s*$)', body):
            variants.append(var_match.group(1))

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "enum",
            "signature": f"enum {name}",
            "docstring": doc,
            "methods": variants,
            "line": line_num,
        })

    # Extract impl blocks
    impl_pattern = r'''
        (?:^|\n)\s*
        impl\s*
        (?:<[^>]+>\s*)?                      # Optional generics
        (?:(\w+)\s+for\s+)?                  # Optional trait
        (\w+)                                # Type name
        (?:<[^>]+>)?                         # Optional type generics
        \s*\{
    '''
    for match in re.finditer(impl_pattern, source, re.VERBOSE):
        trait_name = match.group(1)
        type_name = match.group(2)

        line_num = source[:match.start()].count("\n") + 1

        name = f"{type_name}" if not trait_name else f"{trait_name} for {type_name}"

        result["interfaces"].append({
            "name": name,
            "type": "impl",
            "signature": f"impl {name}",
            "docstring": "",
            "line": line_num,
        })

    # Extract trait definitions
    trait_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        trait\s+
        (\w+)                                # Trait name
        (?:<[^>]+>)?                         # Optional generics
        \s*(?::\s*[^{]+)?\s*\{               # Optional bounds + opening brace
    '''
    for match in re.finditer(trait_pattern, source, re.VERBOSE):
        name = match.group(1)
        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "trait",
            "signature": f"trait {name}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract const definitions
    const_pattern = r'''
        (?:^|\n)\s*
        (?:pub(?:\([^)]+\))?\s+)?
        const\s+
        (\w+)                                # Const name
        \s*:\s*([^=]+?)                      # Type
        \s*=
    '''
    for match in re.finditer(const_pattern, source, re.VERBOSE):
        name = match.group(1)
        const_type = match.group(2).strip()
        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "const",
            "signature": f"const {name}: {const_type}",
            "docstring": "",
            "line": line_num,
        })

    return result


def _extract_module_doc(source: str) -> str:
    """Extract module-level doc comment (//! or /*!)."""
    # Check for //! comments at start
    lines = source.split("\n")
    doc_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("//!"):
            doc_lines.append(line[3:].strip())
        elif line.startswith("/*!"):
            # Block doc comment
            match = re.match(r'/\*!\s*(.*?)\s*\*/', source, re.DOTALL)
            if match:
                return match.group(1).split("\n")[0].strip()[:100]
            break
        elif line and not line.startswith("//"):
            break

    if doc_lines:
        return doc_lines[0][:100] if doc_lines else ""
    return ""


def _extract_doc_comment(source: str, pos: int) -> str:
    """Extract /// doc comment immediately before a position."""
    before = source[:pos]
    lines = before.split("\n")

    # Look for /// comments working backwards
    doc_lines = []
    for line in reversed(lines[-10:]):  # Check last 10 lines
        line = line.strip()
        if line.startswith("///"):
            doc_lines.insert(0, line[3:].strip())
        elif line.startswith("#["):
            continue  # Skip attributes
        elif line == "" and doc_lines:
            continue
        elif doc_lines:
            break
        else:
            break

    return doc_lines[0] if doc_lines else ""


def _summarize_params(params: str) -> str:
    """Summarize function parameters for display."""
    if not params.strip():
        return ""

    # Count parameters
    depth = 0
    count = 1
    for c in params:
        if c in "(<[{":
            depth += 1
        elif c in ")>]}":
            depth -= 1
        elif c == "," and depth == 0:
            count += 1

    if count > 3:
        return "..."
    if len(params) > 50:
        return "..."
    return params


def resolve_use_to_module(
    use_info: dict,
    project_modules: List[str],
) -> Optional[str]:
    """Resolve a use statement to a project module.

    Args:
        use_info: Dict from parse_rust_file imports
        project_modules: List of known module paths in the project

    Returns:
        Module path if internal, None if external crate
    """
    crate = use_info.get("crate", "")

    # Check if it's a known internal module
    if use_info["type"] == "mod":
        name = use_info["name"]
        for mod in project_modules:
            if mod.endswith(f"/{name}.rs") or mod.endswith(f"/{name}/mod.rs"):
                return mod

    # Check use statements
    if crate in ("crate", "self", "super"):
        # Internal path
        name = use_info["name"].replace("::", "/")
        for mod in project_modules:
            if name in mod:
                return mod

    return None


def classify_external_crate(use_info: dict) -> Optional[str]:
    """Extract external crate name from use statement.

    Returns the crate name, or None if it's internal.
    """
    if use_info["type"] == "mod":
        return None

    crate = use_info.get("crate", "")

    if crate in ("crate", "self", "super"):
        return None  # Internal

    if crate == "std":
        return None  # Standard library

    return crate
