---
name: coder:execute-phase
description: Execute all plans for a phase with wave-based parallelization
argument-hint: "<phase-number> [--gaps-only]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
---

# Execute Phase

Execute all plans in a phase using wave-based parallel execution. This skill orchestrates the full execution flow - do not skip steps.

<process>

<step name="1_call_cli" priority="first">
## Step 1: Get Phase Context from CLI

```bash
python3 -m erirpg.cli coder-execute-phase $ARGUMENTS
```

The CLI returns JSON with:
- `phase_dir`: Path to phase directory
- `phase_number`: Phase number
- `phase_name`: Phase name
- `goal`: Phase goal from ROADMAP.md
- `plans`: List of plans with paths, waves, completion status
- `waves`: Grouped wave structure
- `settings`: Execution settings (includes `model_profile`)
- `instructions`: High-level guidance

**It also creates EXECUTION_STATE.json** - hooks will allow file edits.

Parse and store these values for use in subsequent steps.

### Resolve Model Profile

Extract the model profile from settings and resolve models for executor and verifier:

```bash
MODEL_PROFILE=$(cat .planning/config.json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('model_profile', 'balanced'))
except: print('balanced')
" 2>/dev/null || echo "balanced")
```

**Model lookup table:**

| Profile | Executor | Verifier |
|---------|----------|----------|
| quality | opus | sonnet |
| balanced | sonnet | sonnet |
| budget | sonnet | haiku |

Resolve:

```bash
case "$MODEL_PROFILE" in
  quality)  EXECUTOR_MODEL="opus";  VERIFIER_MODEL="sonnet" ;;
  budget)   EXECUTOR_MODEL="sonnet"; VERIFIER_MODEL="haiku" ;;
  *)        EXECUTOR_MODEL="sonnet"; VERIFIER_MODEL="sonnet" ;;
esac
```

Report: `Model profile: {MODEL_PROFILE} (executor={EXECUTOR_MODEL}, verifier={VERIFIER_MODEL})`
</step>

<step name="2_load_state">
## Step 2: Load Project State

Read and internalize project state:

```bash
cat .planning/STATE.md 2>/dev/null
```

Parse:
- Current position (phase, plan, status)
- Accumulated decisions (constraints on execution)
- Blockers/concerns (things to watch for)

**If STATE.md missing:** Warn user but continue - will create at completion.
</step>

<step name="3_validate_phase">
## Step 3: Validate Phase Ready

Confirm phase exists and has plans:

```bash
PHASE_DIR=$(ls -d .planning/phases/${PHASE_NUM}-* 2>/dev/null | head -1)
PLAN_COUNT=$(ls -1 "$PHASE_DIR"/*-PLAN.md 2>/dev/null | wc -l)
```

**If no plans found:** Error - run `/coder:plan-phase {N}` first.

Report: "Found {N} plans in {phase_dir}"
</step>

<step name="4_discover_plans">
## Step 4: Discover Plans and Wave Structure

List all plans and their status:

```bash
# All plans
ls -1 "$PHASE_DIR"/*-PLAN.md 2>/dev/null | sort

# Completed plans (have SUMMARY.md)
ls -1 "$PHASE_DIR"/*-SUMMARY.md 2>/dev/null | sort
```

For each plan, read frontmatter to extract:
- `wave: N` - Execution wave
- `autonomous: true/false` - Has checkpoints?
- `gap_closure: true/false` - Closing verification gaps?

**Build plan inventory:**

| Plan | Wave | Status | Autonomous |
|------|------|--------|------------|
| 01 | 1 | pending | yes |
| 02 | 1 | pending | yes |
| 03 | 2 | pending | no |

**Filtering:**
- Skip completed plans (have SUMMARY.md)
- If `--gaps-only`: Also skip plans where `gap_closure` is not `true`

**If all plans filtered out:** Report "All plans already complete" and skip to verification.
</step>

<step name="5_report_wave_structure">
## Step 5: Report Execution Plan

Before executing, show what will happen:

```markdown
## Execution Plan

**Phase {X}: {Name}** — {total_plans} plans across {wave_count} waves

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1 | 01, 02 | {from plan objectives} |
| 2 | 03 | {from plan objectives} |
```

