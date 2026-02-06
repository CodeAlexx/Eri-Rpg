"""
Graph data structures for representing codebases.

Provides Module, Interface, Edge, and Graph classes for storing
and querying indexed project structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional, Set, FrozenSet, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from erirpg.knowledge import Knowledge


@dataclass
class Interface:
    """A public interface (class, function, method, const) in a module."""
    name: str
    type: str  # "class" | "function" | "method" | "const"
    signature: str = ""  # Full signature string
    docstring: str = ""  # First line of docstring
    methods: List[str] = field(default_factory=list)  # For classes
    line: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "signature": self.signature,
            "docstring": self.docstring,
            "methods": self.methods,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Interface":
        return cls(
            name=d["name"],
            type=d["type"],
            signature=d.get("signature", ""),
            docstring=d.get("docstring", ""),
            methods=d.get("methods", []),
            line=d.get("line", 0),
        )


@dataclass
class Module:
    """A source file/module in the project."""
    path: str  # Relative path from project root
    lang: str  # "python" | "rust" | "typescript"
    lines: int = 0
    summary: str = ""  # From module docstring
    interfaces: List[Interface] = field(default_factory=list)
    deps_internal: List[str] = field(default_factory=list)  # Modules in same project
    deps_external: List[str] = field(default_factory=list)  # External packages

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "lang": self.lang,
            "lines": self.lines,
            "summary": self.summary,
            "interfaces": [i.to_dict() for i in self.interfaces],
            "deps_internal": self.deps_internal,
            "deps_external": self.deps_external,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Module":
        return cls(
            path=d["path"],
            lang=d["lang"],
            lines=d.get("lines", 0),
            summary=d.get("summary", ""),
            interfaces=[Interface.from_dict(i) for i in d.get("interfaces", [])],
            deps_internal=d.get("deps_internal", []),
            deps_external=d.get("deps_external", []),
        )


@dataclass
class Edge:
    """A dependency edge between modules."""
    source: str  # Module path
    target: str  # Module path or external package
    edge_type: str  # "imports" | "uses" | "inherits"
    specifics: List[str] = field(default_factory=list)  # What exactly is imported

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "specifics": self.specifics,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(
            source=d["source"],
            target=d["target"],
            edge_type=d["edge_type"],
            specifics=d.get("specifics", []),
        )


@dataclass
class Graph:
    """Complete dependency graph for a project."""
    project: str
    version: str = "0.60.0"
    indexed_at: datetime = field(default_factory=datetime.now)
    modules: Dict[str, Module] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    _dependents_index: Dict[str, Set[str]] = field(default_factory=dict, repr=False)
    _knowledge: Optional["Knowledge"] = field(default=None, repr=False)
    _transitive_deps_cache: Dict[str, FrozenSet[str]] = field(default_factory=dict, repr=False)

    @property
    def knowledge(self) -> "Knowledge":
        """Get or create knowledge store."""
        if self._knowledge is None:
            from erirpg.knowledge import Knowledge
            self._knowledge = Knowledge()
        return self._knowledge

    @knowledge.setter
    def knowledge(self, value: "Knowledge") -> None:
        self._knowledge = value

    def save(self, path: str) -> None:
        """Save graph to JSON file.

        Note: As of v2, knowledge is stored separately in knowledge.json
        and is NOT included in the graph. The graph is structural-only
        and can be safely rebuilt without losing knowledge.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project": self.project,
            "version": self.version,
            "indexed_at": self.indexed_at.isoformat(),
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

        # Knowledge is NO LONGER embedded in graph.json (v2 change)
        # It is stored separately in knowledge.json to survive reindexing
        # See erirpg.memory for the new storage system

        with open(p, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Graph":
        """Load graph from JSON file.

        Note: For v1 backward compatibility, knowledge embedded in graph.json
        is still loaded. However, new code should use the separate knowledge.json
        storage via erirpg.memory. Use migration.migrate_knowledge() to move
        embedded knowledge to the new storage format.
        """
        with open(path, "r") as f:
            data = json.load(f)

        graph = cls(
            project=data["project"],
            version=data.get("version", "0.60.0"),
            indexed_at=datetime.fromisoformat(data["indexed_at"]),
            modules={k: Module.from_dict(v) for k, v in data["modules"].items()},
            edges=[Edge.from_dict(e) for e in data.get("edges", [])],
        )

        # Load knowledge if present (v1 backward compatibility)
        # New code should use erirpg.memory.load_knowledge() instead
        if "knowledge" in data:
            from erirpg.knowledge import Knowledge
            graph._knowledge = Knowledge.from_dict(data["knowledge"])

        # Build dependents index for O(1) lookups
        graph._build_dependents_index()
        return graph

    def get_module(self, path: str) -> Optional[Module]:
        """Get a module by path."""
        return self.modules.get(path)

    def add_module(self, module: Module) -> None:
        """Add a module to the graph."""
        self.modules[module.path] = module

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        # Update index
        if edge.target not in self._dependents_index:
            self._dependents_index[edge.target] = set()
        self._dependents_index[edge.target].add(edge.source)

    def _build_dependents_index(self) -> None:
        """Build reverse lookup index for get_dependents(). O(edges) once."""
        self._dependents_index = {}
        for edge in self.edges:
            if edge.target not in self._dependents_index:
                self._dependents_index[edge.target] = set()
            self._dependents_index[edge.target].add(edge.source)

    def get_deps(self, path: str) -> List[str]:
        """Get modules that this module depends on (internal only)."""
        module = self.modules.get(path)
        if not module:
            return []
        return module.deps_internal

    def get_dependents(self, path: str) -> List[str]:
        """Get modules that depend on this module. O(1) via index."""
        # Filter to only modules that exist in graph
        return [m for m in self._dependents_index.get(path, set()) 
                if m in self.modules]

    def get_transitive_deps(self, path: str) -> Set[str]:
        """Get all transitive dependencies of a module."""
        # Check cache first
        if path in self._transitive_deps_cache:
            return set(self._transitive_deps_cache[path])

        # Compute transitive deps
        visited = set()
        to_visit = [path]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            deps = self.get_deps(current)
            for dep in deps:
                if dep not in visited:
                    to_visit.append(dep)

        visited.discard(path)  # Don't include self

        # Cache result
        self._transitive_deps_cache[path] = frozenset(visited)
        return visited

    def get_transitive_dependents(self, path: str) -> Set[str]:
        """Get all modules that transitively depend on this module."""
        visited = set()
        to_visit = [path]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            dependents = self.get_dependents(current)
            for dep in dependents:
                if dep not in visited:
                    to_visit.append(dep)

        visited.discard(path)  # Don't include self
        return visited

    def topo_sort(self, modules: List[str]) -> List[str]:
        """Topologically sort modules by dependencies.

        Returns modules in order where dependencies come before dependents.
        O(V + E) using Kahn's algorithm with deque.
        """
        # Build dependency subgraph for requested modules
        module_set = set(modules)
        in_degree = {m: 0 for m in modules}
        
        # Build reverse lookup: module -> modules that depend on it (within subset)
        dependents_in_set: Dict[str, List[str]] = {m: [] for m in modules}

        for m in modules:
            deps = self.get_deps(m)
            for dep in deps:
                if dep in module_set:
                    in_degree[m] += 1
                    dependents_in_set[dep].append(m)

        # Kahn's algorithm with deque - O(1) popleft
        result = []
        queue = deque(m for m, d in in_degree.items() if d == 0)

        while queue:
            current = queue.popleft()  # O(1) instead of O(n)
            result.append(current)

            # Only check modules that actually depend on current
            for m in dependents_in_set.get(current, []):
                in_degree[m] -= 1
                if in_degree[m] == 0:
                    queue.append(m)

        # Handle cycles by appending remaining
        remaining = [m for m in modules if m not in result]
        result.extend(remaining)

        return result

    def clear_caches(self) -> None:
        """Clear caches. Call after modifying graph."""
        self._transitive_deps_cache.clear()

    def stats(self) -> dict:
        """Get graph statistics."""
        return {
            "modules": len(self.modules),
            "edges": len(self.edges),
            "total_lines": sum(m.lines for m in self.modules.values()),
            "total_interfaces": sum(len(m.interfaces) for m in self.modules.values()),
        }

    def find_modules(self, pattern: str) -> List[Module]:
        """Find modules matching a name pattern.

        Args:
            pattern: Pattern to match against module paths (supports wildcards via fnmatch)

        Returns:
            List of matching modules
        """
        import fnmatch
        results = []
        pattern_lower = pattern.lower()
        for path, module in self.modules.items():
            # Match against path
            if fnmatch.fnmatch(path.lower(), pattern_lower):
                results.append(module)
            # Also match against path segments
            elif pattern_lower in path.lower():
                results.append(module)
        return results

    def find_interface(self, name: str) -> List[tuple]:
        """Find interfaces by name across all modules.

        Args:
            name: Interface name to search (case-insensitive partial match)

        Returns:
            List of (module_path, Interface) tuples
        """
        results = []
        name_lower = name.lower()
        for module_path, module in self.modules.items():
            for iface in module.interfaces:
                if name_lower in iface.name.lower():
                    results.append((module_path, iface))
        return results

    def get_dependencies(self, path: str, include_external: bool = False) -> dict:
        """Get dependencies of a module.

        Args:
            path: Module path
            include_external: Include external package dependencies

        Returns:
            Dict with 'internal' and optionally 'external' dependency lists
        """
        module = self.get_module(path)
        if not module:
            return {"internal": [], "external": []}

        result = {"internal": module.deps_internal}
        if include_external:
            result["external"] = module.deps_external
        return result

    def impact_analysis(self, path: str, depth: Optional[int] = None) -> dict:
        """Analyze impact of changing a module.

        Args:
            path: Module path
            depth: Maximum dependency depth to analyze (None = unlimited)

        Returns:
            Dict with module info, dependents, and impact metrics
        """
        module = self.get_module(path)
        if not module:
            raise ValueError(f"Module not found: {path}")

        direct_dependents = self.get_dependents(path)
        transitive_dependents = self.get_transitive_dependents(path)

        # Filter by depth if specified
        if depth is not None:
            # BFS to get dependents within depth
            limited_dependents = set()
            current_level = {path}
            for _ in range(depth):
                next_level = set()
                for p in current_level:
                    deps = self.get_dependents(p)
                    for d in deps:
                        if d not in limited_dependents:
                            limited_dependents.add(d)
                            next_level.add(d)
                current_level = next_level
                if not current_level:
                    break
            transitive_dependents = limited_dependents
            direct_dependents = [d for d in direct_dependents if d in transitive_dependents]

        # Calculate risk level
        total_affected = len(transitive_dependents)
        if total_affected > 10:
            risk = "HIGH"
        elif total_affected >= 3:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "module": path,
            "summary": module.summary,
            "interfaces": [i.name for i in module.interfaces],
            "direct_dependents": direct_dependents,
            "transitive_dependents": list(transitive_dependents - set(direct_dependents)),
            "total_affected": total_affected,
            "risk": risk,
            "lines": module.lines,
        }

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependency chains in the graph.

        Returns:
            List of cycles, where each cycle is a list of module paths
        """
        def dfs_cycle(node: str, visited: Set[str], stack: List[str]) -> Optional[List[str]]:
            """DFS to find cycles."""
            if node in stack:
                # Found cycle - return path from node to node
                idx = stack.index(node)
                return stack[idx:] + [node]

            if node in visited:
                return None

            visited.add(node)
            stack.append(node)

            # Visit dependencies
            deps = self.get_deps(node)
            for dep in deps:
                if dep in self.modules:  # Only check internal modules
                    cycle = dfs_cycle(dep, visited, stack[:])
                    if cycle:
                        return cycle

            return None

        cycles = []
        visited = set()

        for module_path in self.modules:
            if module_path not in visited:
                cycle = dfs_cycle(module_path, visited, [])
                if cycle:
                    # Normalize cycle (start from min element)
                    min_idx = cycle.index(min(cycle[:-1]))  # Exclude duplicate last element
                    normalized = cycle[min_idx:-1] + [cycle[min_idx]]
                    # Check if we've seen this cycle before
                    if normalized not in cycles:
                        cycles.append(normalized)

        return cycles

    def orphan_modules(self) -> List[str]:
        """Find modules with no dependents (dead code candidates).

        Returns:
            List of module paths that have no dependents
        """
        orphans = []
        for module_path in self.modules:
            dependents = self.get_dependents(module_path)
            if not dependents:
                orphans.append(module_path)
        return sorted(orphans)
