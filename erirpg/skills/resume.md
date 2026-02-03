# /coder:resume - Restore from Last Session

Resume work from where you left off. Counterpart to `/coder:pause`.

## CLI Integration

**First, call the CLI to get resume state:**
```bash
erirpg coder-resume [--phase N] [--plan N-M]
```

This returns JSON with:
- `source`: Where resume state was found (RESUME.md, STATE.md, CHECKPOINT.md)
- `exists`: Whether resume state exists
- `phase`, `plan`, `task`: Position info
- `content`: Full content of resume file
- `git_status`: Current git state

Use this data to drive the workflow below.

---

## Usage

```
/coder:resume
/coder:resume --phase N      # Resume specific phase
/coder:resume --plan N-M     # Resume specific plan
```

## Execution Steps

### Step 1: Locate Resume State

Check for resume files in order:

```
1. .planning/RESUME.md (from /coder:pause)
2. .planning/STATE.md (session continuity section)
3. .planning/phases/*/CHECKPOINT.md (in-progress checkpoints)
```

**If no resume state found:**
```
No pending work to resume.

Current project status:
- Phase: [X] of [Y]
- Last completed: [phase name]
- Next action: /coder:plan-phase [N] or /coder:execute-phase [N]
```

### Step 2: Load Resume Context

Read all context files:
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/RESUME.md` (if exists)

Extract:
- **stopped_at**: Where work paused
- **pending_checkpoint**: Any awaiting user response
- **next_action**: Recommended next step
- **blockers**: Any issues preventing continuation

### Step 3: Present Resume Options

**If RESUME.md exists (clean pause):**
```markdown
## Resume Point

**Stopped:** [timestamp]
**Location:** Phase [X], Plan [Y], Task [Z]
**Reason:** [reason from pause]

### Context Preserved
- [Key decisions made]
- [Files modified]
- [Pending work]

### Resume Options

1. **Continue from pause point** (recommended)
   → `/coder:execute-phase [N]` will resume at task [Z]

2. **Re-plan current phase**
   → `/coder:plan-phase [N] --force` to regenerate plans

3. **Skip to next phase**
   → `/coder:execute-phase [N+1]` if current phase is optional

Select option (1/2/3):
```

**If checkpoint pending:**
```markdown
## Checkpoint Awaiting Response

**Type:** [human-verify | decision | human-action]
**Phase:** [N] - [name]
**Plan:** [M]

### What Was Built
[Description from checkpoint]

### Awaiting Your Input
[What the checkpoint needs]

### To Continue
Respond with your input, then run:
`/coder:execute-phase [N]`
```

### Step 4: Execute Resume

Based on user selection:

**Option 1 - Continue:**
1. Delete RESUME.md
2. Update STATE.md with resume timestamp
3. Execute: `/coder:execute-phase [N]`

**Option 2 - Re-plan:**
1. Archive current plans to `.planning/phases/[phase]/archived/`
2. Delete RESUME.md
3. Execute: `/coder:plan-phase [N]`

**Option 3 - Skip:**
1. Mark current phase as skipped in ROADMAP.md
2. Delete RESUME.md
3. Execute: `/coder:execute-phase [N+1]`

### Step 5: Validate State

After resume action completes:

```bash
# Verify git state is clean
git status

# Verify STATE.md is current
cat .planning/STATE.md | head -20
```

Report:
```markdown
## Resumed Successfully

**Now at:** Phase [X], Plan [Y]
**Status:** [executing | planning | ready]
**Next step:** [automatic or user action needed]
```

## Resume File Format

`.planning/RESUME.md` structure:
```markdown
---
paused_at: YYYY-MM-DDTHH:MM:SSZ
phase: N
plan: M
task: T
reason: "user provided reason"
---

# Resume Point

## Stopped At
Phase [N]: [name]
Plan [M]: [plan name]
Task [T]: [task name]

## Completed This Session
| Phase | Plan | Task | Status |
|-------|------|------|--------|
| ... | ... | ... | ... |

## Pending Work
- [Remaining tasks in current plan]
- [Remaining plans in current phase]

## Key Context
- [Important decisions made]
- [Files modified but not committed]
- [Blockers or concerns]

## Resume Command
```
/coder:resume
```
```

## Integration with STATE.md

STATE.md Session Continuity section:
```markdown
## Session Continuity
Last session: YYYY-MM-DD HH:MM
Stopped at: Phase N, Plan M, Task T
Resume file: .planning/RESUME.md
Pending checkpoint: [checkpoint-id or "None"]
```

## Error Handling

**Dirty git state:**
```
Warning: Uncommitted changes detected.

Files with changes:
- [list of files]

Options:
1. Commit changes: `git add . && git commit -m "WIP: resume point"`
2. Stash changes: `git stash`
3. Discard changes: `git checkout .` (destructive)

After resolving, run `/coder:resume` again.
```

**Conflicting resume states:**
```
Multiple resume points found:
1. RESUME.md (paused at Phase 2, Plan 1)
2. Checkpoint pending (Phase 2, Plan 2)

These may conflict. Options:
1. Use RESUME.md state
2. Use checkpoint state
3. Reset to last completed phase

Select option:
```
