# Phase 04: Quick Fix Mode

## Status: Complete

## Objective

Enable lightweight single-file edits without full spec/run ceremony. For typos, config changes, small bug fixes.

## What Was Built

1. **Quick Fix API** (`quick.py`)
   - Start quick fix session
   - Track allowed file
   - Auto-snapshot
   - Complete with commit
   - Cancel with restore

2. **Hook Integration**
   - PreToolUse recognizes quick fix state
   - Allows edits to the specific file
   - Blocks edits to other files

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Single file only | Keep it simple, avoid scope creep |
| Auto-snapshot | Always have rollback |
| Auto-commit on done | Clean git history |
| Description required | Know why change was made |

## Files Created/Modified

- `erirpg/quick.py`
- `erirpg/hooks/pretooluse.py` (modified)

## CLI Commands

```bash
eri-rpg quick <project> <file> "<description>"  # Start
eri-rpg quick-done <project>                     # Complete
eri-rpg quick-cancel <project>                   # Abort
eri-rpg quick-status <project>                   # Check
```

## Use Cases

1. **Typo fix**: `eri-rpg quick myproject README.md "Fix typo"`
2. **Config change**: `eri-rpg quick myproject config.yaml "Update API URL"`
3. **Small bug**: `eri-rpg quick myproject src/utils.py "Fix off-by-one error"`
