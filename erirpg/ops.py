"""
Core operations: find, extract, impact, plan.

These operations work on indexed graphs to:
- Find modules matching capabilities
- Extract features as self-contained units
- Analyze impact of changes
- Plan transplants between projects
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Union
import json
import os
import re

from erirpg.graph import Graph, Module, Interface
from erirpg.registry import Project
from erirpg.refs import CodeRef


@dataclass
class Feature:
    """An extracted feature - self-contained unit of code.

    Features can store code in two ways:
    1. As CodeRefs (default): References to code locations, hydrated on demand
    2. As snapshots (--snapshot flag): Full code content for offline use

    Attributes:
        name: Feature name
        source_project: Source project name
        extracted_at: When the feature was extracted
        primary_module: The main module that defines the capability (query match)
        components: List of module paths in dependency order (topo-sorted)
        requires: External packages/interfaces needed
        provides: Interfaces exported by this feature (with source_module provenance)
        code_refs: Dict of path -> CodeRef (reference-based storage)
        code_snapshots: Dict of path -> str (snapshot-based storage)
    """
    name: str
    source_project: str
    extracted_at: datetime = field(default_factory=datetime.now)
    primary_module: str = ""  # The module that matched the query (defines main capability)
    components: List[str] = field(default_factory=list)  # Module paths (topo-sorted)
    requires: List[Dict] = field(default_factory=list)  # External interfaces needed
    provides: List[Dict] = field(default_factory=list)  # Interfaces with source_module provenance
    code_refs: Dict[str, CodeRef] = field(default_factory=dict)  # path -> CodeRef
    code_snapshots: Dict[str, str] = field(default_factory=dict)  # path -> code (for backwards compat)

    # Backward compatibility property
    @property
    def code(self) -> Dict[str, str]:
        """Get code dict (for backward compatibility).

        Returns snapshots if available, otherwise empty dict.
        Use hydrate_code() to get fresh code from refs.
        """
        return self.code_snapshots

    @code.setter
    def code(self, value: Dict[str, str]) -> None:
        """Set code snapshots (for backward compatibility)."""
        self.code_snapshots = value

    def hydrate_code(self, project_path: str, component: Optional[str] = None) -> Dict[str, str]:
        """Load fresh code from refs.

        Args:
            project_path: Root path of the source project
            component: If specified, only hydrate this component

        Returns:
            Dict of path -> code content
        """
        result = {}

        if component:
            # Hydrate single component
            if component in self.code_refs:
                result[component] = self.code_refs[component].hydrate(project_path)
            elif component in self.code_snapshots:
                result[component] = self.code_snapshots[component]
        else:
            # Hydrate all components
            for path in self.components:
                if path in self.code_refs:
                    try:
                        result[path] = self.code_refs[path].hydrate(project_path)
                    except FileNotFoundError:
                        # Fall back to snapshot if available
                        if path in self.code_snapshots:
                            result[path] = self.code_snapshots[path]
                elif path in self.code_snapshots:
                    result[path] = self.code_snapshots[path]

        return result

    def get_stale_components(self, project_path: str) -> List[str]:
        """Get components whose source files have changed.

        Args:
            project_path: Root path of the source project

        Returns:
            List of component paths that are stale
        """
        stale = []
        for path, ref in self.code_refs.items():
            if ref.is_stale(project_path):
                stale.append(path)
        return stale

    def save(self, path: str) -> None:
        """Save feature to JSON file."""
        data = {
            "name": self.name,
            "source_project": self.source_project,
            "extracted_at": self.extracted_at.isoformat(),
            "primary_module": self.primary_module,
            "components": self.components,
            "requires": self.requires,
            "provides": self.provides,
            "code_refs": {k: v.to_dict() for k, v in self.code_refs.items()},
        }
        # Include snapshots if present (for --snapshot mode or backward compat)
        if self.code_snapshots:
            data["code"] = self.code_snapshots
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Feature":
        """Load feature from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        # Load code_refs if present (v2 format)
        code_refs = {}
        if "code_refs" in data:
            code_refs = {k: CodeRef.from_dict(v) for k, v in data["code_refs"].items()}

        # Load code snapshots if present (v1 format or --snapshot)
        code_snapshots = data.get("code", {})

        # Backward compat: if no primary_module, use components[0] (old behavior)
        primary_module = data.get("primary_module", "")
        if not primary_module and data.get("components"):
            # Old files: provides didn't have source_module, so we can't recover
            # Just use first component as fallback (matches old buggy behavior)
            primary_module = data["components"][0]

        return cls(
            name=data["name"],
            source_project=data["source_project"],
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            primary_module=primary_module,
            components=data["components"],
            requires=data["requires"],
            provides=data["provides"],
            code_refs=code_refs,
            code_snapshots=code_snapshots,
        )


