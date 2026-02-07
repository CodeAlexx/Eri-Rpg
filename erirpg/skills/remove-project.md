---
name: coder:remove-project
description: Remove a project and optionally clean up all data
argument-hint: "<project-name>"
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, gather project info:**
```bash
python3 -m erirpg.cli remove $ARGUMENTS --info-only --json
```

This returns JSON with:
- `found`: Whether project exists
- `name`, `path`, `lang`, `indexed_at`: Project details
- `is_active`: Whether this is the current active project
- `eri_dir`: `.eri-rpg/` existence and file count
- `planning_dir`: `.planning/` existence and phase count
- `database`: Session count and graph existence

Use this data to show the user what exists and what can be cleaned up.

---

<objective>
Remove a registered project with user-chosen cleanup level.
Shows what data exists, asks what to clean, then executes.
</objective>

<context>
Project name: $ARGUMENTS
</context>

<process>
## Step 1: Gather Info

```bash
python3 -m erirpg.cli remove $ARGUMENTS --info-only --json
```

If `found` is false, report the error and stop.

## Step 2: Present Info

Show the user what exists:

```
Project: {name}
Path: {path}
Language: {lang}
Active: {is_active}
```

Then list data that exists:
- .eri-rpg/ directory ({file_count} files) — if exists
- .planning/ directory ({phase_count} phases) — if exists
- Database graph — if has_graph
- Database sessions ({session_count}) — if any

## Step 3: Ask Cleanup Level

Use AskUserQuestion with these options:

- "Registry only" — just deregister, keep all data
- "Registry + database" — also clear SQLite sessions and graph
- "Registry + local data" — also delete .eri-rpg/ directory
- "Everything" — registry + .eri-rpg/ + .planning/ + database

Only show options relevant to what data exists. If nothing exists beyond
the registry entry, skip the question and just remove.

## Step 4: Execute

Build the CLI command based on chosen level:

- Registry only: `python3 -m erirpg.cli remove $ARGUMENTS --json --force`
- Registry + database: `python3 -m erirpg.cli remove $ARGUMENTS --clean --json --force`
- Registry + local data: `python3 -m erirpg.cli remove $ARGUMENTS --clean --json --force`
- Everything: `python3 -m erirpg.cli remove $ARGUMENTS --clean-all --json --force`

Parse the JSON result to confirm what was cleaned.

## Step 5: Report

Show what was removed.
</process>

<completion>
## On Completion

### 1. Update STATE.md

If the project had a `.planning/` directory and it was removed:
```markdown
## Last Action
Completed remove-project
- Removed: {name} from registry
- Cleaned: {list of what was cleaned}
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Results

```
====================================================================
  PROJECT REMOVED: {name}
====================================================================
  Cleaned: {comma-separated list}
  Was active: {yes/no — if yes, active project is now cleared}
====================================================================

If active project was cleared:
  Run /coder:switch-project to set a new active project.
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</completion>
