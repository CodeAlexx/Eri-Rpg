"""
SQLite storage layer for EriRPG graphs.

Provides a single global database at ~/.eri-rpg/graphs.db that stores
all project graphs with indexed cross-project queries.

Benefits over JSON:
- O(log n) indexed queries vs O(n) JSON scans
- ~50-70% smaller storage
- Fast cross-project queries
- No need to load full graph into memory
"""

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from erirpg.graph import Graph, Module, Interface, Edge


# Default database path
DEFAULT_DB_PATH = os.path.expanduser("~/.eri-rpg/graphs.db")

# Schema version for migrations
SCHEMA_VERSION = 1


def get_db_path() -> str:
    """Get the database path, respecting ERI_RPG_DB env var."""
    return os.environ.get("ERI_RPG_DB", DEFAULT_DB_PATH)


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Get a database connection with proper settings.

    Uses WAL mode for better concurrent access.
    """
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize the database schema.

    Creates tables and indexes if they don't exist.
    Safe to call multiple times.
    """
    with get_connection(db_path) as conn:
        conn.executescript("""
            -- Schema version tracking
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );

            -- Projects table
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                lang TEXT NOT NULL,
                version TEXT DEFAULT '0.55.0-alpha',
                indexed_at TEXT NOT NULL
            );

            -- Modules table
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                lang TEXT NOT NULL,
                lines INTEGER DEFAULT 0,
                summary TEXT DEFAULT '',
                UNIQUE(project_id, path)
            );

            -- Interfaces table (classes, functions, methods, consts)
            CREATE TABLE IF NOT EXISTS interfaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                signature TEXT DEFAULT '',
                docstring TEXT DEFAULT '',
                line INTEGER DEFAULT 0
            );

            -- Interface methods (for classes)
            CREATE TABLE IF NOT EXISTS interface_methods (
                interface_id INTEGER NOT NULL REFERENCES interfaces(id) ON DELETE CASCADE,
                method_name TEXT NOT NULL,
                PRIMARY KEY (interface_id, method_name)
            );

            -- Edges (dependency relationships between modules)
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                target_module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                edge_type TEXT NOT NULL,
                UNIQUE(source_module_id, target_module_id, edge_type)
            );

            -- Edge specifics (what exactly is imported)
            CREATE TABLE IF NOT EXISTS edge_specifics (
                edge_id INTEGER NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
                specific TEXT NOT NULL,
                PRIMARY KEY (edge_id, specific)
            );

            -- External dependencies
            CREATE TABLE IF NOT EXISTS deps_external (
                module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                package TEXT NOT NULL,
                PRIMARY KEY (module_id, package)
            );

            -- Internal dependencies (denormalized for faster queries)
            CREATE TABLE IF NOT EXISTS deps_internal (
                module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                dep_path TEXT NOT NULL,
                PRIMARY KEY (module_id, dep_path)
            );

            -- Indexes for fast cross-project queries
            CREATE INDEX IF NOT EXISTS idx_modules_project ON modules(project_id);
            CREATE INDEX IF NOT EXISTS idx_modules_path ON modules(path);
            CREATE INDEX IF NOT EXISTS idx_interfaces_module ON interfaces(module_id);
            CREATE INDEX IF NOT EXISTS idx_interfaces_name ON interfaces(name);
            CREATE INDEX IF NOT EXISTS idx_interfaces_type ON interfaces(type);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_module_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_module_id);
            CREATE INDEX IF NOT EXISTS idx_deps_external_package ON deps_external(package);
            CREATE INDEX IF NOT EXISTS idx_deps_internal_dep ON deps_internal(dep_path);

            -- Set schema version
            INSERT OR REPLACE INTO schema_version (version) VALUES (1);
        """)
        conn.commit()


def get_schema_version(db_path: Optional[str] = None) -> int:
    """Get current schema version, or 0 if not initialized."""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            return row["version"] if row else 0
    except sqlite3.OperationalError:
        return 0


# =============================================================================
# Write Operations
# =============================================================================

