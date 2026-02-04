---
name: coder:pause
description: Create handoff state when stopping work mid-session
argument-hint: "[reason]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

## CLI Integration

**First, call the CLI to gather pause context:**
```bash
erirpg coder-pause "stopping for lunch"
```

This returns JSON with:
- `current_phase`: Current phase being worked on
- `current_plan`: Current plan in progress
- `uncommitted_changes`: List of uncommitted files
- `is_dirty`: Whether working directory has changes
- `last_commit`: Most recent commit hash
- `timestamp`: When pause was initiated

Use this data to create the .planning/.continue-here.md file.

---

<objective>
Capture current state for seamless resume later.
Creates handoff file with position, context, and next steps.
</objective>

<context>
Reason: $ARGUMENTS (optional)
Output: .planning/.continue-here.md
</context>

<process>
## Step 1: Capture Current State
```bash
cat .planning/STATE.md
ls .planning/phases/*/
git status
git log -1 --oneline
```

Gather:
- Current phase and plan
- Tasks completed vs remaining
- Uncommitted changes
- Last commit

## Step 2: Write Handoff File
Create .planning/.continue-here.md:

```markdown
---
paused: {timestamp}
reason: {reason or "Session end"}
---

# Continue Here

## Last Position
**Phase:** {N} - {name}
**Plan:** {M} of {total}
**Task:** {current task or "Between tasks"}
**Status:** {in-progress | blocked | ready}

## Uncommitted Changes
{git status summary or "None"}

## What Was Happening
{narrative of current work}

## Next Steps
1. {immediate next action}
2. {following action}
3. {etc}

## Context to Remember
{important decisions or learnings from this session}

## Resume Command
```
/coder:resume
```
```

## Step 3: Update STATE.md
Add session continuity section:
```markdown
## Session Continuity
Last session: {timestamp}
Stopped at: {description}
Resume file: .planning/.continue-here.md
```

## Step 4: Commit (if safe)
If there are staged changes that are complete:
```bash
git add .planning/
git commit -m "wip: pause work - {reason}"
```

If changes are incomplete, don't commit code - only commit handoff.
</process>

<completion>
## On Completion

### 1. Verify Handoff Created

```bash
ls -la .planning/.continue-here.md
```

### 2. Update STATE.md

```markdown
## Session Continuity
Last session: {timestamp}
Stopped at: {current phase/plan}
Reason: {reason}
Resume file: .planning/.continue-here.md

## Next Step
Resume with `/coder:resume`
```

### 3. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 4. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ WORK PAUSED                                                 ║
╠════════════════════════════════════════════════════════════════╣
║  Position: Phase {N}, Plan {M}                                 ║
║  Reason: {reason}                                              ║
║  Handoff: .planning/.continue-here.md                          ║
╚════════════════════════════════════════════════════════════════╝

## ▶ TO RESUME LATER

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:resume
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The resume command will read .continue-here.md and pick up where you left off.
```
</completion>
