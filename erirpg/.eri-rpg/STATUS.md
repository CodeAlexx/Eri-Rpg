# Status: erirpg

_Updated: 2026-01-29 16:30_

## Current Position

- **Phase**: complete
- **Feature**: Auto-update STATUS.md/TASKS.md on all state changes

## Commits This Session

1. `424cccd` - feat: auto-update STATUS.md on all state changes
2. `7d77301` - feat: add auto-commit to status_sync
3. `b33df30` - feat: auto-commit when verification passes
4. `d9a40e4` - fix: auto-commit even when no verification configured
5. `589c818` - feat: track STATUS.md and TASKS.md in git for session resume

## Files Changed

- `erirpg/status_sync.py` - NEW: Central sync + auto-commit
- `erirpg/storage.py` - Added sync calls to 5 functions
- `erirpg/agent/run.py` - Added sync calls to 4 methods
- `erirpg/commit.py` - Added sync after commit
- `erirpg/runs.py` - Added sync after save_run
- `erirpg/verification.py` - Added auto-commit on pass/skip
- `.gitignore` - Allow .eri-rpg/*.md files

## Resume Commands

```bash
/eri:status --full     # Full context
/eri:recall decisions  # List all decisions
/eri:recall blockers   # List all blockers
```
