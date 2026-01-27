# Phase 01: Core Infrastructure

## Status: Complete

## Objective

Build the foundation for project management, code indexing, and dependency tracking.

## What Was Built

1. **Project Registry** (`registry.py`)
   - Add/remove/list projects
   - Store project metadata (path, language, indexed status)
   - Persist to `~/.eri-rpg/registry.json`

2. **Code Indexer** (`indexer.py`)
   - Scan project files
   - Extract module information
   - Build searchable index

3. **Dependency Graph** (`graph.py`)
   - Track imports and dependencies
   - Enable impact analysis
   - Support module search

4. **Language Parsers** (`parsers/`)
   - Python parser (AST-based)
   - Rust parser (regex-based)
   - C parser (regex-based)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| JSON for registry | Simple, human-readable, no dependencies |
| Per-project `.eri-rpg/` | Isolate project data, git-friendly |
| AST for Python | Accurate parsing, handles edge cases |
| Regex for Rust/C | Good enough, avoid complex dependencies |

## Files Created

- `erirpg/registry.py`
- `erirpg/indexer.py`
- `erirpg/graph.py`
- `erirpg/parsers/__init__.py`
- `erirpg/parsers/python.py`
- `erirpg/parsers/rust.py`
- `erirpg/parsers/c.py`

## CLI Commands

```bash
eri-rpg add <name> <path>    # Register project
eri-rpg remove <name>        # Unregister
eri-rpg list                 # List all
eri-rpg index <name>         # Build graph
eri-rpg show <name>          # Show structure
eri-rpg find <name> <query>  # Search modules
eri-rpg impact <name> <file> # Impact analysis
```

## Lessons Learned

- AST parsing is worth the complexity for Python
- Regex parsers need careful escaping
- Indexing should be incremental (not implemented yet)