@dataclass
class Mapping:
    """A mapping between source and target module/interface."""
    source_module: str
    source_interface: str
    target_module: Optional[str]  # None = CREATE
    target_interface: Optional[str]  # None = CREATE
    action: str  # "ADAPT" | "CREATE" | "SKIP"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_module": self.source_module,
            "source_interface": self.source_interface,
            "target_module": self.target_module,
            "target_interface": self.target_interface,
            "action": self.action,
            "notes": self.notes,
        }


@dataclass
class WiringTask:
    """A wiring task for transplant."""
    file: str
    action: str
    details: str

    def to_dict(self) -> dict:
        return {"file": self.file, "action": self.action, "details": self.details}


@dataclass
class TransplantPlan:
    """Plan for transplanting a feature to a target project."""
    feature_name: str
    source_project: str
    target_project: str
    mappings: List[Mapping] = field(default_factory=list)
    wiring: List[WiringTask] = field(default_factory=list)
    generation_order: List[str] = field(default_factory=list)

    def save(self, path: str) -> None:
        """Save plan to JSON file."""
        data = {
            "feature_name": self.feature_name,
            "source_project": self.source_project,
            "target_project": self.target_project,
            "mappings": [m.to_dict() for m in self.mappings],
            "wiring": [w.to_dict() for w in self.wiring],
            "generation_order": self.generation_order,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TransplantPlan":
        """Load plan from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(
            feature_name=data["feature_name"],
            source_project=data["source_project"],
            target_project=data["target_project"],
            mappings=[Mapping(**m) for m in data["mappings"]],
            wiring=[WiringTask(**w) for w in data["wiring"]],
            generation_order=data["generation_order"],
        )


def find_modules(
    graph: Graph,
    query: str,
    limit: int = 10,
) -> List[Tuple[Module, float]]:
    """Find modules matching a query.

    Uses simple token-based scoring:
    - Summary match: 0.5 weight
    - Interface names: 0.3 weight
    - Docstrings: 0.2 weight

    Args:
        graph: Project graph
        query: Search query
        limit: Maximum results

    Returns:
        List of (Module, score) tuples, sorted by score descending
    """
    query_tokens = _tokenize(query.lower())

    results = []
    for mod in graph.modules.values():
        score = 0.0

        # Summary match (0.5 weight)
        summary_tokens = _tokenize(mod.summary.lower())
        summary_score = _jaccard(query_tokens, summary_tokens)
        score += summary_score * 0.5

        # Interface names (0.3 weight)
        iface_names = " ".join(i.name for i in mod.interfaces)
        iface_tokens = _tokenize(iface_names.lower())
        iface_score = _jaccard(query_tokens, iface_tokens)
        score += iface_score * 0.3

        # Docstrings (0.2 weight)
        docstrings = " ".join(i.docstring for i in mod.interfaces)
        doc_tokens = _tokenize(docstrings.lower())
        doc_score = _jaccard(query_tokens, doc_tokens)
        score += doc_score * 0.2

        # Boost for exact phrase in summary
        if query.lower() in mod.summary.lower():
            score += 0.3

        # Boost for path match
        path_tokens = _tokenize(mod.path.lower().replace("/", " ").replace("_", " "))
        if query_tokens & path_tokens:
            score += 0.1

        if score > 0:
            results.append((mod, score))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into words."""
    return set(re.findall(r'\w+', text))


def _jaccard(set1: Set[str], set2: Set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def extract_feature(
    graph: Graph,
    project: Project,
    query: str,
    feature_name: str,
    snapshot: bool = False,
) -> Feature:
    """Extract a feature from a project.

    Finds matching modules, includes transitive dependencies,
    and packages as a Feature with code references (or snapshots).

    Args:
        graph: Project graph
        project: Project (for reading files)
        query: Search query
        feature_name: Name for the feature
        snapshot: If True, store full code instead of refs (for offline use)

    Returns:
        Extracted Feature
    """
    # Find matching modules
    matches = find_modules(graph, query, limit=5)
    if not matches:
        raise ValueError(f"No modules match query: {query}")

    # Take top match and its dependencies
    primary = matches[0][0]
    deps = graph.get_transitive_deps(primary.path)

    # Include primary + deps
    components = [primary.path] + list(deps)

    # Topo sort for correct order (dependencies first)
    ordered = graph.topo_sort(components)

    # Create code refs (and optionally snapshots)
    code_refs = {}
    code_snapshots = {}
    for comp in ordered:
        file_path = os.path.join(project.path, comp)
        if os.path.exists(file_path):
            # Always create CodeRef for freshness tracking
            try:
                code_refs[comp] = CodeRef.from_file(project.path, comp)
            except Exception as e:
                import sys; print(f"[EriRPG] {e}", file=sys.stderr)  # Skip if can't create ref

            # Optionally include full code snapshot
            if snapshot:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code_snapshots[comp] = f.read()

    # Extract requires (external deps)
    requires = []
    external_seen = set()
    for comp in ordered:
        mod = graph.get_module(comp)
        if mod:
            for ext in mod.deps_external:
                if ext not in external_seen:
                    external_seen.add(ext)
                    requires.append({"package": ext})

    # Extract provides - interfaces from ALL components, with provenance
    # Each interface tracks which module it comes from (source_module)
    provides = []
    interface_seen = set()  # Avoid duplicates by name

    # Start with primary module's interfaces (most important)
    for iface in primary.interfaces:
        if iface.name not in interface_seen:
            interface_seen.add(iface.name)
            provides.append({
                "name": iface.name,
                "type": iface.type,
                "signature": iface.signature,
                "source_module": primary.path,  # Track provenance
            })

    # Include interfaces from dependencies (for completeness)
    for comp in ordered:
        if comp == primary.path:
            continue  # Already added
        mod = graph.get_module(comp)
        if mod:
            for iface in mod.interfaces:
                if iface.name not in interface_seen:
                    interface_seen.add(iface.name)
                    provides.append({
                        "name": iface.name,
                        "type": iface.type,
                        "signature": iface.signature,
                        "source_module": comp,  # Track provenance
                    })

    return Feature(
        name=feature_name,
        source_project=project.name,
        primary_module=primary.path,  # Track which module matched the query
        components=ordered,
        requires=requires,
        provides=provides,
        code_refs=code_refs,
        code_snapshots=code_snapshots,
    )


def analyze_impact(
    graph: Graph,
    module_path: str,
) -> Dict:
    """Analyze impact of changing a module.

    Args:
        graph: Project graph
        module_path: Module to analyze

    Returns:
        Dict with direct_dependents, transitive_dependents, risk level
    """
    module = graph.get_module(module_path)
    if not module:
        raise ValueError(f"Module not found: {module_path}")

    # Get dependents
    direct = graph.get_dependents(module_path)
    transitive = graph.get_transitive_dependents(module_path)
    transitive_only = [d for d in transitive if d not in direct]

    # Assess risk
    total = len(transitive)
    if total > 5:
        risk = "HIGH"
    elif total >= 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "module": module_path,
        "summary": module.summary,
        "interfaces": [i.name for i in module.interfaces],
        "direct_dependents": direct,
        "transitive_dependents": transitive_only,
        "total_affected": total,
        "risk": risk,
    }


def plan_transplant(
    feature: Feature,
    target_graph: Graph,
    target_project: Project,
) -> TransplantPlan:
    """Plan how to transplant a feature to a target project.

    Args:
        feature: Feature to transplant
        target_graph: Target project's graph
        target_project: Target project

    Returns:
        TransplantPlan with mappings and wiring
    """
    plan = TransplantPlan(
        feature_name=feature.name,
        source_project=feature.source_project,
        target_project=target_project.name,
    )

    # Build target interface index
    target_interfaces = {}
    for mod in target_graph.modules.values():
        for iface in mod.interfaces:
            target_interfaces[iface.name.lower()] = (mod.path, iface.name)

    # Create mappings for each provided interface
    for provided in feature.provides:
        name = provided["name"]
        name_lower = name.lower()

        # Use actual source_module from provenance (new), or fall back to primary_module
        source_module = provided.get("source_module") or feature.primary_module
        if not source_module:
            # Last resort fallback for old feature files without provenance
            source_module = feature.components[0] if feature.components else ""

        if name_lower in target_interfaces:
            # Interface exists - ADAPT
            target_mod, target_iface = target_interfaces[name_lower]
            plan.mappings.append(Mapping(
                source_module=source_module,
                source_interface=name,
                target_module=target_mod,
                target_interface=target_iface,
                action="ADAPT",
                notes=f"Existing {target_iface} in {target_mod}",
            ))
        else:
            # Interface doesn't exist - CREATE
            # Suggest a path based on the actual source module
            suggested_path = _suggest_target_path(source_module, target_project)
            plan.mappings.append(Mapping(
                source_module=source_module,
                source_interface=name,
                target_module=None,
                target_interface=None,
                action="CREATE",
                notes=f"Suggested path: {suggested_path}",
            ))

    # Check required packages
    for req in feature.requires:
        pkg = req["package"]
        # Check if any target module uses this package
        pkg_used = any(
            pkg in mod.deps_external
            for mod in target_graph.modules.values()
        )
        if not pkg_used:
            plan.wiring.append(WiringTask(
                file="requirements.txt or pyproject.toml",
                action="add_dependency",
                details=f"Add {pkg} to dependencies",
            ))

    # Compute generation order
    plan.generation_order = feature.components

    return plan


def _suggest_target_path(source_path: str, target_project: Project) -> str:
    """Suggest a target path for a new module."""
    # Simple heuristic: use filename in a logical location
    filename = os.path.basename(source_path)
    # Could be smarter based on target project structure
    return f"<appropriate_dir>/{filename}"
