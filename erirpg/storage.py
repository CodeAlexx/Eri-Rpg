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
SCHEMA_VERSION = 2


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

            -- =================================================================
            -- Session tracking tables (v2)
            -- =================================================================

            -- Sessions table - tracks Claude sessions for context preservation
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,  -- UUID
                project_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                phase TEXT,  -- e.g., 'implementing', 'researching', 'planning'
                step TEXT,   -- e.g., '2/5 - Add SQLite session storage'
                progress_pct INTEGER DEFAULT 0,
                summary TEXT,  -- Brief summary of what was accomplished
                files_modified TEXT,  -- JSON array of modified files
                alias TEXT,  -- Human-readable session name (optional)
                branch TEXT  -- Git branch at session start
            );

            -- Decisions made during sessions
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                context TEXT NOT NULL,  -- What was being decided
                decision TEXT NOT NULL,  -- What was chosen
                rationale TEXT,  -- Why this choice
                timestamp TEXT NOT NULL,
                archived INTEGER DEFAULT 0  -- 1 if archived after session
            );

            -- Blockers encountered during sessions
            CREATE TABLE IF NOT EXISTS blockers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                severity TEXT,  -- Optional: LOW, MEDIUM, HIGH, CRITICAL
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                resolution TEXT,  -- How it was resolved
                timestamp TEXT NOT NULL
            );

            -- Next actions queue
            CREATE TABLE IF NOT EXISTS next_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                priority INTEGER DEFAULT 0,  -- Higher = more important
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                timestamp TEXT NOT NULL
            );

            -- Learnings captured during sessions (for cross-session knowledge)
            CREATE TABLE IF NOT EXISTS session_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            -- Indexes for session queries
            CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name);
            CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
            CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);
            CREATE INDEX IF NOT EXISTS idx_blockers_session ON blockers(session_id);
            CREATE INDEX IF NOT EXISTS idx_blockers_unresolved ON blockers(resolved) WHERE resolved = 0;
            CREATE INDEX IF NOT EXISTS idx_next_actions_session ON next_actions(session_id);
            CREATE INDEX IF NOT EXISTS idx_next_actions_pending ON next_actions(completed) WHERE completed = 0;

            -- Update schema version to 2
            INSERT OR REPLACE INTO schema_version (version) VALUES (2);
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

                # Insert methods for classes (deduplicate)
                seen_methods = set()
                for method in iface.methods:
                    if method not in seen_methods:
                        seen_methods.add(method)
                        conn.execute("""
                            INSERT OR IGNORE INTO interface_methods (interface_id, method_name)
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


# =============================================================================
# Session Tracking Operations
# =============================================================================

@dataclass
class Session:
    """A Claude session for context tracking."""
    id: str
    project_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    phase: Optional[str] = None
    step: Optional[str] = None
    progress_pct: int = 0
    summary: Optional[str] = None
    files_modified: Optional[List[str]] = None
    alias: Optional[str] = None  # Human-readable name
    branch: Optional[str] = None  # Git branch at session start


@dataclass
class Decision:
    """A decision made during a session."""
    id: int
    session_id: str
    context: str
    decision: str
    rationale: Optional[str]
    timestamp: datetime
    archived: bool = False


@dataclass
class Blocker:
    """A blocker encountered during a session."""
    id: int
    session_id: str
    description: str
    severity: Optional[str]  # Optional: LOW, MEDIUM, HIGH, CRITICAL
    resolved: bool
    resolved_at: Optional[datetime]
    resolution: Optional[str]
    timestamp: datetime


@dataclass
class NextAction:
    """An action queued for future work."""
    id: int
    session_id: str
    action: str
    priority: int
    completed: bool
    completed_at: Optional[datetime]
    timestamp: datetime


def create_session(
    session_id: str,
    project_name: str,
    phase: Optional[str] = None,
    step: Optional[str] = None,
    alias: Optional[str] = None,
    branch: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Session:
    """Create a new session record."""
    init_db(db_path)
    now = datetime.now()

    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO sessions (id, project_name, started_at, phase, step, alias, branch)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, project_name, now.isoformat(), phase, step, alias, branch))
        conn.commit()

    return Session(
        id=session_id,
        project_name=project_name,
        started_at=now,
        phase=phase,
        step=step,
        alias=alias,
        branch=branch,
    )


def get_session(session_id: str, db_path: Optional[str] = None) -> Optional[Session]:
    """Get a session by ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (session_id,)).fetchone()

        if not row:
            return None

        import json
        files = json.loads(row["files_modified"]) if row["files_modified"] else None

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            phase=row["phase"],
            step=row["step"],
            progress_pct=row["progress_pct"],
            summary=row["summary"],
            files_modified=files,
            alias=row["alias"] if "alias" in row.keys() else None,
            branch=row["branch"] if "branch" in row.keys() else None,
        )


