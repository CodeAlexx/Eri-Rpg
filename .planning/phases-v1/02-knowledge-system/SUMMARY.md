# Phase 02: Knowledge System

## Status: Complete

## Objective

Store learnings about code modules so we don't re-read the same code repeatedly. Enable staleness detection and versioned rollback.

## What Was Built

1. **Memory Storage** (`memory.py`)
   - StoredLearning dataclass
   - KnowledgeStore for persistence
   - CodeRef for file references
   - Version tracking

2. **Learning Commands**
   - `learn` - Store understanding of a module
   - `recall` - Retrieve stored learning
   - `relearn` - Force re-read
   - `forget` - Remove learning

3. **Staleness Detection**
   - Track file hashes at learn time
   - Detect when file changed since last learn
   - Warn user before using stale knowledge

4. **Rollback System**
   - Snapshot files before edits
   - Restore to previous versions
   - Both code and learning rollback

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| JSON for knowledge | Human-readable, easy to debug |
| Hash-based staleness | Simple, reliable, fast |
| Embedded CodeRefs | Context stays with learning |
| Version array | Full history, not just current |

## Files Created

- `erirpg/memory.py`
- `erirpg/refs.py` (CodeRef)

## CLI Commands

```bash
eri-rpg learn <project> <file>      # Store learning
eri-rpg recall <project> <file>     # Retrieve
eri-rpg knowledge <project>         # List all
eri-rpg relearn <project> <file>    # Force update
eri-rpg forget <project> <file>     # Remove
eri-rpg rollback <project> <file>   # Restore
```

## Data Stored

```yaml
StoredLearning:
  module_path: "src/utils.py"
  learned_at: "2026-01-26T10:00:00"
  summary: "Utility functions for string handling"
  purpose: "Validate and transform user input"
  key_functions:
    validate: "Check input against rules"
    transform: "Convert to standard format"
  gotchas:
    - "Returns None on invalid input, not exception"
  dependencies: ["re", "typing"]
  confidence: 0.95
```
