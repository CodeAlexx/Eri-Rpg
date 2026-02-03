---
name: coder:plan-phase
description: Create executable plans with verification criteria for a phase
argument-hint: "<phase-number> [--gaps]"
allowed-tools:
  - Read
  - Bash
  - Task
---

# Plan Phase

**Run the CLI command. Follow its output exactly.**

```bash
python3 -m erirpg.cli coder-plan-phase $ARGUMENTS
```

For gap mode (re-planning from verification failures):
```bash
python3 -m erirpg.cli coder-plan-phase $ARGUMENTS --gaps
```

The CLI returns everything you need:
- Phase info and goal from ROADMAP.md
- Whether CONTEXT.md and RESEARCH.md exist
- Whether this is brownfield (has codebase docs)
- Settings (research enabled, plan_check enabled, etc.)
- Paths to all relevant files

## After CLI Returns

1. If `settings.workflow.research` is true and no RESEARCH.md exists:
   - Spawn **eri-phase-researcher** first

2. Spawn **eri-planner** with the context from CLI output:
   - Pass paths to PROJECT.md, ROADMAP.md, STATE.md
   - Pass CONTEXT.md if exists
   - Pass RESEARCH.md if exists
   - Pass codebase/* files if brownfield

3. If `settings.workflow.plan_check` is true:
   - Spawn **eri-plan-checker** to validate the plans:
     - Pass CONTEXT.md if exists (for context compliance checking)
     - Checker verifies plans honor locked decisions (Dimension 7)
   - If issues found, have planner revise

**IMPORTANT:** CONTEXT.md must flow through the ENTIRE pipeline:
- Researcher: constrains research scope (locked decisions vs discretion)
- Planner: must honor locked decisions exactly
- Checker: verifies context compliance (Dimension 7)
- Revision: maintains compliance when fixing issues

4. Commit the plans:
   ```bash
   git add .planning/phases/
   git commit -m "plan(phase-N): create execution plans"
   ```

## If Agent Spawn Fails

If the Task tool returns an error (API 500, timeout, rejection):

1. **Retry once** - transient errors are common
2. **If still fails, STOP and report:**
   ```
   Agent spawn failed: {error}

   Options:
   - Retry: I can try spawning the agent again
   - Manual: You can run the agent manually in a new session
   - Skip: Continue without this step (not recommended)
   ```
3. **DO NOT improvise** - Never try to do the agent's job yourself
4. **Wait for user decision** - Don't proceed until user responds

**Why this matters:** Improvising causes context drift and state inconsistencies.
The workflow is designed for agents - doing it manually breaks the system.

## On Completion

Suggest: `/coder:execute-phase N`
