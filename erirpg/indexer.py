"""
Code indexer for building dependency graphs.

Walks project directories, parses files, builds module graph
with interfaces and dependencies.
"""

import os
from pathlib import Path
from typing import List, Set, Tuple
from datetime import datetime

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg.parsers.python import (
    parse_python_file,
    resolve_import_to_module,
    classify_external_package,
)
from erirpg.parsers.c import parse_c_file, resolve_include_to_module
from erirpg.parsers.rust import parse_rust_file, resolve_use_to_module, classify_external_crate
from erirpg.parsers import get_parser_for_file, detect_language
from erirpg.registry import Project


# Standard library modules to ignore as external deps
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
    "base64", "binascii", "bisect", "builtins", "bz2",
    "calendar", "cgi", "cgitb", "chunk", "cmath", "code", "codecs",
    "codeop", "collections", "colorsys", "compileall", "concurrent",
    "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "cProfile", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "doctest", "email", "encodings", "enum", "errno",
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "grp", "gzip",
    "hashlib", "heapq", "hmac", "html", "http",
    "imaplib", "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
    "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder",
    "multiprocessing", "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
    "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
    "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors", "shelve", "shlex",
    "shutil", "signal", "site", "smtplib", "sndhdr", "socket", "socketserver",
    "spwd", "sqlite3", "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize", "trace",
    "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
    "unicodedata", "unittest", "urllib", "uu", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    # Typing extensions
    "typing_extensions",
}


def index_project(project: Project, verbose: bool = False) -> Graph:
    """Index a project and build its dependency graph.

    This function rebuilds the structural index (graph.json) from source files.
    Knowledge (stored in knowledge.json) is PRESERVED and NOT modified by
    reindexing - it exists independently of the structural graph.

    Args:
        project: Project to index
        verbose: Print progress

    Returns:
        The built Graph

    Note:
        If you have v1 knowledge embedded in graph.json, run migration first:
        >>> from erirpg.migration import auto_migrate_if_needed
        >>> auto_migrate_if_needed(project.path, project.name)
    """
    # Check for v1 knowledge that needs migration
    from erirpg.migration import check_migration_needed, auto_migrate_if_needed

    needs_migration, reason = check_migration_needed(project.path)
    if needs_migration:
        if verbose:
            print(f"Migrating v1 knowledge to separate storage...")
        result = auto_migrate_if_needed(project.path, project.name)
        if result and result.get("migrated"):
            if verbose:
                print(f"  Migrated {result['learnings']} learnings, "
                      f"{result['decisions']} decisions, "
                      f"{result['patterns']} patterns")

    # Create new graph (structural only - knowledge is separate)
    graph = Graph(project=project.name)

    # Find all source files based on language
    if project.lang == "python":
        source_files = _find_python_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} Python files")
    elif project.lang == "c":
        source_files = _find_c_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} C/C++ files")
    elif project.lang == "rust":
        source_files = _find_rust_files(project.path)
        if verbose:
            print(f"Found {len(source_files)} Rust files")
    else:
        raise NotImplementedError(f"Language '{project.lang}' not yet supported")

    # Collect all module paths first
    module_paths = set()
    for file_path in source_files:
        rel_path = os.path.relpath(file_path, project.path)
        module_paths.add(rel_path)

    # Parse each file
    for file_path in source_files:
        rel_path = os.path.relpath(file_path, project.path)

        if verbose:
            print(f"  Parsing {rel_path}")

        try:
            # Get appropriate parser
            parser = get_parser_for_file(file_path)
            if not parser:
                if verbose:
                    print(f"    Skipped (no parser)")
                continue
            parsed = parser(file_path)
        except Exception as e:
            if verbose:
                print(f"    Error: {e}")
            continue

        # Create interfaces
        interfaces = []
        for iface in parsed.get("interfaces", []):
            interfaces.append(Interface(
                name=iface["name"],
                type=iface["type"],
                signature=iface.get("signature", ""),
                docstring=iface.get("docstring", ""),
                methods=iface.get("methods", []),
                line=iface.get("line", 0),
            ))

        # Resolve imports based on language
        deps_internal = []
        deps_external = set()

        for imp in parsed.get("imports", []):
            if project.lang == "python":
                resolved = resolve_import_to_module(
                    imp, list(module_paths), project.name, rel_path
                )
                if resolved:
                    deps_internal.append(resolved)
                else:
                    pkg = classify_external_package(imp)
                    if pkg and pkg not in STDLIB_MODULES:
                        deps_external.add(pkg)
            elif project.lang == "c":
                resolved = resolve_include_to_module(imp, list(module_paths))
                if resolved:
                    deps_internal.append(resolved)
                elif not imp.get("is_system"):
                    deps_external.add(imp["name"])
            elif project.lang == "rust":
                resolved = resolve_use_to_module(imp, list(module_paths))
                if resolved:
                    deps_internal.append(resolved)
                else:
                    crate = classify_external_crate(imp)
                    if crate:
                        deps_external.add(crate)

        module = Module(
            path=rel_path,
            lang=project.lang,
            lines=parsed.get("lines", 0),
            summary=parsed.get("docstring", ""),
            interfaces=interfaces,
            deps_internal=list(set(deps_internal)),
            deps_external=list(deps_external),
        )

        graph.add_module(module)

    # Build edges from internal deps
    for mod_path, module in graph.modules.items():
        for dep in module.deps_internal:
            edge = Edge(
                source=mod_path,
                target=dep,
                edge_type="imports",
                specifics=[],  # Could populate from parsed imports
            )
            graph.add_edge(edge)

    # Save graph
    graph.indexed_at = datetime.now()
    graph.save(project.graph_path)

    if verbose:
        stats = graph.stats()
        print(f"Indexed: {stats['modules']} modules, {stats['edges']} edges, "
              f"{stats['total_lines']} lines, {stats['total_interfaces']} interfaces")

    return graph


