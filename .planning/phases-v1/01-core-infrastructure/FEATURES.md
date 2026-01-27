# Phase 01: Features

## Project Registry

### Add Project
```bash
eri-rpg add myproject /path/to/code
```
- Auto-detects language (Python, Rust, C)
- Validates path exists
- Prevents duplicate names

### Remove Project
```bash
eri-rpg remove myproject
```
- Removes from registry
- Does NOT delete `.eri-rpg/` folder (user choice)

### List Projects
```bash
eri-rpg list
```
- Shows name, path, language, index status
- Indicates if index is stale

## Code Indexing

### Full Index
```bash
eri-rpg index myproject
```
- Scans all source files
- Extracts: functions, classes, imports, docstrings
- Builds dependency graph
- Stores in `.eri-rpg/index.json`

### Module Search
```bash
eri-rpg find myproject "loss calculation"
```
- Fuzzy search on module names and docstrings
- Returns relevance scores
- Shows file path and summary

### Impact Analysis
```bash
eri-rpg impact myproject src/utils.py
```
- Shows what depends on this file
- Helps assess change risk
- Traces transitive dependencies

## Language Support

### Python
- Full AST parsing
- Functions, classes, methods
- Import tracking (from x import y)
- Docstring extraction
- Type hints (partial)

### Rust
- Regex-based parsing
- Functions (fn), structs, impls
- Use statements
- Doc comments (///)

### C
- Regex-based parsing
- Functions, structs, typedefs
- #include tracking
- Comment extraction
