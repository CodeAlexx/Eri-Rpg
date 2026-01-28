"""
Mojo parser using regex (no external deps).

Mojo is a systems programming language by Modular, designed for AI/ML.
File extensions: .mojo, .🔥

Extracts:
- import statements (for dependencies)
- fn/def definitions (for interfaces)
- struct definitions (for interfaces)
- trait definitions (for interfaces)
- decorators
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path


# Fire emoji as bytes for reliable matching
FIRE_EMOJI = "\U0001F525"  # 🔥


def parse_mojo_file(path: str) -> Dict[str, Any]:
    """Parse Mojo file, extract interfaces and imports.

    Args:
        path: Path to .mojo or .🔥 file

    Returns:
        Dict with keys:
        - docstring: Module docstring
        - imports: List of import dicts
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

    # Extract import statements
    # import foo
    # import foo.bar
    # import foo as f
    for match in re.finditer(r'^import\s+([\w.]+)(?:\s+as\s+(\w+))?', source, re.MULTILINE):
        module = match.group(1)
        alias = match.group(2)
        result["imports"].append({
            "type": "import",
            "name": module,
            "asname": alias,
        })

    # from foo import bar, baz
    # from foo.bar import baz as b
    for match in re.finditer(r'^from\s+([\w.]+)\s+import\s+(.+?)$', source, re.MULTILINE):
        module = match.group(1)
        names_str = match.group(2).strip()
        # Parse imported names
        names = []
        for name in names_str.split(","):
            name = name.strip()
            if " as " in name:
                name = name.split(" as ")[0].strip()
            if name and not name.startswith("#"):
                names.append(name)

        result["imports"].append({
            "type": "from",
            "module": module,
            "names": names,
            "level": 0,  # Mojo doesn't have relative imports like Python
        })

    # Extract Python interop imports
    # Python.import_module("numpy")
    for match in re.finditer(r'Python\.import_module\(["\'](\w+)["\']\)', source):
        result["imports"].append({
            "type": "python_interop",
            "name": match.group(1),
        })

    # Extract fn definitions (strongly-typed functions)
    fn_pattern = r'''
        (?:^|\n)\s*
        (?:(@\w+(?:\([^)]*\))?)\s*\n\s*)?  # Optional decorator
        fn\s+
        (\w+)                               # Function name
        (?:\[([^\]]+)\])?                   # Optional parameters [...] (compile-time)
        \s*\(([^)]*)\)                      # Arguments (...)
        (?:\s+raises)?                      # Optional raises
        (?:\s*->\s*([^\n:]+?))?             # Optional return type
        \s*:                                # Colon
    '''
    for match in re.finditer(fn_pattern, source, re.VERBOSE | re.MULTILINE):
        decorator = match.group(1) or ""
        name = match.group(2)
        type_params = match.group(3) or ""
        params = match.group(4).strip()
        ret_type = match.group(5).strip() if match.group(5) else "None"

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        sig = f"fn {name}"
        if type_params:
            sig += f"[{type_params}]"
        sig += f"({_summarize_params(params)})"
        if ret_type and ret_type != "None":
            sig += f" -> {ret_type}"

        interface = {
            "name": name,
            "type": "fn",
            "signature": sig,
            "docstring": doc,
            "line": line_num,
        }
        if decorator:
            interface["decorator"] = decorator

        result["interfaces"].append(interface)

    # Extract def definitions (dynamic functions)
    def_pattern = r'''
        (?:^|\n)\s*
        (?:(@\w+(?:\([^)]*\))?)\s*\n\s*)?  # Optional decorator
        def\s+
        (\w+)                               # Function name
        \s*\(([^)]*)\)                      # Arguments
        (?:\s*->\s*([^\n:]+?))?             # Optional return type
        \s*:                                # Colon
    '''
    for match in re.finditer(def_pattern, source, re.VERBOSE | re.MULTILINE):
        decorator = match.group(1) or ""
        name = match.group(2)
        params = match.group(3).strip()
        ret_type = match.group(4).strip() if match.group(4) else ""

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        sig = f"def {name}({_summarize_params(params)})"
        if ret_type:
            sig += f" -> {ret_type}"

        interface = {
            "name": name,
            "type": "def",
            "signature": sig,
            "docstring": doc,
            "line": line_num,
        }
        if decorator:
            interface["decorator"] = decorator

        result["interfaces"].append(interface)

    # Extract struct definitions
    struct_pattern = r'''
        (?:^|\n)\s*
        (?:(@\w+(?:\([^)]*\))?)\s*\n\s*)*  # Optional decorators
        struct\s+
        (\w+)                               # Struct name
        (?:\[([^\]]+)\])?                   # Optional type parameters
        (?:\s*\(([^)]+)\))?                 # Optional traits (like inheritance)
        \s*:                                # Colon
    '''
    for match in re.finditer(struct_pattern, source, re.VERBOSE | re.MULTILINE):
        name = match.group(2)
        type_params = match.group(3) or ""
        traits = match.group(4) or ""

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        # Extract struct body (fields and methods)
        body_start = match.end()
        body = _extract_indented_block(source, body_start)
        fields = _extract_struct_fields(body)
        methods = _extract_struct_methods(body)

        sig = f"struct {name}"
        if type_params:
            sig += f"[{type_params}]"
        if traits:
            sig += f"({traits})"

        result["interfaces"].append({
            "name": name,
            "type": "struct",
            "signature": sig,
            "docstring": doc,
            "methods": methods,
            "fields": fields,
            "line": line_num,
        })

    # Extract trait definitions
    trait_pattern = r'''
        (?:^|\n)\s*
        trait\s+
        (\w+)                               # Trait name
        (?:\[([^\]]+)\])?                   # Optional type parameters
        (?:\s*\(([^)]+)\))?                 # Optional parent traits
        \s*:                                # Colon
    '''
    for match in re.finditer(trait_pattern, source, re.VERBOSE | re.MULTILINE):
        name = match.group(1)
        type_params = match.group(2) or ""
        parents = match.group(3) or ""

        line_num = source[:match.start()].count("\n") + 1
        doc = _extract_doc_comment(source, match.start())

        sig = f"trait {name}"
        if type_params:
            sig += f"[{type_params}]"
        if parents:
            sig += f"({parents})"

        result["interfaces"].append({
            "name": name,
            "type": "trait",
            "signature": sig,
            "docstring": doc,
            "line": line_num,
        })

    # Extract alias definitions
    alias_pattern = r'''
        (?:^|\n)\s*
        alias\s+
        (\w+)                               # Alias name
        \s*=\s*
        ([^\n]+)                            # Aliased type
    '''
    for match in re.finditer(alias_pattern, source, re.VERBOSE | re.MULTILINE):
        name = match.group(1)
        aliased = match.group(2).strip()
        line_num = source[:match.start()].count("\n") + 1

        result["interfaces"].append({
            "name": name,
            "type": "alias",
            "signature": f"alias {name} = {aliased}",
            "docstring": "",
            "line": line_num,
        })

    # Extract var/let at module level (constants)
    var_pattern = r'''
        ^(?:var|let)\s+
        (\w+)                               # Variable name
        \s*:\s*
        ([^=\n]+?)                          # Type
        (?:\s*=)?
    '''
    for match in re.finditer(var_pattern, source, re.VERBOSE | re.MULTILINE):
        name = match.group(1)
        var_type = match.group(2).strip()
        line_num = source[:match.start()].count("\n") + 1

        # Only include if it looks like a constant (uppercase or at module level)
        if name.isupper() or line_num < 50:  # Heuristic for module-level
            result["interfaces"].append({
                "name": name,
                "type": "var",
                "signature": f"var {name}: {var_type}",
                "docstring": "",
                "line": line_num,
            })

    return result


