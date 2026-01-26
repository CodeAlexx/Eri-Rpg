"""
Python parser using stdlib ast module.

Extracts:
- Module docstring (for summary)
- Import statements (for dependencies)
- Class definitions (for interfaces)
- Top-level function definitions (for interfaces)
"""

import ast
from typing import Dict, List, Any, Optional
from pathlib import Path


def parse_python_file(path: str) -> Dict[str, Any]:
    """Parse Python file, extract interfaces and imports.

    Args:
        path: Path to Python file

    Returns:
        Dict with keys:
        - docstring: Module docstring (first line)
        - imports: List of import dicts
        - interfaces: List of interface dicts
        - lines: Line count
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    lines = source.count("\n") + 1

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            "docstring": "",
            "imports": [],
            "interfaces": [],
            "lines": lines,
            "error": f"SyntaxError: {e}",
        }

    result = {
        "docstring": _get_first_line(ast.get_docstring(tree)),
        "imports": [],
        "interfaces": [],
        "lines": lines,
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "type": "import",
                    "name": alias.name,
                    "asname": alias.asname,
                })
        elif isinstance(node, ast.ImportFrom):
            # Include import if it has a module name OR is a relative import
            # Relative imports (level > 0) may have module=None for 'from . import x'
            if node.module or node.level > 0:
                result["imports"].append({
                    "type": "from",
                    "module": node.module or "",  # Empty string for 'from . import x'
                    "names": [a.name for a in node.names],
                    "level": node.level,  # 0=absolute, 1=relative, etc.
                })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

            result["interfaces"].append({
                "name": node.name,
                "type": "class",
                "methods": methods,
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
                "bases": [_get_name(base) for base in node.bases],
            })
        elif isinstance(node, ast.FunctionDef):
            # Top-level function only (col_offset check not needed at module level)
            result["interfaces"].append({
                "name": node.name,
                "type": "function",
                "signature": _get_function_signature(node),
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
            })
        elif isinstance(node, ast.AsyncFunctionDef):
            result["interfaces"].append({
                "name": node.name,
                "type": "async_function",
                "signature": _get_function_signature(node, is_async=True),
                "docstring": _get_first_line(ast.get_docstring(node)),
                "line": node.lineno,
            })
        elif isinstance(node, ast.Assign):
            # Module-level constants (ALL_CAPS)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    result["interfaces"].append({
                        "name": target.id,
                        "type": "const",
                        "signature": "",
                        "docstring": "",
                        "line": node.lineno,
                    })

    return result


def _get_first_line(docstring: Optional[str]) -> str:
    """Extract first line of docstring."""
    if not docstring:
        return ""
    lines = docstring.strip().split("\n")
    return lines[0].strip() if lines else ""


def _get_name(node: ast.expr) -> str:
    """Get string name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[...]"
    else:
        return "?"


def _get_function_signature(node, is_async: bool = False) -> str:
    """Extract function signature as string.

    Args:
        node: ast.FunctionDef or ast.AsyncFunctionDef
        is_async: Whether function is async

    Returns:
        Signature string like "def foo(x: int, y: str) -> bool"
    """
    args = []

    # Regular args
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            try:
                arg_str += f": {ast.unparse(arg.annotation)}"
            except Exception:
                arg_str += ": ?"
        args.append(arg_str)

    # *args
    if node.args.vararg:
        vararg = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            try:
                vararg += f": {ast.unparse(node.args.vararg.annotation)}"
            except Exception:
                pass
        args.append(vararg)

    # **kwargs
    if node.args.kwarg:
        kwarg = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            try:
                kwarg += f": {ast.unparse(node.args.kwarg.annotation)}"
            except Exception:
                pass
        args.append(kwarg)

    prefix = "async def" if is_async else "def"
    sig = f"{prefix} {node.name}({', '.join(args)})"

    if node.returns:
        try:
            sig += f" -> {ast.unparse(node.returns)}"
        except Exception:
            sig += " -> ?"

    return sig


