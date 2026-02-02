#!/usr/bin/env python3
"""
EriRPG Project Pattern Analysis

Analyzes a codebase to detect patterns, conventions, extension points,
base classes, and registries. Stores results in .eri-rpg/patterns.json.

Usage:
    eri-rpg analyze <project>
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from erirpg.graph import Graph
from erirpg.storage import load_graph
from erirpg.registry import Registry


@dataclass
class ExtensionPoint:
    """A point where code can be extended (hooks, callbacks, overrides)."""
    name: str           # "training_hooks"
    location: str       # "trainer.py"
    methods: List[str]  # ["on_step_start", "on_step_end"]
    usage: str          # "override to hook into training loop"


@dataclass
class Registry:
    """A factory/registry pattern for registering implementations."""
    name: str           # "SchedulerFactory"
    path: str           # "training/scheduler/__init__.py"
    pattern: str        # "register(name, class)" or "@register"
    entries: List[str] = field(default_factory=list)  # Known registered items


@dataclass
class ProjectPatterns:
    """Detected patterns for a project."""
    # When analyzed
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "0.55.0-alpha"

    # Where things go
    structure: Dict[str, str] = field(default_factory=dict)
    # {"modules": "modules/{category}/{Name}.py", "configs": "config/{name}_config.py"}

    # How to create new things
    conventions: Dict[str, str] = field(default_factory=dict)
    # {"new_scheduler": "inherit BaseScheduler, implement step()"}

    # What can be extended
    extension_points: List[ExtensionPoint] = field(default_factory=list)

    # Base classes and their locations
    base_classes: Dict[str, str] = field(default_factory=dict)
    # {"BaseScheduler": "training/scheduler/base.py"}

    # Registries/factories that need updating
    registries: List[Registry] = field(default_factory=list)

    # Common imports
    common_imports: Dict[str, List[str]] = field(default_factory=dict)
    # {"torch": ["torch", "torch.nn"], "typing": ["List", "Dict", "Optional"]}

    # Test patterns
    test_patterns: Dict[str, str] = field(default_factory=dict)
    # {"location": "tests/", "naming": "test_{module}.py"}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        # Convert ExtensionPoint and Registry objects
        d['extension_points'] = [asdict(ep) for ep in self.extension_points]
        d['registries'] = [asdict(r) for r in self.registries]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ProjectPatterns':
        """Load from dict."""
        d = d.copy()
        d['extension_points'] = [ExtensionPoint(**ep) for ep in d.get('extension_points', [])]
        d['registries'] = [Registry(**r) for r in d.get('registries', [])]
        return cls(**d)


def get_patterns_path(project_path: str) -> Path:
    """Get path to patterns.json."""
    return Path(project_path) / ".eri-rpg" / "patterns.json"


def load_patterns(project_path: str) -> Optional[ProjectPatterns]:
    """Load patterns from .eri-rpg/patterns.json."""
    path = get_patterns_path(project_path)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return ProjectPatterns.from_dict(json.load(f))
    except Exception as e:
        import sys; print(f"[EriRPG] Error loading patterns: {e}", file=sys.stderr)
        return None


def save_patterns(project_path: str, patterns: ProjectPatterns):
    """Save patterns to .eri-rpg/patterns.json."""
    path = get_patterns_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(patterns.to_dict(), f, indent=2)


def analyze_project(project_path: str) -> ProjectPatterns:
    """Analyze codebase for patterns."""
    # Find project name from path
    reg = Registry.get_instance()
    project_name = None
    for name, proj in reg.projects.items():
        if proj.path == project_path:
            project_name = name
            break

    graph = load_graph(project_name) if project_name else None
    if graph is None:
        # Fallback to empty graph
        graph = Graph(modules={}, edges=[])

    patterns = ProjectPatterns(
        structure=detect_structure_patterns(project_path),
        conventions=detect_conventions(project_path, graph),
        extension_points=find_extension_points(project_path, graph),
        base_classes=find_base_classes(project_path, graph),
        registries=find_registries(project_path, graph),
        common_imports=detect_common_imports(project_path, graph),
        test_patterns=detect_test_patterns(project_path),
    )

    return patterns


def detect_structure_patterns(project_path: str) -> Dict[str, str]:
    """Detect where different types of files live."""
    patterns = {}
    path = Path(project_path)

    # Collect all Python files by directory
    dir_files: Dict[str, List[str]] = defaultdict(list)
    for py_file in path.rglob("*.py"):
        if ".eri-rpg" in str(py_file) or "__pycache__" in str(py_file):
            continue
        rel_path = py_file.relative_to(path)
        parent = str(rel_path.parent)
        dir_files[parent].append(py_file.stem)

    # Look for common patterns
    for dir_path, files in dir_files.items():
        if len(files) < 2:
            continue

        parts = dir_path.split(os.sep)

        # modules/{category}/ pattern
        if "modules" in parts or "module" in parts:
            # Check if files are CamelCase (class names)
            camel_files = [f for f in files if f[0].isupper() and f != "__init__"]
            if camel_files:
                patterns["modules"] = f"{dir_path}/{{Name}}.py"

        # schedulers/, optimizers/, etc.
        if any(p.endswith('s') and p[:-1] in ['scheduler', 'optimizer', 'loader', 'sampler', 'callback'] for p in parts):
            category = [p for p in parts if p.endswith('s')][-1]
            patterns[category] = f"{dir_path}/{{name}}.py"

        # config/ pattern
        if "config" in parts or "configs" in parts:
            patterns["configs"] = f"{dir_path}/{{name}}_config.py"

        # tests/ pattern
        if "test" in parts or "tests" in parts:
            patterns["tests"] = f"{dir_path}/test_{{name}}.py"

    return patterns


def detect_conventions(project_path: str, graph: Graph) -> Dict[str, str]:
    """Detect naming and implementation conventions."""
    conventions = {}
    path = Path(project_path)

    # Look for base classes and their expected methods
    for module_path, module_info in graph.modules.items():
        content = ""
        full_path = path / module_path
        if full_path.exists():
            try:
                content = full_path.read_text()
            except Exception:
                continue

        # Find abstract methods / required overrides
        abstract_pattern = r'@abstractmethod\s+def\s+(\w+)'
        abstracts = re.findall(abstract_pattern, content)

        if abstracts and 'base' in module_path.lower():
            class_match = re.search(r'class\s+(\w+)', content)
            if class_match:
                class_name = class_match.group(1)
                category = class_name.replace('Base', '').replace('Abstract', '').lower()
                conventions[f"new_{category}"] = f"inherit {class_name}, implement {', '.join(abstracts[:3])}"

    return conventions


def find_extension_points(project_path: str, graph: Graph) -> List[ExtensionPoint]:
    """Find hook methods, callbacks, overridable points."""
    extension_points = []
    path = Path(project_path)

    # Patterns for hooks/callbacks
    hook_patterns = [
        r'def\s+(on_\w+)\s*\(',      # on_step_start, on_epoch_end
        r'def\s+(handle_\w+)\s*\(',   # handle_event
        r'def\s+(process_\w+)\s*\(',  # process_batch
        r'def\s+(_hook_\w+)\s*\(',    # _hook_forward
    ]

    for module_path, module_info in graph.modules.items():
        full_path = path / module_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
        except Exception:
            continue

        methods = []
        for pattern in hook_patterns:
            methods.extend(re.findall(pattern, content))

        if methods:
            # Determine usage from docstrings or comments
            usage = "override to customize behavior"

            # Check if there's a docstring explaining hooks
            docstring_match = re.search(r'"""[\s\S]*?hook[\s\S]*?"""', content, re.IGNORECASE)
            if docstring_match:
                usage = docstring_match.group(0)[:100].replace('"""', '').strip()

            extension_points.append(ExtensionPoint(
                name=f"{Path(module_path).stem}_hooks",
                location=module_path,
                methods=list(set(methods))[:10],  # Limit to 10
                usage=usage,
            ))

    return extension_points


