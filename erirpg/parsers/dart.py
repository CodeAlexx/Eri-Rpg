"""
Dart parser using regex (no external deps).

Extracts:
- import statements (for dependencies)
- class definitions (for interfaces)
- function definitions (for interfaces)
- mixin definitions (for interfaces)
- extension definitions (for interfaces)
- enum definitions (for interfaces)
- typedef definitions (for interfaces)
"""

import re
from typing import Dict, List, Any, Optional


def parse_dart_file(path: str) -> Dict[str, Any]:
    """Parse Dart file, extract interfaces and imports.

    Args:
        path: Path to .dart file

    Returns:
        Dict with keys:
        - docstring: Library/file doc comment
        - imports: List of import dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    result = {
        "docstring": _extract_library_doc(source),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    # Extract import statements
    # import 'package:foo/bar.dart';
    # import 'dart:core';
    # import 'relative/path.dart';
    # import '...' as alias;
    # import '...' show Foo, Bar;
    # import '...' hide Baz;
    import_pattern = r'''
        import\s+
        ['\"]([^'\"]+)['\"]       # Import path
        (?:\s+as\s+(\w+))?       # Optional alias
        (?:\s+(?:show|hide)\s+   # Optional show/hide
            ([\w,\s]+))?
        \s*;
    '''
    for match in re.finditer(import_pattern, source, re.VERBOSE):
        import_path = match.group(1)
        alias = match.group(2)
        
        # Determine import type
        if import_path.startswith("dart:"):
            import_type = "dart"
            package = import_path[5:]  # Remove "dart:"
        elif import_path.startswith("package:"):
            import_type = "package"
            package = import_path[8:].split("/")[0]  # Extract package name
        else:
            import_type = "relative"
            package = import_path

        result["imports"].append({
            "type": import_type,
            "path": import_path,
            "package": package,
            "alias": alias,
        })

    # Extract export statements
    export_pattern = r'''
        export\s+
        ['\"]([^'\"]+)['\"]
        \s*;
    '''
    for match in re.finditer(export_pattern, source, re.VERBOSE):
        export_path = match.group(1)
        result["imports"].append({
            "type": "export",
            "path": export_path,
            "package": export_path,
        })

    # Extract part/part of statements
    part_pattern = r"part\s+(?:of\s+)?['\"]([^'\"]+)['\"]\s*;"
    for match in re.finditer(part_pattern, source):
        part_path = match.group(1)
        result["imports"].append({
            "type": "part",
            "path": part_path,
            "package": part_path,
        })

    # Extract class definitions
    class_pattern = r'''
        (?:^|\n)\s*
        (?:abstract\s+)?                    # Optional abstract
        (?:base\s+)?                        # Optional base (Dart 3)
        (?:final\s+)?                       # Optional final (Dart 3)
        (?:interface\s+)?                   # Optional interface (Dart 3)
        (?:sealed\s+)?                      # Optional sealed (Dart 3)
        (?:mixin\s+)?                       # Optional mixin class
        class\s+
        (\w+)                               # Class name
        (?:<[^>]+>)?                        # Optional generics
        (?:\s+extends\s+(\w+))?             # Optional extends
        (?:\s+with\s+([\w,\s]+))?           # Optional mixins
        (?:\s+implements\s+([\w,\s]+))?     # Optional implements
        \s*\{
    '''
    for match in re.finditer(class_pattern, source, re.VERBOSE):
        name = match.group(1)
        extends = match.group(2)
        mixins = match.group(3)
        implements = match.group(4)

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        # Build signature
        sig_parts = [f"class {name}"]
        if extends:
            sig_parts.append(f"extends {extends}")
        if mixins:
            sig_parts.append(f"with {mixins.strip()}")
        if implements:
            sig_parts.append(f"implements {implements.strip()}")

        result["interfaces"].append({
            "name": name,
            "type": "class",
            "signature": " ".join(sig_parts),
            "docstring": doc,
            "line": line_num,
        })

    # Extract mixin definitions
    mixin_pattern = r'''
        (?:^|\n)\s*
        (?:base\s+)?                        # Optional base
        mixin\s+
        (\w+)                               # Mixin name
        (?:<[^>]+>)?                        # Optional generics
        (?:\s+on\s+([\w,\s]+))?             # Optional on clause
        (?:\s+implements\s+([\w,\s]+))?     # Optional implements
        \s*\{
    '''
    for match in re.finditer(mixin_pattern, source, re.VERBOSE):
        name = match.group(1)
        on_clause = match.group(2)
        
        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        sig = f"mixin {name}"
        if on_clause:
            sig += f" on {on_clause.strip()}"

        result["interfaces"].append({
            "name": name,
            "type": "mixin",
            "signature": sig,
            "docstring": doc,
            "line": line_num,
        })

    # Extract extension definitions
    extension_pattern = r'''
        (?:^|\n)\s*
        extension\s+
        (\w+)?                              # Optional extension name
        (?:<[^>]+>)?                        # Optional generics
        \s+on\s+
        ([\w<>,\s]+?)                       # Extended type
        \s*\{
    '''
    for match in re.finditer(extension_pattern, source, re.VERBOSE):
        name = match.group(1) or "(anonymous)"
        extended_type = match.group(2).strip()
        
        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "extension",
            "signature": f"extension {name} on {extended_type}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract enum definitions
    enum_pattern = r'''
        (?:^|\n)\s*
        enum\s+
        (\w+)                               # Enum name
        (?:<[^>]+>)?                        # Optional generics (Dart 2.17+)
        (?:\s+with\s+([\w,\s]+))?           # Optional mixins
        (?:\s+implements\s+([\w,\s]+))?     # Optional implements
        \s*\{([^}]*)\}
    '''
    for match in re.finditer(enum_pattern, source, re.VERBOSE | re.DOTALL):
        name = match.group(1)
        body = match.group(4)
        
        # Extract enum values (before semicolon or end)
        values = []
        value_section = body.split(";")[0] if ";" in body else body
        for val_match in re.finditer(r'(\w+)(?:\s*\(|,|\s*$)', value_section):
            val = val_match.group(1)
            if val and val not in ("const", "final", "static"):
                values.append(val)
        
        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "enum",
            "signature": f"enum {name}",
            "docstring": doc,
            "methods": values[:10],  # Limit to first 10 values
            "line": line_num,
        })

    # Extract top-level function definitions
    fn_pattern = r'''
        (?:^|\n)\s*
        (?:external\s+)?                    # Optional external
        ([\w<>,\s\?]+?)                     # Return type
        \s+
        (\w+)                               # Function name
        (?:<[^>]+>)?                        # Optional generics
        \s*\(([^)]*)\)                      # Parameters
        (?:\s+async)?                       # Optional async
        \s*(?:\{|=>|;)                      # Body start or arrow or abstract
    '''
    for match in re.finditer(fn_pattern, source, re.VERBOSE):
        ret_type = match.group(1).strip()
        name = match.group(2)
        params = match.group(3).strip()

        # Skip if this looks like a class method (inside class body)
        # or constructor
        if name[0].isupper():
            continue
        if ret_type in ("class", "mixin", "enum", "extension", "typedef", "import", "export", "part"):
            continue

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "function",
            "signature": f"{ret_type} {name}({_summarize_params(params)})",
            "docstring": doc,
            "line": line_num,
        })

    # Extract typedef definitions
    typedef_pattern = r'''
        (?:^|\n)\s*
        typedef\s+
        (\w+)                               # Typedef name
        (?:<[^>]+>)?                        # Optional generics
        \s*=\s*
        ([^;]+)                             # Type definition
        ;
    '''
    for match in re.finditer(typedef_pattern, source, re.VERBOSE):
        name = match.group(1)
        type_def = match.group(2).strip()

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        result["interfaces"].append({
            "name": name,
            "type": "typedef",
            "signature": f"typedef {name} = {type_def[:50]}{'...' if len(type_def) > 50 else ''}",
            "docstring": doc,
            "line": line_num,
        })

    # Extract top-level constants/variables
    const_pattern = r'''
        (?:^|\n)\s*
        (?:final|const)\s+
        ([\w<>,\?]+)                        # Type
        \s+
        (\w+)                               # Name
        \s*=
    '''
    for match in re.finditer(const_pattern, source, re.VERBOSE):
        var_type = match.group(1)
        name = match.group(2)

        # Skip if inside a class (rough heuristic)
        before = source[:match.start()]
        open_braces = before.count("{") - before.count("}")
        if open_braces > 0:
            continue

        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "constant",
            "signature": f"const {var_type} {name}",
            "docstring": "",
            "line": line_num,
        })

    return result


def _extract_library_doc(source: str) -> str:
    """Extract library-level doc comment."""
    # Look for /// comments at the very start (before library/import)
    lines = source.split("\n")
    doc_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("///"):
            doc_lines.append(stripped[3:].strip())
        elif stripped.startswith("//"):
            continue  # Skip regular comments
        elif stripped == "":
            if doc_lines:
                break
            continue
        else:
            break
    
    if doc_lines:
        return doc_lines[0][:100]
    
    # Check for library statement with doc
    match = re.search(r'library\s+(\w+(?:\.\w+)*)\s*;', source)
    if match:
        return f"Library: {match.group(1)}"
    
    return ""


def _extract_doc_comment(source: str, pos: int) -> str:
    """Extract /// doc comment immediately before a position."""
    before = source[:pos]
    lines = before.split("\n")

    doc_lines = []
    for line in reversed(lines[-15:]):  # Check last 15 lines
        stripped = line.strip()
        if stripped.startswith("///"):
            doc_lines.insert(0, stripped[3:].strip())
        elif stripped.startswith("@"):
            continue  # Skip annotations
        elif stripped == "" and doc_lines:
            continue
        elif doc_lines:
            break
        elif stripped == "":
            continue
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
    if len(params) > 60:
        return "..."
    return params


def resolve_import_to_module(
    import_info: dict,
    project_modules: List[str],
) -> Optional[str]:
    """Resolve a Dart import to a project module.

    Args:
        import_info: Dict from parse_dart_file imports
        project_modules: List of known module paths in the project

    Returns:
        Module path if internal, None if external package
    """
    import_type = import_info.get("type", "")
    import_path = import_info.get("path", "")

    # External packages
    if import_type in ("dart", "package"):
        return None

    # Relative imports - try to match
    if import_type == "relative":
        for mod in project_modules:
            if mod.endswith(import_path) or import_path in mod:
                return mod

    # Part files
    if import_type == "part":
        for mod in project_modules:
            if mod.endswith(import_path) or import_path in mod:
                return mod

    return None


def classify_external_package(import_info: dict) -> Optional[str]:
    """Extract external package name from import statement.

    Returns the package name, or None if it's internal/dart SDK.
    """
    import_type = import_info.get("type", "")

    if import_type == "dart":
        return None  # Dart SDK

    if import_type == "package":
        return import_info.get("package")

    return None  # Relative imports are internal
