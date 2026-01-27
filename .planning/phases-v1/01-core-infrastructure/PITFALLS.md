# Phase 01: Pitfalls & Gotchas

## Registry Issues

### Path Normalization
**Problem**: Paths like `/path/to/project` vs `/path/to/project/` treated differently.

**Solution**: Always normalize with `os.path.normpath()` and `os.path.abspath()`.

### Nested .eri-rpg
**Problem**: If project A contains project B, both have `.eri-rpg/` folders. Confusion about which is active.

**Solution**: Always resolve from the registered project path, not current directory.

## Indexing Issues

### Large Projects
**Problem**: Indexing huge monorepos takes forever.

**Mitigation**: 
- Skip common directories: `node_modules`, `venv`, `.git`, `__pycache__`
- Consider incremental indexing (not yet implemented)

### Symlinks
**Problem**: Symlinks can cause infinite loops or duplicate entries.

**Solution**: Use `os.path.realpath()` and track visited paths.

### Encoding
**Problem**: Non-UTF8 files crash the parser.

**Solution**: Wrap file reads in try/except, skip unreadable files with warning.

## Parser Issues

### Python Dynamic Imports
**Problem**: `importlib.import_module("x")` not detected.

**Status**: Known limitation. Only static imports tracked.

### Rust Macros
**Problem**: Macro-generated code not visible to regex parser.

**Status**: Known limitation. Document when encountered.

### C Preprocessor
**Problem**: `#ifdef` sections create conditional code paths.

**Status**: Parser sees all code, doesn't evaluate conditions. May show false dependencies.

## Performance

### Memory Usage
**Problem**: Loading entire graph into memory for large projects.

**Mitigation**: Lazy loading, only load what's needed for current operation.

### Search Speed
**Problem**: Linear search through all modules is slow.

**Future**: Consider inverted index or SQLite for large projects.
