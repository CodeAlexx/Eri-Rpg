# Tasks: erirpg

_Updated: 2026-01-29 16:45_

## Completed

- [x] Create status_sync.py module
- [x] Add sync to storage.py: ALL 9 state functions
- [x] Add sync to agent/run.py: complete_step, fail_step, skip_step, add_decision
- [x] Add sync to commit.py: verify_and_commit
- [x] Add sync to runs.py: save_run, create_run, delete_run
- [x] Add auto-commit when verification passes
- [x] Add auto-commit when no verification configured
- [x] Update .gitignore to track STATUS.md, TASKS.md, ROADMAP.md
- [x] VERIFIED: Auto-commit fires (commit 1117d9f proves it)
- [x] VERIFIED: /eri:verify found 6 gaps - ALL FIXED
- [x] VERIFIED: 420 tests pass
- [x] **posttooluse.py: Run verification + auto-commit after EVERY Edit/Write**

## Pending

_No pending tasks_

## Bugs/Issues

- [x] **BUG: Status line issues** - project not updating, model missing, token meter missing, persona wrong
  - Reported: 2026-01-29 16:48
  - Phase: implementing
  - Status: Fixed
  - **Fixes applied**:
    1. `statusline.py`: Now reads `model.display_name` from Claude Code input
    2. `statusline.py`: Prioritizes cwd-based project detection over stale state
    3. `statusline.py`: Calculates tokens from `total_input_tokens + total_output_tokens`
    4. `persona_detect.py`: Smarter detection based on file type being read (not always "analyzer")
