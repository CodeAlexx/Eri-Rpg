# EriRPG Design Document

## Overview

EriRPG is a lean CLI tool (~1500 lines Python) for cross-project feature transplant.
No LLM. Pure Python. Claude Code is the LLM.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 CLI (cli.py + cli_commands/)                 │
│  91+ commands across 26 modular modules                     │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Registry       │  │  Indexer        │  │  Operations     │
│  (registry.py)  │  │  (indexer.py)   │  │  (ops.py)       │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ add_project()   │  │ index_python()  │  │ find()          │
│ remove_project()│  │ index_rust()    │  │ extract()       │
│ list_projects() │  │ index_ts()      │  │ impact()        │
│ get_project()   │  │ build_graph()   │  │ plan()          │
└─────────────────┘  └─────────────────┘  │ context()       │
                              │           └─────────────────┘
                              ▼
                     ┌─────────────────┐
                     │  Graph          │
                     │  (graph.py)     │
                     ├─────────────────┤
                     │ Module          │
                     │ Edge            │
                     │ Interface       │
                     │ Graph.save()    │
                     │ Graph.load()    │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  State          │
                     │  (state.py)     │
                     ├─────────────────┤
                     │ current_task    │
                     │ phase           │
                     │ waiting_on      │
                     │ history         │
                     └─────────────────┘
```

## File Structure

```
eri-rpg/
├── erirpg/
│   ├── __init__.py       # Version, exports
│   ├── cli.py            # Click CLI entry point
│   ├── cli_commands/     # 26 modular command modules
│   ├── registry.py       # Project registry (150 lines)
│   ├── indexer.py        # Code indexing (400 lines)
│   ├── graph.py          # Graph data structures (200 lines)
│   ├── ops.py            # Core operations (300 lines)
│   ├── state.py          # State tracking (100 lines)
│   ├── context.py        # Context generation (150 lines)
│   └── parsers/
│       ├── __init__.py
│       ├── python.py     # AST-based Python parser (200 lines)
│       ├── rust.py       # tree-sitter Rust parser (150 lines)
│       └── typescript.py # tree-sitter TS parser (150 lines)
├── pyproject.toml
├── README.md
└── tests/
    ├── test_registry.py
    ├── test_indexer.py
    └── test_ops.py

Total: ~1500 lines
```

## Data Structures

### Registry (`~/.eri-rpg/registry.json`)

```python
@dataclass
class Project:
    name: str           # Unique identifier
    path: str           # Absolute path to project root
    lang: str           # "python" | "rust" | "typescript"
    indexed_at: Optional[datetime]  # Last index time
    graph_path: str     # Path to graph.json

@dataclass
class Registry:
    projects: Dict[str, Project]
    config_dir: str = "~/.eri-rpg"

    def add(self, name: str, path: str, lang: str) -> Project
    def remove(self, name: str) -> bool
    def get(self, name: str) -> Optional[Project]
    def list(self) -> List[Project]
    def save(self) -> None
    def load(self) -> None
```

### Graph (`<project>/.eri-rpg/graph.json`)

```python
@dataclass
class Interface:
    name: str           # "FluxModel", "forward", etc.
    type: str           # "class" | "function" | "method" | "const"
    signature: str      # "def forward(self, batch: Dict) -> Tensor"
    docstring: str      # First line of docstring

@dataclass
class Module:
    path: str           # Relative path from project root
    lang: str           # "python" | "rust" | "typescript"
    lines: int          # Line count
    summary: str        # From module docstring
    interfaces: List[Interface]
    deps_internal: List[str]    # Modules in same project
    deps_external: List[str]    # External packages

@dataclass
class Edge:
    source: str         # Module path
    target: str         # Module path or external package
    edge_type: str      # "imports" | "uses" | "inherits"
    specifics: List[str]  # What exactly is imported

@dataclass
class Graph:
    project: str
    version: str
    indexed_at: datetime
    modules: Dict[str, Module]
    edges: List[Edge]

    def save(self, path: str) -> None
    @classmethod
    def load(cls, path: str) -> 'Graph'

    def get_module(self, path: str) -> Optional[Module]
    def get_deps(self, path: str) -> List[str]
    def get_dependents(self, path: str) -> List[str]
    def topo_sort(self, modules: List[str]) -> List[str]
```

### Feature (extracted unit)

```python
@dataclass
class Feature:
    name: str
    source_project: str
    extracted_at: datetime
    components: List[str]       # Module paths
    requires: List[Interface]   # External interfaces needed
    provides: List[Interface]   # Interfaces exported
    code: Dict[str, str]        # path -> code content

    def save(self, path: str) -> None
    @classmethod
    def load(cls, path: str) -> 'Feature'
```

### Transplant Plan

```python
@dataclass
class Mapping:
    source_module: str
    source_interface: str
    target_module: Optional[str]  # None = CREATE
    target_interface: Optional[str]  # None = CREATE
    action: str  # "ADAPT" | "CREATE" | "SKIP"
    notes: str

@dataclass
class WiringTask:
    file: str
    action: str
    details: str

