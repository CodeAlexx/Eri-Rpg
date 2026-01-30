# Status: erirpg

_Updated: 2026-01-29 16:38_

## Current Position

- **Phase**: complete
- **Feature**: Auto-update STATUS.md/TASKS.md on ALL state changes

## Commits This Session

1. `424cccd` - feat: auto-update STATUS.md on all state changes
2. `7d77301` - feat: add auto-commit to status_sync
3. `b33df30` - feat: auto-commit when verification passes
4. `d9a40e4` - fix: auto-commit even when no verification configured
5. `589c818` - feat: track STATUS.md and TASKS.md in git for session resume
6. `6d675ed` - chore: update STATUS.md and TASKS.md with current state
7. `1117d9f` - chore: auto-update status files (AUTO-COMMITTED!)
8. `PENDING` - fix: add sync to ALL remaining state-changing functions

## Files Changed

- `erirpg/status_sync.py` - NEW: Central sync + auto-commit
- `erirpg/storage.py` - Added sync to ALL 9 state functions
- `erirpg/agent/run.py` - Added sync calls to 4 methods
- `erirpg/commit.py` - Added sync after commit
- `erirpg/runs.py` - Added sync to create_run, save_run, delete_run
- `erirpg/verification.py` - Added auto-commit on pass/skip
- `.gitignore` - Allow .eri-rpg/*.md files

## Functions With Sync (17 total)

### storage.py (9 functions)
- ✅ create_session
- ✅ update_session
- ✅ add_decision
- ✅ archive_session_decisions
- ✅ add_blocker
- ✅ resolve_blocker
- ✅ add_next_action
- ✅ complete_action
- ✅ add_session_learning

### agent/run.py (4 methods)
- ✅ complete_step
- ✅ fail_step
- ✅ skip_step
- ✅ add_decision

### runs.py (3 functions)
- ✅ create_run
- ✅ save_run
- ✅ delete_run

### Other (1 function)
- ✅ verify_and_commit (commit.py)

## Tests

- ✅ 420 passed

## Resume Commands

```bash
/eri:status --full     # Full context
/eri:recall decisions  # List all decisions
/eri:recall blockers   # List all blockers
```
