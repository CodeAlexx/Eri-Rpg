---
name: coder:execute-phase
description: Execute all plans for a phase with wave-based parallelization. Use when ready to build code after planning.
argument-hint: "<phase-number> [--gaps-only]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
---

# Execute Phase

Execute all plans in a phase using wave-based parallel execution.

## Dynamic Context

**Phase info from CLI:**
!`python3 -m erirpg.cli coder-execute-phase $ARGUMENTS 2>/dev/null || echo '{"error": "CLI failed"}'`

**Current state:**
!`cat .planning/STATE.md 2>/dev/null | head -30`

**Plans in phase:**
!`ls -1 .planning/phases/$0-*/*-PLAN.md 2>/dev/null | head -20`

---

## Execution Flow

### 1. Validate CLI Response

If CLI returned error, stop and report. Otherwise parse:
- `phase_dir`, `phase_number`, `phase_name`, `goal`
- `plans` list with paths, waves, completion status
- `waves` grouped structure

**CLI creates EXECUTION_STATE.json** — hooks now allow file edits.

### 2. Build Wave Inventory

| Plan | Wave | Status | Autonomous |
|------|------|--------|------------|
| {from CLI response} |

**Filter:**
- Skip plans with SUMMARY.md (already complete)
- If `--gaps-only`: only execute `gap_closure: true` plans

**If all complete:** Skip to verification.

### 3. Execute Each Wave

For each wave in sequence, plans within wave run in parallel:

**3a. Spawn eri-executor for each plan:**

```
Task(
  subagent_type="eri-executor",
  prompt="Execute plan {plan_number} of phase {phase_number}-{phase_name}.

<plan>
{Read plan file content here}
</plan>

<project_state>
{Read STATE.md here}
</project_state>

Execute all tasks, commit atomically, create SUMMARY.md.
Report: plan ID, tasks completed, SUMMARY path, commit hashes."
)
```

**3b. Wait for all executors in wave**

**3c. Verify each SUMMARY.md exists**

**3d. Update STATE.md:**

```markdown
## Current Phase
**Phase {N}: {name}** - executing (wave {X}/{Y} complete)

## Last Action
Completed wave {X}
- Plans executed: {list}
- Progress: {completed}/{total}
```

**3e. If executor fails:** See [failure handling](reference.md#agent-failure-handling)

### 4. Verification (MANDATORY)

After all waves, spawn **eri-verifier**:

```
Task(
  subagent_type="eri-verifier",
  prompt="Verify phase {phase_number} goal achievement.

Phase directory: {phase_dir}
Phase goal: {goal from ROADMAP}

Check must_haves against actual codebase.
Create VERIFICATION.md with status: passed/gaps_found/human_needed."
)
```

**Route by status:**

| Status | Action |
|--------|--------|
| `passed` | → Step 5 (completion) |
| `human_needed` | Present checklist, wait for "approved" |
| `gaps_found` | **BLOCK** — show [gaps template](templates/gaps-found.md) |

### 5. Completion (only if passed)

```bash
python3 -m erirpg.cli coder-end-plan
git add .planning/phases/*/
git commit -m "chore(phase-{N}): complete execution and verification"
python3 -m erirpg.cli switch "$(pwd)"
```

Update STATE.md and show [completion box](templates/completion-box.md).

---

## Critical Rules

1. **Never skip verification** — Step 4 MUST run
2. **Never proceed on gaps_found** — Must fix gaps first
3. **Update STATE.md after each wave** — Not just at completion
4. **Wait for user on failures** — Don't auto-proceed
5. **Show completion box** — Never say "ready when you are"

For detailed step documentation, see [reference.md](reference.md).