@dataclass
class TransplantPlan:
    feature: str
    source_project: str
    target_project: str
    mappings: List[Mapping]
    wiring: List[WiringTask]
    generation_order: List[str]  # Topo sorted

    def save(self, path: str) -> None
    @classmethod
    def load(cls, path: str) -> 'TransplantPlan'
```

### State (orchestration tracking)

```python
@dataclass
class State:
    current_task: Optional[str]
    phase: str  # "idle" | "extracting" | "planning" | "implementing" | "validating"
    waiting_on: Optional[str]  # "user" | "claude" | None
    history: List[Dict]  # Action log
    context_file: Optional[str]  # Generated context path

    def update(self, **kwargs) -> None
    def log(self, action: str, details: str) -> None
    def save(self) -> None
    @classmethod
    def load(cls) -> 'State'
```

## Core Operations

### `index(project: str) -> Graph`

1. Get project from registry
2. Walk project directory
3. For each file matching lang:
   - Parse with appropriate parser
   - Extract interfaces, imports, docstrings
   - Create Module node
4. Build edges from imports
5. Save graph to project/.eri-rpg/graph.json

### `find(project: str, query: str) -> List[Tuple[Module, float]]`

1. Load graph
2. For each module:
   - Score = match_summary(query) * 0.5 + match_interfaces(query) * 0.3 + match_docstrings(query) * 0.2
3. Return sorted by score

**Matching algorithm:**
- Tokenize query and target
- Jaccard similarity on tokens
- Boost for exact phrase matches
- No LLM - pure string matching

### `extract(project: str, query: str, output: str) -> Feature`

1. Find matching modules
2. For top match:
   - Get transitive dependencies (internal only)
   - Topo sort for order
3. Read code for each module
4. Extract interfaces (what it provides)
5. Extract requirements (external deps)
6. Save as Feature JSON

### `impact(project: str, module_path: str) -> Dict`

1. Load graph
2. BFS from module to find dependents
3. Classify: direct (distance=1), transitive (distance>1)
4. Assess risk: HIGH (>5 dependents), MEDIUM (2-5), LOW (<2)
5. Return structured report

### `plan(feature_path: str, target_project: str) -> TransplantPlan`

1. Load feature and target graph
2. For each component in feature:
   - Find matching module in target (by name/interface similarity)
   - If match: ADAPT, note differences
   - If no match: CREATE
3. For each required interface:
   - If exists in target: SKIP
   - If missing: ADD to wiring
4. Topo sort for generation order
5. Save plan

### `context(feature_path: str, target_project: str, output: str) -> str`

1. Load feature and plan
2. Generate markdown:
   ```markdown
   # Feature: {name}

   ## Source Code (from {source})

   ### {module1}
   ```python
   {code}
   ```

   ## Target Interfaces ({target})

   ### Existing
   {signatures only - not full code}

   ### To Create
   {from plan}

   ## Transplant Plan

   {mappings and wiring}
   ```
3. Save to .eri-rpg/context/{feature}.md
4. Return path

## CLI Commands

```python
@click.group()
def cli():
    """EriRPG - Cross-project feature transplant"""
    pass

# Setup
@cli.command()
@click.argument('name')
@click.argument('path', type=click.Path(exists=True))
@click.option('--lang', default='python', type=click.Choice(['python', 'rust', 'typescript']))
def add(name, path, lang):
    """Register a project"""

@cli.command()
@click.argument('name')
def remove(name):
    """Remove a project"""

@cli.command()
def list():
    """List registered projects"""

@cli.command()
@click.argument('name')
def index(name):
    """Index a project"""

# Exploration
@cli.command()
@click.argument('project')
def show(project):
    """Show project structure"""

@cli.command()
@click.argument('project')
@click.argument('query')
def find(project, query):
    """Find modules matching query"""

@cli.command()
@click.argument('project')
@click.argument('module_path')
def impact(project, module_path):
    """Show impact of changing a module"""

# Transplant
@cli.command()
@click.argument('project')
@click.argument('query')
@click.option('-o', '--output', required=True)
def extract(project, query, output):
    """Extract a feature"""

@cli.command()
@click.argument('feature_file', type=click.Path(exists=True))
@click.argument('target_project')
def plan(feature_file, target_project):
    """Plan transplant to target"""

@cli.command()
@click.argument('feature_file', type=click.Path(exists=True))
@click.argument('target_project')
def context(feature_file, target_project):
    """Generate context for Claude Code"""

# Orchestration
@cli.command()
@click.argument('task')
def do(task):
    """Smart mode - figure out steps"""

@cli.command()
def status():
    """Where am I? What's next?"""

@cli.command()
def validate():
    """Check Claude's work"""

@cli.command()
def diagnose():
    """What went wrong?"""
```

## Orchestration Mode (`do` command)

The `do` command implements intelligent task routing.

### Task Patterns

| Pattern | Actions |
|---------|---------|
| "transplant X from Y to Z" | extract(Y, X) → plan → context |
| "find X in Y" | find(Y, X) |
| "what uses X in Y" | impact(Y, X) |
| "index Y" | index(Y) |
| "implement the plan" | Generate context, output instructions |

### State Machine

```
idle ──[do]──> extracting ──[extract]──> planning ──[plan]──> context_ready
                                                                    │
                                                                    ▼
                                                              implementing
                                                                    │
                                              ┌───────────────[validate]──┐
                                              ▼                           │
                                          validating ──[pass]──> done     │
                                              │                           │
                                              └──[fail]──> diagnosing ────┘
