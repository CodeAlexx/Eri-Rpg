# Status: erirpg

_Updated: 2026-01-29 16:45_

## Current Position

- **Phase**: complete
- **Feature**: Auto-commit on EVERY file edit after verification passes

## Commits This Session

1. `424cccd` - feat: auto-update STATUS.md on all state changes
2. `7d77301` - feat: add auto-commit to status_sync
3. `b33df30` - feat: auto-commit when verification passes
4. `d9a40e4` - fix: auto-commit even when no verification configured
5. `589c818` - feat: track STATUS.md and TASKS.md in git for session resume
6. `6d675ed` - chore: update STATUS.md and TASKS.md with current state
7. `1117d9f` - chore: auto-update status files (AUTO-COMMITTED!)
8. `9383855` - fix: add sync to ALL remaining state-changing functions
9. `PENDING` - feat: posttooluse hook runs verification + auto-commit

## Key Change

**posttooluse.py now runs verification after EVERY Edit/Write and auto-commits if tests pass**

## Files Changed

- `erirpg/hooks/posttooluse.py` - NOW runs verification + auto-commit after edits
- `erirpg/status_sync.py` - Central sync + auto-commit
- `erirpg/storage.py` - Sync on ALL 9 state functions
- `erirpg/agent/run.py` - Sync on 4 methods
- `erirpg/runs.py` - Sync on create_run, save_run, delete_run
- `erirpg/verification.py` - Auto-commit on pass/skip
- `erirpg/commit.py` - Sync after commit
- `.gitignore` - Allow .eri-rpg/*.md files

## Resume Commands

```bash
/eri:status --full     # Full context
/eri:recall decisions  # List all decisions
/eri:recall blockers   # List all blockers
```