def _resolve_relative_import(
    module: str,
    level: int,
    current_module: str,
    project_modules: List[str],
) -> Optional[str]:
    """Resolve a relative import to a project module path.

    Args:
        module: The module name after 'from .' (may be empty for 'from . import')
        level: Number of dots (1 for '.', 2 for '..', etc.)
        current_module: Path of the importing module (e.g., 'pkg/sub/mod.py')
        project_modules: List of known module paths

    Returns:
        Resolved module path if found, None otherwise

    Examples:
        - 'from . import foo' in 'pkg/sub/mod.py' -> 'pkg/sub/foo.py'
        - 'from .utils import bar' in 'pkg/mod.py' -> 'pkg/utils.py'
        - 'from .. import base' in 'pkg/sub/mod.py' -> 'pkg/base.py'
        - 'from ..other import x' in 'pkg/sub/mod.py' -> 'pkg/other.py'
    """
    if not current_module:
        return None

    # Get the directory parts of the current module
    # e.g., 'pkg/sub/mod.py' -> ['pkg', 'sub']
    current_path = Path(current_module)
    parts = list(current_path.parent.parts)

    # Go up 'level' directories (level=1 means current package, level=2 means parent, etc.)
    # Actually, level=1 means same package (no going up), level=2 means parent package, etc.
    # So we go up (level - 1) times from the current package
    if level > 1:
        up_count = level - 1
        if up_count > len(parts):
            return None  # Can't go up beyond root
        parts = parts[:-up_count] if up_count > 0 else parts

    # Handle __init__.py case - treat as same level as parent
    if current_path.stem == "__init__":
        # For __init__.py, level=1 means same package, not parent
        # So don't change parts for level=1
        pass

    # Add the module path if specified
    if module:
        parts.extend(module.split("."))

    # Try to find matching module
    # First try as a regular .py file
    candidate = "/".join(parts) + ".py"
    if candidate in project_modules:
        return candidate

    # Try as __init__.py (package)
    candidate = "/".join(parts) + "/__init__.py"
    if candidate in project_modules:
        return candidate

    # For 'from . import foo' where foo could be a submodule
    # The module might be empty and we're importing a name from the package
    if not module:
        # Just importing from current package's __init__
        candidate = "/".join(parts) + "/__init__.py"
        if candidate in project_modules:
            return candidate

    return None


def resolve_import_to_module(
    import_info: dict,
    project_modules: List[str],
    project_name: str = "",
    current_module: str = "",
) -> Optional[str]:
    """Resolve an import to a project module path.

    Args:
        import_info: Dict from parse_python_file imports
        project_modules: List of known module paths in the project
        project_name: Name of project (for matching top-level imports)
        current_module: Path of the module containing the import (for relative imports)

    Returns:
        Module path if internal, None if external
    """
    if import_info["type"] == "import":
        # import foo.bar.baz
        name = import_info["name"]
        parts = name.split(".")

        # Check if any module path starts with this
        for mod in project_modules:
            mod_parts = mod.replace("/", ".").replace(".py", "").split(".")
            if parts[0] == mod_parts[0]:
                # Match - figure out which module
                candidate = "/".join(parts) + ".py"
                if candidate in project_modules:
                    return candidate
                # Try as package
                candidate = "/".join(parts) + "/__init__.py"
                if candidate in project_modules:
                    return candidate
        return None

    elif import_info["type"] == "from":
        # from foo.bar import baz
        module = import_info.get("module", "")
        level = import_info.get("level", 0)

        if level > 0:
            # Relative import - resolve using current module context
            if module:
                # 'from .module import x' - resolve the module
                resolved = _resolve_relative_import(
                    module, level, current_module, project_modules
                )
                return resolved
            else:
                # 'from . import x' - the names might be modules
                # Try to resolve each name as a potential module
                names = import_info.get("names", [])
                for name in names:
                    resolved = _resolve_relative_import(
                        name, level, current_module, project_modules
                    )
                    if resolved:
                        return resolved
                # Fallback to package __init__
                return _resolve_relative_import(
                    "", level, current_module, project_modules
                )

        parts = module.split(".")

        # Check project name match
        if project_name and parts[0] == project_name:
            candidate = "/".join(parts) + ".py"
            if candidate in project_modules:
                return candidate
            candidate = "/".join(parts[1:]) + ".py"  # Without project name
            if candidate in project_modules:
                return candidate

        # Check direct module match
        for mod in project_modules:
            mod_no_ext = mod.replace(".py", "").replace("/__init__", "")
            mod_dotted = mod_no_ext.replace("/", ".")
            if mod_dotted == module or mod_dotted.endswith(f".{module}"):
                return mod

        return None

    return None


def classify_external_package(import_info: dict) -> Optional[str]:
    """Extract external package name from import.

    Returns the top-level package name (e.g., "torch" from "torch.nn").
    Returns None for relative imports.
    """
    if import_info["type"] == "import":
        name = import_info["name"]
        return name.split(".")[0]

    elif import_info["type"] == "from":
        if import_info.get("level", 0) > 0:
            return None  # Relative import
        module = import_info["module"]
        return module.split(".")[0]

    return None