The "What it builds" column comes from reading each plan's `<objective>` section.
</step>

<step name="6_execute_waves">
## Step 6: Execute Waves

Execute each wave in sequence. Plans within a wave run in parallel.

**For each wave:**

### 6a. Describe What's Being Built

Read each plan's `<objective>` section. Output:

```markdown
---

## Wave {N}

**Plan {ID}: {Name}**
{2-3 sentences: what this builds, key approach, why it matters}

Spawning {count} executor(s)...

---
```

### 6b. Read Plan Files

Before spawning, read each plan file content. The @ syntax doesn't work across Task() boundaries.

```bash
PLAN_CONTENT=$(cat "{plan_path}")
STATE_CONTENT=$(cat .planning/STATE.md 2>/dev/null)
```

### 6c. Spawn Executors

For each plan in the wave, spawn **eri-executor** with resolved model:

```
Task(
  subagent_type="eri-executor",
  model="{EXECUTOR_MODEL}",
  prompt="Execute plan {plan_number} of phase {phase_number}-{phase_name}.

<plan>
{plan_content}
</plan>

<project_state>
{state_content}
</project_state>

Execute all tasks, commit each atomically, create SUMMARY.md, update STATE.md.
Report completion with: plan ID, tasks completed, SUMMARY path, commit hashes."
)
```

**Spawn all plans in wave simultaneously** (parallel execution).

### 6d. Wait and Verify

Wait for all executors in wave to complete. For each:

1. Verify SUMMARY.md exists at expected path
2. Read SUMMARY.md to extract what was built
3. Note any issues or deviations

### 6e. Report Wave Completion

```markdown
---

## Wave {N} Complete

**Plan {ID}: {Name}**
{What was built — from SUMMARY.md deliverables}
{Notable deviations, if any}

{If more waves: "Enables Wave {N+1}: {brief}"}

---
```

### 6f. Update STATE.md (Mid-Execution)

**CRITICAL: Update STATE.md after each wave, not just at completion.**

```markdown
## Current Phase
**Phase {N}: {phase-name}** - executing (wave {X}/{Y} complete)

## Last Action
Completed wave {X}
- Plans executed: {list}
- Total progress: {completed}/{total} plans
```

### 6g. Handle Failures

If any executor in wave fails:

```
Executor failed for plan {ID}: {error}

Options:
1. Retry - Spawn executor again
2. Skip - Mark as failed, continue to next wave
3. Abort - Stop execution, preserve state
```

**Wait for user decision.** Do NOT proceed automatically.

### 6h. Proceed to Next Wave

Continue until all waves complete.
</step>

<step name="7_verification" priority="critical">
## Step 7: Verification (MANDATORY - BLOCKS PROGRESS)

After all waves complete, you **MUST** spawn **eri-verifier**.

**This step is NOT optional. Do NOT skip to completion.**

```bash
# Get phase goal from ROADMAP
PHASE_GOAL=$(grep -A 5 "Phase $PHASE_NUM" .planning/ROADMAP.md | head -6)
```

Spawn verifier with resolved model:

```
Task(
  subagent_type="eri-verifier",
  model="{VERIFIER_MODEL}",
  prompt="Verify phase {phase_number} goal achievement.

Phase directory: {phase_dir}
Phase goal: {phase_goal}

Check must_haves against actual codebase (not SUMMARY claims).
Create VERIFICATION.md with status: passed/gaps_found/human_needed.
Return status and gap summary if any."
)
```

**Wait for verifier to complete.**

### 7a. Check Verification Result

```bash
VERIFICATION_STATUS=$(grep "^status:" "$PHASE_DIR"/VERIFICATION.md | cut -d: -f2 | tr -d ' ')
```

### 7b. Route by Status

| Status | Action |
|--------|--------|
| `passed` | Proceed to completion |
| `human_needed` | Present items to user, wait for approval |
| `gaps_found` | **BLOCK** - Present gaps, offer fix command |

**If `gaps_found`:**

<offer_next>