def _extract_module_doc(source: str) -> str:
    """Extract module-level docstring (triple-quoted at start)."""
    # Check for triple-quoted string at start
    source = source.lstrip()
    if source.startswith('"""'):
        end = source.find('"""', 3)
        if end != -1:
            doc = source[3:end].strip()
            return doc.split("\n")[0][:100] if doc else ""
    elif source.startswith("'''"):
        end = source.find("'''", 3)
        if end != -1:
            doc = source[3:end].strip()
            return doc.split("\n")[0][:100] if doc else ""

    # Check for # comments at start
    lines = source.split("\n")
    doc_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            doc_lines.append(line[1:].strip())
        elif line == "":
            continue
        else:
            break

    return doc_lines[0][:100] if doc_lines else ""


def _extract_doc_comment(source: str, pos: int) -> str:
    """Extract docstring or # comment immediately before a position."""
    before = source[:pos]
    lines = before.split("\n")

    # Look for # comments or docstring working backwards
    doc_lines = []
    for line in reversed(lines[-10:]):
        line = line.strip()
        if line.startswith("#"):
            doc_lines.insert(0, line[1:].strip())
        elif line.startswith("@"):
            continue  # Skip decorators
        elif line == "" and doc_lines:
            continue
        elif doc_lines:
            break
        else:
            break

    return doc_lines[0] if doc_lines else ""


