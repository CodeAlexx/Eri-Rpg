---
name: coder:execute-phase
description: Execute all plans for a phase with wave-based parallelization
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Bash
  - Task
---

# Execute Phase

**Run the CLI command. Follow its output exactly.**

```bash
python3 -m erirpg.cli coder-execute-phase $ARGUMENTS
```

The CLI returns everything you need:
- Plans to execute (with paths and wave assignments)
- Wave groupings for parallel execution
- Current completion state
- Settings (parallelization, verifier enabled, etc.)

**It also creates EXECUTION_STATE.json automatically** - hooks will allow file edits.

## After CLI Returns

Follow the `instructions` field in the JSON output exactly:

1. For each wave in order, spawn **eri-executor** for each plan in that wave
2. Pass the full plan content to each executor (read the plan file first)
3. Wait for wave completion (all executors done, SUMMARY.md files exist)
4. **MANDATORY: Spawn eri-verifier** after all waves complete

## Verification is MANDATORY

After all plans execute, you MUST spawn **eri-verifier** to:
- Check must_haves against actual codebase (not SUMMARY claims)
- Create VERIFICATION.md with status: passed/gaps_found/human_needed
- Block completion if verification fails

**The phase CANNOT be marked complete without VERIFICATION.md having `status: passed`.**

If verification finds gaps:
1. Do NOT call coder-end-plan
2. Report gaps to user
3. Offer `/coder:plan-phase {N} --gaps` to create fix plans
4. Re-execute and re-verify until passed

## If Agent Spawn Fails

If the Task tool returns an error (API 500, timeout, rejection):

1. **Retry once** - transient errors are common
2. **If still fails, STOP and report:**
   ```
   Agent spawn failed for {plan}: {error}

   Options:
   - Retry: I can try spawning the agent again
   - Skip plan: Mark as failed and continue (creates gap)
   - Abort: Stop execution, preserve state for later
   ```
3. **DO NOT execute the plan yourself** - That's what agents are for
4. **Wait for user decision** - Don't proceed until user responds

**Why this matters:** Manual execution causes context exhaustion and quality degradation.
Agents have isolated context - that's by design.

## On Completion

Only after verification passes:

```bash
python3 -m erirpg.cli coder-end-plan
```

This checks verification status and:
- If passed: Removes EXECUTION_STATE.json, marks phase complete
- If failed: **BLOCKS** completion, returns error with instructions

**Never bypass verification.** Use `--force` only in emergencies (will mark phase as incomplete).