def _find_python_files(root: str) -> List[str]:
    """Find all Python files in a directory tree.

    Excludes:
    - __pycache__ directories
    - .git directories
    - .eri-rpg directories
    - Virtual environments (venv, .venv, env)
    - Build directories (build, dist, *.egg-info)
    """
    exclude_dirs = {
        "__pycache__", ".git", ".eri-rpg", "venv", ".venv", "env",
        "build", "dist", "node_modules", ".tox", ".pytest_cache",
    }

    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs and not d.endswith(".egg-info")
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                py_files.append(os.path.join(dirpath, filename))

    return py_files


def _find_c_files(root: str) -> List[str]:
    """Find all C/C++ files in a directory tree.

    Includes: .c, .h, .cpp, .hpp, .cc, .hh
    Excludes: build directories, .git, etc.
    """
    exclude_dirs = {
        ".git", ".eri-rpg", "build", "cmake-build-debug", "cmake-build-release",
        "node_modules", ".vscode", ".idea", "third_party", "vendor", "deps",
    }

    c_extensions = {".c", ".h", ".cpp", ".hpp", ".cc", ".hh"}
    c_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext in c_extensions:
                c_files.append(os.path.join(dirpath, filename))

    return c_files


def _find_rust_files(root: str) -> List[str]:
    """Find all Rust files in a directory tree.

    Includes: .rs files
    Excludes: target directory, .git, etc.
    """
    exclude_dirs = {
        ".git", ".eri-rpg", "target", "node_modules", ".vscode", ".idea",
    }

    rs_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs
        ]

        for filename in filenames:
            if filename.endswith(".rs"):
                rs_files.append(os.path.join(dirpath, filename))

    return rs_files


def get_or_load_graph(project: Project) -> Graph:
    """Get project graph, loading from disk if exists."""
    if project.is_indexed() and os.path.exists(project.graph_path):
        return Graph.load(project.graph_path)
    raise ValueError(f"Project '{project.name}' is not indexed. Run: eri-rpg index {project.name}")
