# Architecture

## Overview

EriRPG is organized into several layers:

```
┌─────────────────────────────────────────────────────┐
│                   CLI (cli.py)                       │
│  Commands: add, index, learn, quick, cleanup, etc.  │
├─────────────────────────────────────────────────────┤
│                Agent API (agent/)                    │
│  Agent, Run, Plan, Step - orchestrates workflows    │
├─────────────────────────────────────────────────────┤
│              Core Services                           │
│  registry, memory, preflight, verification          │
├─────────────────────────────────────────────────────┤
│              Indexing & Parsing                      │
│  indexer, graph, parsers (python, rust, c)          │
├─────────────────────────────────────────────────────┤
│              Hooks (Claude Code)                     │
│  pretooluse, precompact, sessionstart               │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
erirpg/
├── __init__.py        # Package init, installs write hooks
├── cli.py             # All CLI commands (~3000 lines)
├── registry.py        # Project registry (name → path mapping)
├── indexer.py         # Builds dependency graphs
├── graph.py           # Graph data structure
├── memory.py          # Knowledge storage (learnings, versions)
├── preflight.py       # Preflight checks before edits
├── verification.py    # Test running, result tracking
├── quick.py           # Quick fix mode
├── hooks.py           # Python write interception (NOT the hooks dir)
├── spec.py            # Spec parsing and generation
├── agent/
│   ├── __init__.py    # Agent class - main workflow orchestrator
│   ├── run.py         # RunState - tracks run progress
│   ├── plan.py        # Plan, Step - execution plan
│   ├── learner.py     # Auto-learning after edits
│   └── spec.py        # Re-exports (backward compat)
├── hooks/
│   ├── pretooluse.py  # Claude Code PreToolUse hook
│   ├── precompact.py  # Claude Code PreCompact hook
│   ├── sessionstart.py # Claude Code SessionStart hook
│   └── hooks.json     # Hook configuration template
├── parsers/
│   ├── python.py      # Python AST parsing
│   ├── rust.py        # Rust parsing (regex-based)
│   └── c.py           # C parsing (regex-based)
└── modes/
    ├── take.py        # Transplant workflow
    ├── work.py        # Modify workflow
    └── new.py         # New project workflow
```

## Key Components

### Registry (`registry.py`)

Stores project registrations in `~/.erirpg/registry.json`:

```json
{
  "myproject": {
    "path": "/path/to/project",
    "lang": "python",
    "indexed_at": "2024-01-26T10:00:00"
  }
}
```

### Graph (`graph.py`, `indexer.py`)

Builds a dependency graph from source code:

```python
# graph.json structure
{
  "modules": {
    "src/utils.py": {
      "path": "src/utils.py",
      "interfaces": ["validate_email", "slugify"],
      "imports": ["re", "typing"],
      "lines": 150,
      "docstring": "Utility functions"
    }
  },
  "edges": [
    {"from": "src/forms.py", "to": "src/utils.py", "type": "import"}
  ]
}
```

### Memory (`memory.py`)

Stores learnings with versioning:

```python
# StoredLearning structure
{
  "module_path": "src/utils.py",
  "summary": "Utility functions",
  "purpose": "String manipulation helpers",
  "key_functions": {"validate_email": "Checks email format"},
  "gotchas": ["slugify doesn't handle unicode"],
  "versions": [
    {
      "version": 1,
      "timestamp": "2024-01-26T10:00:00",
      "commit_before": "abc123",
      "files_content": {"src/utils.py": "...original content..."}
    }
  ]
}
```

### Agent (`agent/__init__.py`)

Orchestrates multi-step workflows:

```python
class Agent:
    spec: Spec        # Goal and constraints
    plan: Plan        # Execution steps
    _run: RunState    # Progress tracking

    def preflight(files, operation) -> PreflightReport
    def edit_file(path, old, new, desc) -> bool
    def complete_step(files_touched, notes) -> bool
    def is_complete() -> bool
    def get_report() -> dict
```

### Preflight (`preflight.py`)

Checks before edits:

1. File exists (for modify operations)
2. Learning exists (for refactor operations with strict=True)
3. Learning is not stale (file hasn't changed since last learn)
4. Impact zone is understood

Returns `PreflightReport` with `ready` flag and blockers.

### Verification (`verification.py`)

Runs tests after edits:

1. Loads `.eri-rpg/verification.json` if present
2. Falls back to pytest (Python) or npm test (Node)
3. Captures stdout/stderr
4. Returns pass/fail with details

### Quick Fix (`quick.py`)

Lightweight mode bypassing full workflow:

1. Creates `quick_fix_state.json` with target file
2. Snapshots original content
3. Allows single file edit via hook
4. Commits on `quick-done`, restores on `quick-cancel`

### Hooks

**`hooks.py`** (Python file):
- Intercepts `builtins.open()`
- Blocks writes without active run/preflight
- Only active when erirpg is imported

**`hooks/pretooluse.py`** (Claude Code hook):
- Reads stdin JSON from Claude Code
- Checks quick fix state or preflight state
- Returns `{"decision": "allow"}` or `{"decision": "block", "reason": "..."}`

## Data Storage

Per-project data stored in `.eri-rpg/`:

```
.eri-rpg/
├── graph.json           # Dependency graph (from indexing)
├── knowledge.json       # Learnings (from learn command)
├── preflight_state.json # Active preflight (temporary)
├── quick_fix_state.json # Active quick fix (temporary)
├── verification.json    # Test configuration (optional)
├── runs/                # Run state files
│   └── abc123.json
├── snapshots/           # File snapshots for rollback
│   └── hash123.snapshot
└── resume.md            # Resume instructions (from precompact)
```

Global data in `~/.erirpg/`:

```
~/.erirpg/
└── registry.json        # Project registry
```

## Known Technical Issues

1. **Module naming conflict**: `hooks.py` shadows `hooks/` directory.
   Python resolves `erirpg.hooks` to the file, not the directory.
   Workaround: hooks must be called as scripts, not imported.

2. **Nested .eri-rpg directories**: If a subdirectory has its own `.eri-rpg`,
   hooks may find the wrong one. The search goes up from file path.

3. **Stale state**: `preflight_state.json` persists across sessions.
   If session crashes, state may be stale. Manual cleanup needed.

4. **Large files**: Snapshots store full file content. Large files
   can bloat `.eri-rpg/snapshots/`.