def get_latest_session(project_name: str, db_path: Optional[str] = None) -> Optional[Session]:
    """Get the most recent session for a project."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("""
            SELECT * FROM sessions
            WHERE project_name = ?
            ORDER BY started_at DESC
            LIMIT 1
        """, (project_name,)).fetchone()

        if not row:
            return None

        import json
        files = json.loads(row["files_modified"]) if row["files_modified"] else None

        return Session(
            id=row["id"],
            project_name=row["project_name"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            phase=row["phase"],
            step=row["step"],
            progress_pct=row["progress_pct"],
            summary=row["summary"],
            files_modified=files,
            alias=row["alias"] if "alias" in row.keys() else None,
            branch=row["branch"] if "branch" in row.keys() else None,
        )


def update_session(
    session_id: str,
    phase: Optional[str] = None,
    step: Optional[str] = None,
    progress_pct: Optional[int] = None,
    summary: Optional[str] = None,
    files_modified: Optional[List[str]] = None,
    ended_at: Optional[datetime] = None,
    alias: Optional[str] = None,
    branch: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Update session fields. Only non-None values are updated."""
    updates = []
    params = []

    if phase is not None:
        updates.append("phase = ?")
        params.append(phase)
    if step is not None:
        updates.append("step = ?")
        params.append(step)
    if progress_pct is not None:
        updates.append("progress_pct = ?")
        params.append(progress_pct)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if files_modified is not None:
        import json
        updates.append("files_modified = ?")
        params.append(json.dumps(files_modified))
    if ended_at is not None:
        updates.append("ended_at = ?")
        params.append(ended_at.isoformat())
    if alias is not None:
        updates.append("alias = ?")
        params.append(alias)
    if branch is not None:
        updates.append("branch = ?")
        params.append(branch)

    if not updates:
        return False

    params.append(session_id)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()
        success = cursor.rowcount > 0

    # Sync status files after state change
    if success:
        from erirpg.status_sync import sync_from_session
        sync_from_session(session_id, db_path)

    return success


