# Execute Phase Reference

Detailed documentation for each step of phase execution.

## Step Details

### Step 1: CLI Initialization

The CLI command `python3 -m erirpg.cli coder-execute-phase N` returns JSON:

```json
{
  "phase_dir": ".planning/phases/01-setup",
  "phase_number": 1,
  "phase_name": "setup",
  "goal": "Set up project infrastructure",
  "plans": [
    {"path": "01-PLAN.md", "wave": 1, "complete": false},
    {"path": "02-PLAN.md", "wave": 1, "complete": false},
    {"path": "03-PLAN.md", "wave": 2, "complete": false}
  ],
  "waves": {
    "1": ["01-PLAN.md", "02-PLAN.md"],
    "2": ["03-PLAN.md"]
  },
  "settings": {...},
  "instructions": "Execute waves in order..."
}
```

**Side effect:** Creates `.planning/EXECUTION_STATE.json` which signals hooks to allow file edits.

### Step 2: Plan Discovery

For each plan, read frontmatter:

```yaml
---
wave: 1
autonomous: true
gap_closure: false
---
```

Build inventory table showing execution order.

**Filtering rules:**
- Plan has SUMMARY.md → skip (already executed)
- `--gaps-only` flag AND `gap_closure: false` → skip

### Step 3: Wave Execution

Waves execute sequentially. Plans within a wave execute in parallel.

**Before spawning executors:**
1. Read the plan file content (@ syntax doesn't cross Task boundaries)
2. Read STATE.md for project context
3. Prepare the prompt with both embedded

**Executor prompt template:**

```
Execute plan {plan_number} of phase {phase_number}-{phase_name}.

<plan>
{full plan content}
</plan>

<project_state>
{STATE.md content}
</project_state>

Execute all tasks, commit each atomically, create SUMMARY.md, update STATE.md.
Report completion with: plan ID, tasks completed, SUMMARY path, commit hashes.
```

**After each wave:**
1. Verify SUMMARY.md exists for each plan
2. Read SUMMARY.md to extract deliverables
3. Update STATE.md with progress
4. Report wave completion

### Step 4: Verification

**Why mandatory:** Without verification, phases get marked complete despite missing functionality. This was the root cause of Phase 5 failures.

**Verifier checks:**
- Each `must_have` from plan frontmatter
- Against actual codebase (not SUMMARY claims)
- Creates VERIFICATION.md with evidence

**Status meanings:**

| Status | Meaning | Action |
|--------|---------|--------|
| `passed` | All must_haves verified in codebase | Proceed to completion |
| `gaps_found` | Some must_haves missing or broken | Block, offer gap closure |
| `human_needed` | Automated checks pass, needs manual testing | Wait for user approval |

### Step 5: Completion

Only reached if verification status is `passed`.

**Actions:**
1. `coder-end-plan` removes EXECUTION_STATE.json
2. Commit any uncommitted planning artifacts
3. Update STATE.md with completion status
4. Update global state for session recovery
5. Show completion box with next steps

---

## Agent Failure Handling

If Task tool returns error (API 500, timeout, rejection):

1. **Retry once** — transient errors are common

2. **If still fails, STOP and report:**
   ```
   Executor failed for plan {ID}: {error}

   Options:
   1. Retry - Spawn executor again
   2. Skip - Mark as failed, continue to next wave
   3. Abort - Stop execution, preserve state
   ```

3. **DO NOT execute the work yourself** — defeats isolated context purpose

4. **Wait for user decision** — don't proceed automatically

---

## Mid-Execution Recovery

If execution is interrupted:

1. EXECUTION_STATE.json persists (hooks still allow edits)
2. STATE.md shows last completed wave
3. SUMMARY.md files show which plans completed
4. Re-run `/coder:execute-phase N` to continue

The CLI detects completed plans and skips them.

---

## Wave Report Format

After each wave completes, report:

```markdown
---

## Wave {N} Complete

**Plan {ID}: {Name}**
{What was built — from SUMMARY.md deliverables}
{Notable deviations, if any}

{If more waves: "Enables Wave {N+1}: {brief}"}

---
```

---

## Troubleshooting

### "No plans found"
Phase hasn't been planned. Run `/coder:plan-phase N` first.

### "All plans already complete"
All plans have SUMMARY.md. Proceeds directly to verification.

### "Executor failed"
See agent failure handling above. Don't improvise.

### "gaps_found but I know it works"
Verification checks codebase, not your belief. Either:
- The code truly has gaps → fix them
- The must_haves are wrong → re-plan with `--gaps`

### "EXECUTION_STATE.json stale"
From crashed execution. Run `python3 -m erirpg.cli coder-end-plan --force`.
