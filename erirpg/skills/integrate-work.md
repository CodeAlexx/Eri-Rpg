---
name: coder:integrate-work
description: Retroactively document ad-hoc work from git history into planning artifacts
argument-hint: "<phase-number> [--since YYYY-MM-DD]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to find untracked commits:**
```bash
python3 -m erirpg.cli coder-integrate-work $ARGUMENTS
```

This returns JSON with:
- `phase`: Phase number
- `phase_name`: Directory name (e.g., "03-auth")
- `phase_dir`: Path to phase directory
- `phase_goal`: Goal from ROADMAP.md
- `untracked_commits`: Array of commits not made by workflow
  - Each: {hash, full_hash, message, date, files}
- `untracked_count`: Number of untracked commits
- `next_plan_number`: Next available plan number for this phase
- `requirements`: Available REQ-IDs from REQUIREMENTS.md

Use this data to present commits and generate retroactive artifacts.

---

<objective>
Retroactively document ad-hoc git commits (manual fixes, creative sessions,
experiments) as proper planning artifacts so .planning/ state stays accurate.
Generates PLAN.md + SUMMARY.md pair for progress counting.
No agent spawn needed — skill reads git log and generates markdown.
</objective>

<context>
Phase number: $ARGUMENTS (first arg)
--since: Optional date filter (e.g., 2026-01-15)
Read: CLI output (untracked commits, phase info)
Output: {phase_dir}/{NN-PP}-PLAN.md + {NN-PP}-SUMMARY.md
</context>

<process>
## Step 1: Show Untracked Commits

If untracked_count == 0:
```
No untracked commits found. All recent work is already documented.
```
Stop here.

Otherwise, display a table:
```
Untracked commits for Phase {N}: {phase_goal}

| # | Hash    | Date       | Message              | Files |
|---|---------|------------|----------------------|-------|
| 1 | abc1234 | 2026-01-15 | fix: login redirect  | 3     |
| 2 | def5678 | 2026-01-16 | feat: add reset form | 5     |
| ...                                                       |
```

## Step 2: User Selects Commits

Use AskUserQuestion:
Ask: "Which commits belong to this phase?"
- Options: "All of them", "Let me pick specific ones", "None — wrong phase"

If "Let me pick specific ones":
Ask: "Enter commit numbers (e.g., 1,2,5)"
- Parse selection, validate against available commits

If "None — wrong phase":
Stop — suggest trying a different phase number.

## Step 3: Ask About Requirements

If requirements list is non-empty:
Use AskUserQuestion:
Ask: "Does this work close any requirements?"
- Options: Show available REQ-IDs as options, plus "None"
- multiSelect: true

Collect selected REQ-IDs (may be empty).

## Step 4: Generate PLAN.md

Create `{phase_dir}/{NN-PP}-PLAN.md` where NN = phase number, PP = next_plan_number:

```markdown
---
phase: {phase_name}
plan: {next_plan_number}
wave: 1
external_work: true
objective: "Retroactive documentation of ad-hoc work"
files_modified:
  - {all unique files from selected commits}
must_haves:
  truths:
    - "Changes from {count} commits integrated into phase tracking"
  artifacts: []
  key_links: []
---

# Plan {NN-PP}: External Work Integration

**Objective:** Document {count} ad-hoc commits retroactively.

**Note:** This plan was generated after the fact by `/coder:integrate-work`.
The work was already completed outside the normal workflow.

## Commits Included

| Hash | Date | Message |
|------|------|---------|
{for each selected commit: | {hash} | {date} | {message} |}

## Files Changed

{deduplicated list of all files from selected commits}

## Tasks

{For each selected commit:}
### Task {N}: {commit.message}
- **Commit:** {commit.hash}
- **Date:** {commit.date}
- **Files:** {commit.files joined}
```

## Step 5: Generate SUMMARY.md

Create `{phase_dir}/{NN-PP}-SUMMARY.md`:

```markdown
---
phase: {phase_name}
plan: {next_plan_number}
external_work: true
completed: {current timestamp}
verification:
  all_tasks_verified: true
  method: "retroactive — commits already landed"
---

# Summary: Plan {NN-PP} (External Work)

## Execution
- **Method:** Retroactive integration via `/coder:integrate-work`
- **Commits:** {count}
- **Status:** Complete (work was pre-existing)

## Changes

{For each selected commit:}
### {commit.message} ({commit.hash})
Files: {commit.files joined}
```

## Step 6: Mark Requirements (if any)

If user selected REQ-IDs in Step 3:

1. Read REQUIREMENTS.md
2. For each selected REQ-ID:
   - Change `- [ ] **{REQ-ID}**` to `- [x] **{REQ-ID}**`
3. Read ROADMAP.md Coverage Matrix
4. For each selected REQ-ID:
   - Change `| {REQ-ID} | ... | Pending |` to `| {REQ-ID} | ... | Complete |`

Skip if REQUIREMENTS.md doesn't exist or no REQ-IDs selected.

## Step 7: Update STATE.md

Read STATE.md, update:
```markdown
## Last Action
Integrated {count} external commits into phase {N}
Plan {NN-PP} created retroactively
```

## Step 8: Commit Planning Artifacts

```bash
git add {phase_dir}/{NN-PP}-PLAN.md {phase_dir}/{NN-PP}-SUMMARY.md
git add .planning/STATE.md
# Only if requirements were updated:
git add .planning/REQUIREMENTS.md .planning/ROADMAP.md
git commit -m "plan: integrate {count} external commits into phase {N} ({NN-PP})"
```
</process>

<completion>
## On Completion

### 1. Update STATE.md

Already done in Step 7.

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ EXTERNAL WORK INTEGRATED                                    ║
╠════════════════════════════════════════════════════════════════╣
║  Commits documented: {count}                                   ║
║  Plan created: {NN-PP}-PLAN.md                                 ║
║  Summary created: {NN-PP}-SUMMARY.md                           ║
║  Requirements closed: {REQ-IDs or "none"}                      ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Continue workflow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:progress  OR  /coder:plan-phase {N+1}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Progress tracking now reflects the integrated work.
```
</completion>
