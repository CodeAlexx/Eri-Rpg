# Phase 04: Features

## Starting a Quick Fix

```bash
eri-rpg quick myproject src/config.py "Update database timeout"
```

What happens:
1. Validates file exists
2. Creates snapshot of current content
3. Stores quick fix state in `.eri-rpg/quick_fix.json`
4. Hook now allows edits to this specific file

## Making Edits

During quick fix, you can:
- Edit the specified file (via Claude Code or directly)
- Read any files
- Run commands

You cannot:
- Edit other files (blocked by hook)
- Start another quick fix (one at a time)

## Completing Quick Fix

```bash
eri-rpg quick-done myproject
```

What happens:
1. Verifies file was actually modified
2. Creates git commit with description
3. Clears quick fix state
4. File edits now blocked again

Commit message format:
```
[quick-fix] Update database timeout

File: src/config.py
```

## Canceling Quick Fix

```bash
eri-rpg quick-cancel myproject
```

What happens:
1. Restores file from snapshot
2. Clears quick fix state
3. No git commit

## Checking Status

```bash
eri-rpg quick-status myproject
```

Output:
```
Quick Fix Active:
  File: src/config.py
  Description: Update database timeout
  Started: 2026-01-26 10:30:00
  Snapshot: .eri-rpg/snapshots/abc123.snap
```

Or if no quick fix:
```
No active quick fix for myproject
```