def end_session(
    session_id: str,
    summary: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Mark a session as ended."""
    return update_session(
        session_id,
        ended_at=datetime.now(),
        summary=summary,
        db_path=db_path,
    )


# Decision operations

def add_decision(
    session_id: str,
    context: str,
    decision: str,
    rationale: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Decision:
    """Add a decision to a session."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO decisions (session_id, context, decision, rationale, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, context, decision, rationale, now.isoformat()))
        conn.commit()

        result = Decision(
            id=cursor.lastrowid,
            session_id=session_id,
            context=context,
            decision=decision,
            rationale=rationale,
            timestamp=now,
        )

    # Sync status files after state change
    from erirpg.status_sync import sync_from_session
    sync_from_session(session_id, db_path)

    return result


def get_session_decisions(
    session_id: str,
    include_archived: bool = False,
    db_path: Optional[str] = None,
) -> List[Decision]:
    """Get all decisions for a session."""
    with get_connection(db_path) as conn:
        if include_archived:
            rows = conn.execute("""
                SELECT * FROM decisions WHERE session_id = ? ORDER BY timestamp
            """, (session_id,))
        else:
            rows = conn.execute("""
                SELECT * FROM decisions WHERE session_id = ? AND archived = 0 ORDER BY timestamp
            """, (session_id,))

        return [
            Decision(
                id=r["id"],
                session_id=r["session_id"],
                context=r["context"],
                decision=r["decision"],
                rationale=r["rationale"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                archived=bool(r["archived"]),
            )
            for r in rows
        ]


def get_recent_decisions(
    project_name: str,
    limit: int = 10,
    db_path: Optional[str] = None,
) -> List[Decision]:
    """Get recent decisions across all sessions for a project."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT d.* FROM decisions d
            JOIN sessions s ON d.session_id = s.id
            WHERE s.project_name = ?
            ORDER BY d.timestamp DESC
            LIMIT ?
        """, (project_name, limit))

        return [
            Decision(
                id=r["id"],
                session_id=r["session_id"],
                context=r["context"],
                decision=r["decision"],
                rationale=r["rationale"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                archived=bool(r["archived"]),
            )
            for r in rows
        ]


def search_decisions(
    project_name: str,
    context_query: str,
    db_path: Optional[str] = None,
) -> List[Decision]:
    """Search decisions by context keyword."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT d.* FROM decisions d
            JOIN sessions s ON d.session_id = s.id
            WHERE s.project_name = ? AND d.context LIKE ?
            ORDER BY d.timestamp DESC
        """, (project_name, f"%{context_query}%"))

        return [
            Decision(
                id=r["id"],
                session_id=r["session_id"],
                context=r["context"],
                decision=r["decision"],
                rationale=r["rationale"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                archived=bool(r["archived"]),
            )
            for r in rows
        ]


def archive_session_decisions(session_id: str, db_path: Optional[str] = None) -> int:
    """Archive all decisions for a session."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            UPDATE decisions SET archived = 1 WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        return cursor.rowcount


# Blocker operations

def add_blocker(
    session_id: str,
    description: str,
    severity: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Blocker:
    """Add a blocker to a session."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO blockers (session_id, description, severity, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, description, severity, now.isoformat()))
        conn.commit()

        result = Blocker(
            id=cursor.lastrowid,
            session_id=session_id,
            description=description,
            severity=severity,
            resolved=False,
            resolved_at=None,
            resolution=None,
            timestamp=now,
        )

    # Sync status files after state change
    from erirpg.status_sync import sync_from_session
    sync_from_session(session_id, db_path)

    return result


def resolve_blocker(
    blocker_id: int,
    resolution: str,
    db_path: Optional[str] = None,
) -> bool:
    """Mark a blocker as resolved."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        # Get session_id before update for status sync
        row = conn.execute(
            "SELECT session_id FROM blockers WHERE id = ?", (blocker_id,)
        ).fetchone()
        session_id = row["session_id"] if row else None

        cursor = conn.execute("""
            UPDATE blockers SET resolved = 1, resolved_at = ?, resolution = ?
            WHERE id = ?
        """, (now.isoformat(), resolution, blocker_id))
        conn.commit()
        success = cursor.rowcount > 0

    # Sync status files after state change
    if success and session_id:
        from erirpg.status_sync import sync_from_session
        sync_from_session(session_id, db_path)

    return success


def get_unresolved_blockers(
    project_name: str,
    db_path: Optional[str] = None,
) -> List[Blocker]:
    """Get all unresolved blockers for a project."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT b.* FROM blockers b
            JOIN sessions s ON b.session_id = s.id
            WHERE s.project_name = ? AND b.resolved = 0
            ORDER BY
                CASE b.severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                END,
                b.timestamp DESC
        """, (project_name,))

        return [
            Blocker(
                id=r["id"],
                session_id=r["session_id"],
                description=r["description"],
                severity=r["severity"],
                resolved=bool(r["resolved"]),
                resolved_at=datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None,
                resolution=r["resolution"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]


def get_session_blockers(
    session_id: str,
    db_path: Optional[str] = None,
) -> List[Blocker]:
    """Get all blockers for a session."""
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM blockers WHERE session_id = ? ORDER BY timestamp
        """, (session_id,))

        return [
            Blocker(
                id=r["id"],
                session_id=r["session_id"],
                description=r["description"],
                severity=r["severity"],
                resolved=bool(r["resolved"]),
                resolved_at=datetime.fromisoformat(r["resolved_at"]) if r["resolved_at"] else None,
                resolution=r["resolution"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]


# Next action operations

def add_next_action(
    session_id: str,
    action: str,
    priority: int = 0,
    db_path: Optional[str] = None,
) -> NextAction:
    """Add a next action to a session."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO next_actions (session_id, action, priority, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, action, priority, now.isoformat()))
        conn.commit()

        return NextAction(
            id=cursor.lastrowid,
            session_id=session_id,
            action=action,
            priority=priority,
            completed=False,
            completed_at=None,
            timestamp=now,
        )


def complete_action(action_id: int, db_path: Optional[str] = None) -> bool:
    """Mark a next action as completed."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        # Get session_id before update for status sync
        row = conn.execute(
            "SELECT session_id FROM next_actions WHERE id = ?", (action_id,)
        ).fetchone()
        session_id = row["session_id"] if row else None

        cursor = conn.execute("""
            UPDATE next_actions SET completed = 1, completed_at = ?
            WHERE id = ?
        """, (now.isoformat(), action_id))
        conn.commit()
        success = cursor.rowcount > 0

    # Sync status files after state change
    if success and session_id:
        from erirpg.status_sync import sync_from_session
        sync_from_session(session_id, db_path)

    return success


def get_pending_actions(
    project_name: str,
    db_path: Optional[str] = None,
) -> List[NextAction]:
    """Get all pending actions for a project, ordered by priority."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT a.* FROM next_actions a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.project_name = ? AND a.completed = 0
            ORDER BY a.priority DESC, a.timestamp
        """, (project_name,))

        return [
            NextAction(
                id=r["id"],
                session_id=r["session_id"],
                action=r["action"],
                priority=r["priority"],
                completed=bool(r["completed"]),
                completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]


def get_session_actions(
    session_id: str,
    db_path: Optional[str] = None,
) -> List[NextAction]:
    """Get all actions for a session."""
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM next_actions WHERE session_id = ?
            ORDER BY priority DESC, timestamp
        """, (session_id,))

        return [
            NextAction(
                id=r["id"],
                session_id=r["session_id"],
                action=r["action"],
                priority=r["priority"],
                completed=bool(r["completed"]),
                completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in rows
        ]


# Session learning operations

def add_session_learning(
    session_id: str,
    topic: str,
    content: str,
    db_path: Optional[str] = None,
) -> int:
    """Add a learning to a session."""
    now = datetime.now()

    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO session_learnings (session_id, topic, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, topic, content, now.isoformat()))
        conn.commit()
        return cursor.lastrowid


def get_session_learnings(
    session_id: str,
    db_path: Optional[str] = None,
) -> List[dict]:
    """Get all learnings for a session."""
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM session_learnings WHERE session_id = ? ORDER BY timestamp
        """, (session_id,))

        return [
            {
                "id": r["id"],
                "topic": r["topic"],
                "content": r["content"],
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]


# Session summary helpers

def get_session_context(
    session_id: str,
    db_path: Optional[str] = None,
) -> dict:
    """Get complete context for a session including decisions, blockers, actions."""
    init_db(db_path)
    session = get_session(session_id, db_path)
    if not session:
        return {}

    return {
        "session": {
            "id": session.id,
            "project_name": session.project_name,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "phase": session.phase,
            "step": session.step,
            "progress_pct": session.progress_pct,
            "summary": session.summary,
            "files_modified": session.files_modified,
            "alias": session.alias,
            "branch": session.branch,
        },
        "decisions": [
            {
                "context": d.context,
                "decision": d.decision,
                "rationale": d.rationale,
                "timestamp": d.timestamp.isoformat(),
            }
            for d in get_session_decisions(session_id, db_path=db_path)
        ],
        "blockers": [
            {
                "description": b.description,
                "severity": b.severity,
                "resolved": b.resolved,
                "resolution": b.resolution,
            }
            for b in get_session_blockers(session_id, db_path=db_path)
        ],
        "next_actions": [
            {
                "action": a.action,
                "priority": a.priority,
                "completed": a.completed,
            }
            for a in get_session_actions(session_id, db_path=db_path)
        ],
        "learnings": get_session_learnings(session_id, db_path=db_path),
    }


def get_project_context_summary(
    project_name: str,
    db_path: Optional[str] = None,
) -> dict:
    """Get a summary of project context across recent sessions."""
    latest = get_latest_session(project_name, db_path)
    if not latest:
        return {"has_context": False}

    # Get stats
    recent_decisions = get_recent_decisions(project_name, limit=5, db_path=db_path)
    unresolved_blockers = get_unresolved_blockers(project_name, db_path=db_path)
    pending_actions = get_pending_actions(project_name, db_path=db_path)

    # Calculate time since last session
    if latest.ended_at:
        time_since = datetime.now() - latest.ended_at
    else:
        time_since = datetime.now() - latest.started_at

    hours_since = time_since.total_seconds() / 3600

    return {
        "has_context": True,
        "last_session": {
            "id": latest.id,
            "alias": latest.alias,
            "branch": latest.branch,
            "phase": latest.phase,
            "step": latest.step,
            "progress_pct": latest.progress_pct,
            "hours_ago": round(hours_since, 1),
            "was_ended": latest.ended_at is not None,
        },
        "decisions_count": len(recent_decisions),
        "blockers_count": len(unresolved_blockers),
        "blockers_high": len([b for b in unresolved_blockers if b.severity and b.severity in ("HIGH", "CRITICAL")]),
        "pending_actions": len(pending_actions),
    }