def find_base_classes(project_path: str, graph: Graph) -> Dict[str, str]:
    """Find abstract/base classes meant to be inherited."""
    base_classes = {}
    path = Path(project_path)

    # Patterns for base classes
    base_patterns = [
        r'class\s+(Base\w+)',         # BaseScheduler
        r'class\s+(\w+Base)\b',       # SchedulerBase
        r'class\s+(Abstract\w+)',     # AbstractModel
        r'class\s+(\w+)\s*\([^)]*ABC[^)]*\)',  # class Foo(ABC)
    ]

    for module_path, module_info in graph.modules.items():
        full_path = path / module_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
        except Exception:
            continue

        for pattern in base_patterns:
            matches = re.findall(pattern, content)
            for class_name in matches:
                if class_name not in base_classes:
                    base_classes[class_name] = module_path

    # Also look for classes with many subclasses
    inheritance = defaultdict(list)
    for module_path, module_info in graph.modules.items():
        full_path = path / module_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
        except Exception:
            continue

        # Find class inheritance
        class_pattern = r'class\s+\w+\s*\(([^)]+)\)'
        for match in re.findall(class_pattern, content):
            parents = [p.strip() for p in match.split(',')]
            for parent in parents:
                parent = parent.split('.')[-1]  # Remove module prefix
                if parent and parent[0].isupper():
                    inheritance[parent].append(module_path)

    # Classes with 3+ subclasses are likely base classes
    for class_name, subclass_files in inheritance.items():
        if len(subclass_files) >= 3 and class_name not in base_classes:
            # Try to find where this class is defined
            for module_path in graph.modules:
                full_path = path / module_path
                if not full_path.exists():
                    continue
                try:
                    content = full_path.read_text()
                    if re.search(rf'class\s+{class_name}\s*[:\(]', content):
                        base_classes[class_name] = module_path
                        break
                except Exception:
                    continue

    return base_classes


