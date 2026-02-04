---
name: coder:remove-phase
description: Remove a future phase from the roadmap
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to validate removal:**
```bash
erirpg coder-remove-phase 4
```

This returns JSON with:
- `valid`: Whether phase can be removed
- `error`: Error message if not valid
- `phase`: Phase number
- `name`: Phase name
- `requirements`: Requirements assigned to this phase

Use this data to check if removal is allowed and handle requirements.

---

<objective>
Remove a phase that hasn't been started yet.
Cannot remove completed or in-progress phases.
Optionally moves requirements to another phase or defers them.
</objective>

<context>
Phase number: $ARGUMENTS
Check: Phase must be in future (not started)
</context>

<process>
## Step 1: Validate
```bash
cat .planning/ROADMAP.md
cat .planning/STATE.md
```

Check:
- Phase exists
- Phase not yet started (no PLAN.md files, no in-progress status)
- Not the current phase

If validation fails:
- "Cannot remove phase {N}: {reason}"
- Exit

## Step 2: Handle Requirements
Get requirements assigned to this phase.

Use AskUserQuestion:
"Phase {N} has these requirements: {REQ-IDs}. What to do with them?"
Options:
- "Move to phase X" (specify which)
- "Defer to v2"
- "Remove entirely"

Update REQUIREMENTS.md accordingly.

## Step 3: Remove Phase
Remove phase section from ROADMAP.md.
Renumber subsequent phases (-1).

## Step 4: Update References
Update STATE.md if needed (phase count changed).

## Step 5: Commit
```bash
git add .planning/
git commit -m "plan: remove phase {N} - {name}

Requirements: {disposition}"
```
</process>

<completion>
## On Completion

### 1. Verify Committed

```bash
git status --short .planning/
```

### 2. Update STATE.md

```markdown
## Current Position
Phase count: {new_total} phases

## Last Action
Completed remove-phase {N}
- Removed: Phase {N} - {phase-name}
- Requirements: {disposition}
- Renumbered: {count} subsequent phases

## Next Step
Continue with current phase or plan next
```

### 3. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 4. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE REMOVED: {N} - {phase-name}                           ║
╠════════════════════════════════════════════════════════════════╣
║  Requirements: {disposition}                                   ║
║  Updated count: {new_total} phases                             ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Continue workflow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase {current}  (continue current work)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
</completion>