def _extract_indented_block(source: str, start: int) -> str:
    """Extract an indented block starting at position."""
    lines = source[start:].split("\n")
    if not lines:
        return ""

    result = []
    in_block = False
    base_indent = None

    for line in lines[1:]:  # Skip the first line (the header)
        if not line.strip():
            if in_block:
                result.append(line)
            continue

        # Calculate indentation
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if base_indent is None:
            base_indent = indent
            in_block = True

        if indent >= base_indent:
            result.append(line)
            in_block = True
        else:
            break  # End of block

    return "\n".join(result)


def _extract_struct_fields(body: str) -> List[str]:
    """Extract field names from struct body."""
    fields = []
    for match in re.finditer(r'var\s+(\w+)\s*:', body):
        fields.append(match.group(1))
    return fields


def _extract_struct_methods(body: str) -> List[str]:
    """Extract method names from struct body."""
    methods = []
    for match in re.finditer(r'(?:fn|def)\s+(\w+)\s*[\[(]', body):
        methods.append(match.group(1))
    return methods


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
    project_name: str = "",
    current_module: str = "",
) -> Optional[str]:
    """Resolve a Mojo import to a project module path.

    Args:
        import_info: Dict from parse_mojo_file imports
        project_modules: List of known module paths in the project
        project_name: Name of project
        current_module: Path of the module containing the import

    Returns:
        Module path if internal, None if external
    """
    if import_info["type"] == "python_interop":
        return None  # Always external

    if import_info["type"] == "import":
        name = import_info["name"]
        parts = name.split(".")

        # Check if any module path matches
        for mod in project_modules:
            mod_parts = mod.replace("/", ".").replace(".mojo", "").split(".")
            if parts[0] == mod_parts[0]:
                # Try as .mojo file
                candidate = "/".join(parts) + ".mojo"
                if candidate in project_modules:
                    return candidate
                # Try as package (__init__.mojo)
                candidate = "/".join(parts) + "/__init__.mojo"
                if candidate in project_modules:
                    return candidate
        return None

    elif import_info["type"] == "from":
        module = import_info.get("module", "")
        parts = module.split(".")

        # Check direct match
        for mod in project_modules:
            mod_no_ext = mod.replace(".mojo", "").replace("/__init__", "")
            mod_dotted = mod_no_ext.replace("/", ".")
            if mod_dotted == module or mod_dotted.endswith(f".{module}"):
                return mod

        return None

    return None


def classify_external_package(import_info: dict) -> Optional[str]:
    """Extract external package name from import.

    Returns the top-level package name.
    """
    if import_info["type"] == "python_interop":
        return f"python:{import_info['name']}"

    if import_info["type"] == "import":
        name = import_info["name"]
        return name.split(".")[0]

    elif import_info["type"] == "from":
        module = import_info["module"]
        return module.split(".")[0]

    return None


def is_mojo_file(path: str) -> bool:
    """Check if a file is a Mojo source file.

    Handles both .mojo and .🔥 extensions.
    """
    return path.endswith(".mojo") or path.endswith(FIRE_EMOJI) or path.endswith(".🔥")