```markdown
╔════════════════════════════════════════════════════════════════╗
║  ⚠ VERIFICATION FOUND GAPS                                     ║
╠════════════════════════════════════════════════════════════════╣
║  Score: {N}/{M} must-haves verified                            ║
║  Report: {phase_dir}/VERIFICATION.md                           ║
╚════════════════════════════════════════════════════════════════╝

### What's Missing

{Extract gap summaries from VERIFICATION.md}

## ▶ NEXT: Fix the gaps

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase {N} --gaps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After gap plans are created:  /coder:execute-phase {N} --gaps-only

## Alternatives
- View full report:  Read {phase_dir}/VERIFICATION.md
- Skip gaps:         /coder:verify-work {N} (user acceptance)
```

</offer_next>

**Do NOT proceed to completion. Do NOT call coder-end-plan.**

**If `human_needed`:**

```markdown
## ✓ Automated Checks Passed — Human Verification Required

{N} items need human testing:

### Human Verification Checklist

{Extract from VERIFICATION.md human_verification section}

---

After testing, respond:
- "approved" → I'll complete the phase
- Describe issues → I'll route to gap closure
```

**Wait for user response.**

**If `passed`:**

### 7c. Mark Requirements Complete

After verification passes, mark this phase's requirements as complete:

1. Read ROADMAP.md, find this phase's `**Requirements:**` line (e.g., "AUTH-01, AUTH-02")
2. Parse the REQ-IDs from that line
3. Read REQUIREMENTS.md
4. For each REQ-ID from this phase:
   - Change `- [ ] **{REQ-ID}**` to `- [x] **{REQ-ID}**` in v1 requirements section
5. Read ROADMAP.md Coverage Matrix
6. For each REQ-ID from this phase:
   - Change `| {REQ-ID} | ... | Pending |` to `| {REQ-ID} | ... | Complete |`

**Skip if:** REQUIREMENTS.md doesn't exist, or phase has no Requirements line in ROADMAP.md.

Proceed to completion.
</step>

<step name="8_finalize">
## Step 8: Finalize Phase

**Only reach this step if verification status is `passed`.**

### 8a. Call CLI to End Plan

```bash
python3 -m erirpg.cli coder-end-plan
```

This removes EXECUTION_STATE.json and marks phase complete.

### 8b. Verify Git Status Clean

```bash
git status --short
```

If uncommitted files exist, commit them:
```bash
git add .planning/phases/{phase_dir}/
git commit -m "chore(phase-{N}): complete execution and verification"
```
</step>

</process>

<completion>
## On Completion

### 1. Update STATE.md

```markdown
## Current Phase
**Phase {N}: {phase-name}** - complete (verified)

## Last Action
Completed execute-phase {N}
- Plans executed: {X}/{Y}
- Verification: passed

## Next Step
Run `/coder:verify-work {N}` for user acceptance testing
Or proceed to next phase: `/coder:plan-phase {N+1}`
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

<offer_next>

**Primary route (UAT):**
```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE {N} EXECUTED AND VERIFIED                             ║
╠════════════════════════════════════════════════════════════════╣
║  Plans completed: {X}/{Y}                                      ║
║  Verification: passed                                          ║
║  Model profile: {MODEL_PROFILE}                                ║
║  Commits: {commit hashes}                                      ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: User Acceptance Testing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:verify-work {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Alternatives
- Skip UAT, plan next:   /coder:plan-phase {N+1}
- View what was built:   /coder:progress
- Check verification:    Read .planning/phases/{NN-name}/VERIFICATION.md
```

</offer_next>
</completion>

<agent_failure_handling>
## If Agent Spawn Fails

If the Task tool returns an error (API 500, timeout, rejection):

1. **Retry once** - transient errors are common
2. **If still fails, STOP and report:**
   ```
   Agent spawn failed for {context}: {error}

   Options:
   - Retry: I can try spawning the agent again
   - Skip: Mark as failed and continue (creates gap)
   - Abort: Stop execution, preserve state for later
   ```
3. **DO NOT execute the work yourself** - That defeats isolated context
4. **Wait for user decision** - Don't proceed until user responds
</agent_failure_handling>

<critical_rules>
## Critical Rules

1. **Never skip verification** - Step 7 MUST run before completion
2. **Never proceed on gaps_found** - Must fix gaps first
3. **Update STATE.md after each wave** - Not just at completion
4. **Wait for user on failures** - Don't auto-proceed
5. **Show the completion box** - Never say "ready when you are"
</critical_rules>