```

### Status Command

```bash
$ eri-rpg status
# Output:
# Current task: Transplant 24GB Klein training from onetrainer to eritrainer
# Phase: context_ready
# Next step: Give Claude Code the context at .eri-rpg/context/24gb_klein.md
#
# Context includes:
# - 3 source modules (1200 lines)
# - 2 target interfaces
# - 5 wiring tasks
#
# After Claude implements, run: eri-rpg validate
```

### Validate Command

```bash
$ eri-rpg validate
# Output:
# Checking transplant...
#
# ✓ eritrainer/utils/offload.py exists
# ✓ eritrainer/utils/offload.py has ModelOffloader class
# ✗ eritrainer/models/flux1.py missing offload import
# ✗ eritrainer/training/base.py missing offloader initialization
#
# 2/4 checks passed
# Run: eri-rpg diagnose
```

### Diagnose Command

```bash
$ eri-rpg diagnose
# Output:
# Diagnosis:
#
# Missing wiring:
# 1. eritrainer/models/flux1.py needs:
#    from eritrainer.utils.offload import ModelOffloader
#
# 2. eritrainer/training/base.py needs in train_step():
#    offloader = ModelOffloader(model, config.offload_layers)
#
# Next: Tell Claude Code to add these imports and calls
```

## Python Parser (`parsers/python.py`)

Uses `ast` module (stdlib, no deps).

```python
import ast
from typing import List, Dict

def parse_python_file(path: str) -> Dict:
    """Parse Python file, extract interfaces and imports."""
    with open(path, 'r') as f:
        source = f.read()

    tree = ast.parse(source)

    result = {
        'imports': [],
        'interfaces': [],
        'docstring': ast.get_docstring(tree),
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result['imports'].append({
                    'type': 'import',
                    'name': alias.name,
                    'asname': alias.asname,
                })
        elif isinstance(node, ast.ImportFrom):
            result['imports'].append({
                'type': 'from',
                'module': node.module,
                'names': [a.name for a in node.names],
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            result['interfaces'].append({
                'name': node.name,
                'type': 'class',
                'methods': methods,
                'docstring': ast.get_docstring(node),
                'line': node.lineno,
            })
        elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
            # Top-level function only
            result['interfaces'].append({
                'name': node.name,
                'type': 'function',
                'signature': get_function_signature(node),
                'docstring': ast.get_docstring(node),
                'line': node.lineno,
            })

    return result

def get_function_signature(node: ast.FunctionDef) -> str:
    """Extract function signature as string."""
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)

    sig = f"def {node.name}({', '.join(args)})"
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig
```

## Build Order

Implementation sequence:

1. **graph.py** — Data structures (no deps)
2. **parsers/python.py** — Python parser (stdlib only)
3. **registry.py** — Project management
4. **indexer.py** — Build graphs
5. **ops.py** — Core operations
6. **state.py** — State tracking
7. **context.py** — Context generation
8. **cli.py + cli_commands/** — Wire everything up

Each file can be tested independently.

## Self-Test

After v1 is built:

```bash
# Register self
eri-rpg add erirpg /home/alex/eri-rpg/erirpg --lang python

# Index self
eri-rpg index erirpg

# Find its own modules
eri-rpg find erirpg "parse python code"
# Should find: parsers/python.py

# Show impact
eri-rpg impact erirpg graph.py
# Should show: indexer.py, ops.py depend on it

# Extract a feature
eri-rpg extract erirpg "python parsing" -o python_parser.json

# The extracted feature should be usable to improve v1.1
```

## Token Budget Analysis

| Context Type | Tokens | Notes |
|--------------|--------|-------|
| Graph structure (100 modules) | ~2K | Summaries + interfaces |
| Feature (3 modules) | ~3K | Full code |
| Target interfaces | ~1K | Signatures only |
| Transplant plan | ~0.5K | Mappings + wiring |
| **Total per transplant** | **~6.5K** | vs 50K+ for full dump |

## Dependencies

```toml
[project]
dependencies = [
    "click>=8.0",  # CLI framework
]

[project.optional-dependencies]
rust = ["tree-sitter>=0.20", "tree-sitter-rust"]
typescript = ["tree-sitter>=0.20", "tree-sitter-typescript"]
```

Python parser uses only stdlib (`ast`).
Rust/TypeScript support is optional (tree-sitter).

## Error Handling

- Missing project → "Project 'X' not found. Run: eri-rpg add X /path"
- Stale index → "Project last indexed 7 days ago. Run: eri-rpg index X"
- No matches → "No modules match 'query'. Try broader terms or: eri-rpg show X"
- Parse error → "Failed to parse X: {error}. Check for syntax errors."
- Missing deps → "Feature requires Y which isn't in target. Add to plan."
