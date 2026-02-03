---
name: coder:execute-phase
description: Execute all plans for a phase with wave-based parallelization
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Bash
  - Task
---

# Execute Phase

**Run the CLI command. Follow its output exactly.**

```bash
python3 -m erirpg.cli coder-execute-phase $ARGUMENTS
```

The CLI returns everything you need:
- Plans to execute (with paths and wave assignments)
- Wave groupings for parallel execution
- Current completion state
- Settings (parallelization, verifier enabled, etc.)

**It also creates EXECUTION_STATE.json automatically** - hooks will allow file edits.

## After CLI Returns

Follow the `instructions` field in the JSON output exactly:

1. For each wave in order, spawn **eri-executor** for each plan in that wave
2. Pass the full plan content to each executor (read the plan file first)
3. Wait for wave completion (all executors done, SUMMARY.md files exist)
4. After all waves: spawn **eri-verifier** if enabled in settings

## On Completion

Run: `python3 -m erirpg.cli coder-end-plan`

This removes EXECUTION_STATE.json and re-enables hook enforcement.