def find_registries(project_path: str, graph: Graph) -> List[Registry]:
    """Find factory/registry patterns."""
    registries = []
    path = Path(project_path)

    # Patterns for registries
    registry_patterns = [
        (r'class\s+(\w*Factory\w*)', "factory"),
        (r'class\s+(\w*Registry\w*)', "registry"),
        (r'(\w+)\s*=\s*\{\s*["\']', "dict_registry"),  # SCHEDULERS = {"adam": ...}
        (r'@(\w+)\.register', "decorator"),
    ]

    for module_path, module_info in graph.modules.items():
        full_path = path / module_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
        except Exception:
            continue

        for pattern, reg_type in registry_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Skip common false positives
                if match.lower() in ['self', 'cls', 'type', 'dict', 'list']:
                    continue

                # Determine pattern used
                if reg_type == "factory":
                    pattern_desc = f"{match}.create(name) or {match}.register(name, class)"
                elif reg_type == "registry":
                    pattern_desc = f"{match}.register(name, class)"
                elif reg_type == "dict_registry":
                    pattern_desc = f'{match}["name"] = class'
                else:
                    pattern_desc = f"@{match}.register"

                # Find registered entries
                entries = []
                if reg_type == "dict_registry":
                    entry_pattern = rf'{match}\s*\[\s*["\'](\w+)["\']\s*\]'
                    entries = re.findall(entry_pattern, content)

                registries.append(Registry(
                    name=match,
                    path=module_path,
                    pattern=pattern_desc,
                    entries=list(set(entries))[:20],  # Limit entries
                ))

    # Deduplicate by name
    seen = set()
    unique_registries = []
    for r in registries:
        if r.name not in seen:
            seen.add(r.name)
            unique_registries.append(r)

    return unique_registries


def detect_common_imports(project_path: str, graph: Graph) -> Dict[str, List[str]]:
    """Detect commonly used imports."""
    path = Path(project_path)
    import_counts: Dict[str, int] = defaultdict(int)

    for module_path in graph.modules:
        full_path = path / module_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
        except Exception:
            continue

        # Find imports
        import_patterns = [
            r'^import\s+(\w+)',
            r'^from\s+(\w+)',
        ]

        for pattern in import_patterns:
            for match in re.findall(pattern, content, re.MULTILINE):
                import_counts[match] += 1

    # Group by category and return most common
    common = {}

    # ML/torch imports
    torch_imports = [k for k in import_counts if 'torch' in k.lower()]
    if torch_imports:
        common['torch'] = sorted(torch_imports, key=lambda x: import_counts[x], reverse=True)[:5]

    # Typing imports
    typing_imports = [k for k in import_counts if k in ['typing', 'List', 'Dict', 'Optional', 'Any', 'Union']]
    if typing_imports:
        common['typing'] = typing_imports

    # Standard library
    stdlib = ['os', 'sys', 'json', 'pathlib', 're', 'logging', 'datetime', 'collections']
    common['stdlib'] = [k for k in stdlib if import_counts.get(k, 0) > 0]

    return common


def detect_test_patterns(project_path: str) -> Dict[str, str]:
    """Detect test file organization."""
    path = Path(project_path)
    patterns = {}

    # Find test directories
    test_dirs = list(path.glob("**/test*"))
    test_dirs = [d for d in test_dirs if d.is_dir() and "__pycache__" not in str(d)]

    if test_dirs:
        # Use the first/main test directory
        test_dir = min(test_dirs, key=lambda d: len(str(d)))
        patterns["location"] = str(test_dir.relative_to(path))

        # Check naming convention
        test_files = list(test_dir.rglob("test_*.py"))
        if test_files:
            patterns["naming"] = "test_{module}.py"
        else:
            test_files = list(test_dir.rglob("*_test.py"))
            if test_files:
                patterns["naming"] = "{module}_test.py"

    return patterns


def format_patterns(patterns: ProjectPatterns) -> str:
    """Format patterns for display."""
    lines = []
    lines.append("Project Patterns Analysis")
    lines.append("=" * 60)
    lines.append(f"Analyzed: {patterns.analyzed_at}")
    lines.append("")

    if patterns.structure:
        lines.append("Structure Patterns:")
        for category, template in patterns.structure.items():
            lines.append(f"  {category}: {template}")
        lines.append("")

    if patterns.conventions:
        lines.append("Conventions:")
        for name, convention in patterns.conventions.items():
            lines.append(f"  {name}: {convention}")
        lines.append("")

    if patterns.base_classes:
        lines.append("Base Classes:")
        for name, location in patterns.base_classes.items():
            lines.append(f"  {name}: {location}")
        lines.append("")

    if patterns.registries:
        lines.append("Registries:")
        for reg in patterns.registries:
            lines.append(f"  {reg.name} ({reg.path})")
            lines.append(f"    Pattern: {reg.pattern}")
            if reg.entries:
                lines.append(f"    Entries: {', '.join(reg.entries[:5])}")
        lines.append("")

    if patterns.extension_points:
        lines.append("Extension Points:")
        for ep in patterns.extension_points[:5]:  # Limit display
            lines.append(f"  {ep.name} ({ep.location})")
            lines.append(f"    Methods: {', '.join(ep.methods[:5])}")
            lines.append(f"    Usage: {ep.usage[:80]}")
        lines.append("")

    if patterns.test_patterns:
        lines.append("Test Patterns:")
        for key, value in patterns.test_patterns.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)
