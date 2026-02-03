---
name: coder:complete-milestone
description: Archive milestone, tag release, prepare for next version
argument-hint: "[milestone-name]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Task
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to check milestone state:**
```bash
erirpg coder-complete-milestone [milestone-name]
```

This returns JSON with:
- `milestone`: Current milestone name
- `phases`: Array of all phases
- `total_phases`: Number of phases
- `incomplete_phases`: Phases not yet verified as passed
- `can_complete`: Boolean - true if all phases passed
- `progress`: Progress metrics
- `git`: Git status

Use this data to determine if milestone can be completed.

---

<objective>
Complete a milestone after all phases verified.
Archives milestone, creates git tag, updates state for next version.
</objective>

<context>
Milestone: $ARGUMENTS or current milestone from ROADMAP.md
Check: All phases must be complete and verified
Output: Git tag, archived STATE.md, ready for new milestone
</context>

<process>
## Step 1: Verify All Phases Complete
```bash
# Check ROADMAP.md for phase statuses
cat .planning/ROADMAP.md

# Check all VERIFICATION.md files have status: passed
ls .planning/phases/*/VERIFICATION.md
```

If any phase not complete:
- Show which phases are incomplete
- Suggest completing them first
- Exit

## Step 2: Optional Milestone Audit
Ask user: "Run milestone audit? (checks cross-phase integration)"

If yes, spawn integration checker:
- Verify E2E flows work across phases
- Check for orphaned code
- Identify any gaps between phases
- Report findings

If gaps found:
- Offer to create gap-closing phases
- `/coder:plan-milestone-gaps`

## Step 3: Archive Milestone
Create milestone archive entry:

```bash
# Create archive directory
mkdir -p .planning/archive/{milestone-name}

# Copy relevant artifacts
cp .planning/STATE.md .planning/archive/{milestone-name}/
cp .planning/ROADMAP.md .planning/archive/{milestone-name}/
```

Update STATE.md:
```markdown
## Milestone: {name} - COMPLETED

Completed: {timestamp}
Duration: {start to end}
Phases: {N} completed
Requirements: {M} delivered
```

## Step 4: Git Tag
```bash
# Determine version
# If milestone name looks like version (v1.0, 1.0.0), use it
# Otherwise generate from milestone number

git tag -a {version} -m "Milestone: {milestone-name}

Completed phases:
- Phase 1: {name}
- Phase 2: {name}
...

Requirements delivered:
- REQ-001: {description}
- REQ-002: {description}
..."

# Optionally push tag
# git push origin {version}
```

## Step 5: Update for Next Milestone
Reset STATE.md for next version:
```markdown
# Project State

## Current Position
Milestone: {next-milestone-name}
Phase: 0 of 0 (not yet planned)
Status: Ready for roadmapping

## Previous Milestones
- {completed-milestone}: {version} ({date})

## Last Activity
{timestamp} - Milestone {name} completed
```

## Step 6: Commit
```bash
git add .planning/
git commit -m "milestone({name}): complete and archive"
```
</process>

<completion>
## On Completion

### 1. Update STATE.md

```markdown
## Project
**Milestone:** {version} ✅ COMPLETE

## Current Phase
All phases complete. Milestone archived.

## Last Action
Completed milestone {version}
- Phases: {N} completed
- Tag: {version}
- Archive: .planning/archive/{version}/

## Next Step
Start next milestone with `/coder:new-milestone`
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ MILESTONE COMPLETE: {version}                               ║
╠════════════════════════════════════════════════════════════════╣
║  Phases completed: {N}                                         ║
║  Requirements met: {X}/{Y}                                     ║
║  Git tag: {version}                                            ║
║  Archived to: .planning/archive/{version}/                     ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Start next version (optional)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:new-milestone {next-version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Or run your app - it's ready to ship!
```
</completion>