def save_graph(graph: Graph, db_path: Optional[str] = None) -> None:
    """Save a graph to the SQLite database.

    Replaces any existing data for this project.
    """
    init_db(db_path)

    with get_connection(db_path) as conn:
        # Delete existing project data (cascades to all related tables)
        conn.execute("DELETE FROM projects WHERE name = ?", (graph.project,))

        # Insert project
        cursor = conn.execute("""
            INSERT INTO projects (name, path, lang, version, indexed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            graph.project,
            "",  # Path will be set by registry, not graph
            next(iter(graph.modules.values())).lang if graph.modules else "python",
            graph.version,
            graph.indexed_at.isoformat(),
        ))
        project_id = cursor.lastrowid

        # Map module paths to IDs for edge references
        module_ids: Dict[str, int] = {}

        # Insert modules
        for module in graph.modules.values():
            cursor = conn.execute("""
                INSERT INTO modules (project_id, path, lang, lines, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, module.path, module.lang, module.lines, module.summary))
            module_id = cursor.lastrowid
            module_ids[module.path] = module_id

            # Insert interfaces
            for iface in module.interfaces:
                cursor = conn.execute("""
                    INSERT INTO interfaces (module_id, name, type, signature, docstring, line)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (module_id, iface.name, iface.type, iface.signature, iface.docstring, iface.line))
                iface_id = cursor.lastrowid

                # Insert methods for classes
                for method in iface.methods:
                    conn.execute("""
                        INSERT INTO interface_methods (interface_id, method_name)
                        VALUES (?, ?)
                    """, (iface_id, method))

            # Insert external deps
            for pkg in module.deps_external:
                conn.execute("""
                    INSERT INTO deps_external (module_id, package)
                    VALUES (?, ?)
                """, (module_id, pkg))

            # Insert internal deps
            for dep in module.deps_internal:
                conn.execute("""
                    INSERT INTO deps_internal (module_id, dep_path)
                    VALUES (?, ?)
                """, (module_id, dep))

        # Insert edges
        for edge in graph.edges:
            source_id = module_ids.get(edge.source)
            target_id = module_ids.get(edge.target)

            if source_id and target_id:
                cursor = conn.execute("""
                    INSERT OR IGNORE INTO edges (source_module_id, target_module_id, edge_type)
                    VALUES (?, ?, ?)
                """, (source_id, target_id, edge.edge_type))
                edge_id = cursor.lastrowid

                if edge_id:
                    for specific in edge.specifics:
                        conn.execute("""
                            INSERT OR IGNORE INTO edge_specifics (edge_id, specific)
                            VALUES (?, ?)
                        """, (edge_id, specific))

        conn.commit()


def delete_project(project_name: str, db_path: Optional[str] = None) -> bool:
    """Delete a project and all its data from the database.

    Returns True if project was deleted, False if not found.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM projects WHERE name = ?", (project_name,))
        conn.commit()
        return cursor.rowcount > 0


# =============================================================================
# Read Operations - Single Project
# =============================================================================

def load_graph(project_name: str, db_path: Optional[str] = None) -> Optional[Graph]:
    """Load a graph from the database.

    Returns None if project not found.
    """
    with get_connection(db_path) as conn:
        # Get project
        proj = conn.execute("""
            SELECT id, name, version, indexed_at FROM projects WHERE name = ?
        """, (project_name,)).fetchone()

        if not proj:
            return None

        project_id = proj["id"]

        # Load modules
        modules: Dict[str, Module] = {}
        for row in conn.execute("""
            SELECT id, path, lang, lines, summary FROM modules WHERE project_id = ?
        """, (project_id,)):
            module_id = row["id"]

            # Load interfaces
            interfaces = []
            for iface_row in conn.execute("""
                SELECT id, name, type, signature, docstring, line
                FROM interfaces WHERE module_id = ?
            """, (module_id,)):
                # Load methods
                methods = [m["method_name"] for m in conn.execute("""
                    SELECT method_name FROM interface_methods WHERE interface_id = ?
                """, (iface_row["id"],))]

                interfaces.append(Interface(
                    name=iface_row["name"],
                    type=iface_row["type"],
                    signature=iface_row["signature"],
                    docstring=iface_row["docstring"],
                    methods=methods,
                    line=iface_row["line"],
                ))

            # Load deps
            deps_external = [r["package"] for r in conn.execute("""
                SELECT package FROM deps_external WHERE module_id = ?
            """, (module_id,))]

            deps_internal = [r["dep_path"] for r in conn.execute("""
                SELECT dep_path FROM deps_internal WHERE module_id = ?
            """, (module_id,))]

            modules[row["path"]] = Module(
                path=row["path"],
                lang=row["lang"],
                lines=row["lines"],
                summary=row["summary"],
                interfaces=interfaces,
                deps_internal=deps_internal,
                deps_external=deps_external,
            )

        # Load edges
        edges = []
        for edge_row in conn.execute("""
            SELECT e.id, src.path as source, tgt.path as target, e.edge_type
            FROM edges e
            JOIN modules src ON e.source_module_id = src.id
            JOIN modules tgt ON e.target_module_id = tgt.id
            WHERE src.project_id = ?
        """, (project_id,)):
            specifics = [s["specific"] for s in conn.execute("""
                SELECT specific FROM edge_specifics WHERE edge_id = ?
            """, (edge_row["id"],))]

            edges.append(Edge(
                source=edge_row["source"],
                target=edge_row["target"],
                edge_type=edge_row["edge_type"],
                specifics=specifics,
            ))

        graph = Graph(
            project=proj["name"],
            version=proj["version"],
            indexed_at=datetime.fromisoformat(proj["indexed_at"]),
            modules=modules,
            edges=edges,
        )
        graph._build_dependents_index()
        return graph


def get_module(project_name: str, module_path: str, db_path: Optional[str] = None) -> Optional[Module]:
    """Get a single module without loading the full graph."""
    with get_connection(db_path) as conn:
        row = conn.execute("""
            SELECT m.id, m.path, m.lang, m.lines, m.summary
            FROM modules m
            JOIN projects p ON m.project_id = p.id
            WHERE p.name = ? AND m.path = ?
        """, (project_name, module_path)).fetchone()

        if not row:
            return None

        module_id = row["id"]

        # Load interfaces
        interfaces = []
        for iface_row in conn.execute("""
            SELECT id, name, type, signature, docstring, line
            FROM interfaces WHERE module_id = ?
        """, (module_id,)):
            methods = [m["method_name"] for m in conn.execute("""
                SELECT method_name FROM interface_methods WHERE interface_id = ?
            """, (iface_row["id"],))]

            interfaces.append(Interface(
                name=iface_row["name"],
                type=iface_row["type"],
                signature=iface_row["signature"],
                docstring=iface_row["docstring"],
                methods=methods,
                line=iface_row["line"],
            ))

        deps_external = [r["package"] for r in conn.execute("""
            SELECT package FROM deps_external WHERE module_id = ?
        """, (module_id,))]

        deps_internal = [r["dep_path"] for r in conn.execute("""
            SELECT dep_path FROM deps_internal WHERE module_id = ?
        """, (module_id,))]

        return Module(
            path=row["path"],
            lang=row["lang"],
            lines=row["lines"],
            summary=row["summary"],
            interfaces=interfaces,
            deps_internal=deps_internal,
            deps_external=deps_external,
        )


# =============================================================================
# Cross-Project Queries
# =============================================================================

@dataclass
class CrossProjectResult:
    """Result from a cross-project query."""
    project: str
    module_path: str
    match_name: str
    match_type: str
    line: int = 0
    context: str = ""


def find_interface_across_projects(
    name: str,
    interface_type: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[CrossProjectResult]:
    """Find interfaces by name across all projects.

    Args:
        name: Interface name to search (supports LIKE patterns with %)
        interface_type: Optional filter by type (class, function, method, const)

    Returns:
        List of matching results with project and module info
    """
    with get_connection(db_path) as conn:
        if interface_type:
            rows = conn.execute("""
                SELECT p.name as project, m.path as module_path,
                       i.name, i.type, i.line, i.docstring
                FROM interfaces i
                JOIN modules m ON i.module_id = m.id
                JOIN projects p ON m.project_id = p.id
                WHERE i.name LIKE ? AND i.type = ?
                ORDER BY p.name, m.path
            """, (name, interface_type))
        else:
            rows = conn.execute("""
                SELECT p.name as project, m.path as module_path,
                       i.name, i.type, i.line, i.docstring
                FROM interfaces i
                JOIN modules m ON i.module_id = m.id
                JOIN projects p ON m.project_id = p.id
                WHERE i.name LIKE ?
                ORDER BY p.name, m.path
            """, (name,))

        return [
            CrossProjectResult(
                project=r["project"],
                module_path=r["module_path"],
                match_name=r["name"],
                match_type=r["type"],
                line=r["line"],
                context=r["docstring"],
            )
            for r in rows
        ]


def find_external_dep_usage(
    package: str,
    db_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Find all modules across projects that use an external package.

    Args:
        package: Package name to search for

    Returns:
        List of (project_name, module_path) tuples
    """
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT p.name as project, m.path as module_path
            FROM deps_external d
            JOIN modules m ON d.module_id = m.id
            JOIN projects p ON m.project_id = p.id
            WHERE d.package = ?
            ORDER BY p.name, m.path
        """, (package,))

        return [(r["project"], r["module_path"]) for r in rows]


def find_dependents_across_projects(
    module_path: str,
    db_path: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Find all modules across projects that depend on a given module path.

    This is useful for finding impact across projects when a commonly-used
    module pattern exists in multiple codebases.

    Args:
        module_path: Module path to search for dependents of

    Returns:
        List of (project_name, dependent_module_path) tuples
    """
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT p.name as project, m.path as module_path
            FROM deps_internal d
            JOIN modules m ON d.module_id = m.id
            JOIN projects p ON m.project_id = p.id
            WHERE d.dep_path = ?
            ORDER BY p.name, m.path
        """, (module_path,))

        return [(r["project"], r["module_path"]) for r in rows]


def get_project_stats(db_path: Optional[str] = None) -> Dict[str, dict]:
    """Get statistics for all projects in the database.

    Returns:
        Dict mapping project name to stats dict with keys:
        - modules: number of modules
        - interfaces: number of interfaces
        - edges: number of edges
        - lines: total lines of code
        - indexed_at: when last indexed
    """
    with get_connection(db_path) as conn:
        stats = {}

        for proj in conn.execute("SELECT id, name, indexed_at FROM projects"):
            project_id = proj["id"]

            module_count = conn.execute("""
                SELECT COUNT(*) as c FROM modules WHERE project_id = ?
            """, (project_id,)).fetchone()["c"]

            interface_count = conn.execute("""
                SELECT COUNT(*) as c FROM interfaces i
                JOIN modules m ON i.module_id = m.id
                WHERE m.project_id = ?
            """, (project_id,)).fetchone()["c"]

            edge_count = conn.execute("""
                SELECT COUNT(*) as c FROM edges e
                JOIN modules m ON e.source_module_id = m.id
                WHERE m.project_id = ?
            """, (project_id,)).fetchone()["c"]

            total_lines = conn.execute("""
                SELECT COALESCE(SUM(lines), 0) as c FROM modules WHERE project_id = ?
            """, (project_id,)).fetchone()["c"]

            stats[proj["name"]] = {
                "modules": module_count,
                "interfaces": interface_count,
                "edges": edge_count,
                "lines": total_lines,
                "indexed_at": proj["indexed_at"],
            }

        return stats


def get_db_stats(db_path: Optional[str] = None) -> dict:
    """Get overall database statistics.

    Returns:
        Dict with keys: projects, total_modules, total_interfaces,
        total_edges, db_size_bytes
    """
    path = db_path or get_db_path()

    with get_connection(db_path) as conn:
        projects = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
        modules = conn.execute("SELECT COUNT(*) as c FROM modules").fetchone()["c"]
        interfaces = conn.execute("SELECT COUNT(*) as c FROM interfaces").fetchone()["c"]
        edges = conn.execute("SELECT COUNT(*) as c FROM edges").fetchone()["c"]

    size = os.path.getsize(path) if os.path.exists(path) else 0

    return {
        "projects": projects,
        "total_modules": modules,
        "total_interfaces": interfaces,
        "total_edges": edges,
        "db_size_bytes": size,
    }


# =============================================================================
# Migration from JSON
# =============================================================================

def migrate_from_json(json_path: str, project_name: str, db_path: Optional[str] = None) -> bool:
    """Migrate a JSON graph file to the SQLite database.

    Args:
        json_path: Path to the graph.json file
        project_name: Name of the project

    Returns:
        True if migration succeeded, False if file not found
    """
    if not os.path.exists(json_path):
        return False

    graph = Graph.load(json_path)
    graph.project = project_name  # Ensure correct project name
    save_graph(graph, db_path)
    return True


def migrate_all_projects(registry_path: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, bool]:
    """Migrate all registered projects from JSON to SQLite.

    Args:
        registry_path: Path to registry.json (default: ~/.eri-rpg/registry.json)

    Returns:
        Dict mapping project name to success status
    """
    import json

    reg_path = registry_path or os.path.expanduser("~/.eri-rpg/registry.json")
    if not os.path.exists(reg_path):
        return {}

    with open(reg_path) as f:
        registry = json.load(f)

    results = {}
    for name, proj in registry.get("projects", {}).items():
        graph_path = proj.get("graph_path", "")
        if graph_path and os.path.exists(graph_path):
            results[name] = migrate_from_json(graph_path, name, db_path)
        else:
            results[name] = False

    return results


# =============================================================================
# Export to JSON
# =============================================================================

def export_to_json(project_name: str, output_path: str, db_path: Optional[str] = None) -> bool:
    """Export a project's graph to JSON format.

    Args:
        project_name: Name of the project to export
        output_path: Path to write the JSON file

    Returns:
        True if export succeeded, False if project not found
    """
    graph = load_graph(project_name, db_path)
    if not graph:
        return False

    graph.save(output_path)
    return True
