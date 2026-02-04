# Audit: GSD vs Coder Workflow

**Date:** 2026-02-03
**Issue:** Phase 5 execution failed to do proper research, update status, and had other errors
**Status:** FIXED (2026-02-03)

---

## Executive Summary

| Area | GSD | Coder | Gap Severity |
|------|-----|-------|--------------|
| Research/Discovery | 290 lines, 3 depth levels, mandatory | 127 lines, optional, thin | **CRITICAL** |
| Execute-Phase Orchestrator | 672 lines, detailed steps | 150 lines, "follow CLI" | **HIGH** |
| Executor Agent | ~700 lines in workflow | 868 lines, comprehensive | OK |
| Verifier | 289+ lines | 950 lines | OK |
| STATE.md Updates | Explicit in every step | In completion sections | **MEDIUM** |
| Completion Flow | Structured offer_next | Completion box | OK |

---

## Critical Gap 1: Research is Optional and Thin

### GSD Discovery (discovery-phase.md)

```
Depth Levels:
- Level 1: Quick Verify (2-5 min) - Context7 only, no file output
- Level 2: Standard (15-30 min) - Creates DISCOVERY.md
- Level 3: Deep Dive (1+ hour) - Comprehensive DISCOVERY.md + validation gates

Mandatory Protocol:
1. Context7 MCP FIRST - current docs, no hallucination
2. Official docs when Context7 lacks coverage
3. WebSearch LAST - for comparisons only

Confidence Gates:
- LOW confidence → Ask user: "Dig deeper / Proceed anyway / Pause"
- MEDIUM → "Proceed? (yes/no)"
- HIGH → Auto-proceed
```

### Coder Research (eri-phase-researcher.md - 127 lines)

```
Research Process:
1. Understand the phase goal
2. Check CONTEXT.md
3. Research implementation
4. Check existing code
5. Identify gaps

No depth levels
No confidence gates
No Context7 integration mentioned
Optional based on settings.workflow.research
```

### The Problem

**plan-phase.md line 33-34:**
```markdown
1. If `settings.workflow.research` is true and no RESEARCH.md exists:
   - Spawn **eri-phase-researcher** first
```

- Research is **conditional** on a setting
- The researcher agent is too thin (127 lines vs GSD's 290)
- No depth levels - treats all phases the same
- No confidence gates - proceeds even when unsure
- No mandatory Context7 integration

### Fix Required

1. Make research **mandatory** for new/external integrations (detect Level 2-3 indicators)
2. Add depth levels to eri-phase-researcher
3. Add confidence gates that stop execution on LOW
4. Integrate Context7 before WebSearch

---

## Critical Gap 2: Execute-Phase Orchestrator is Too Thin

### GSD execute-phase.md (672 lines)

Has these explicit steps:
1. `resolve_model_profile` - Get model settings
2. `load_project_state` - Read STATE.md, config.json
3. `handle_branching` - Git branching strategy
4. `validate_phase` - Confirm phase exists with plans
5. `discover_plans` - List all plans, extract metadata
6. `group_by_wave` - Read wave numbers, group plans
7. `execute_waves` - Detailed wave execution with context descriptions
8. `checkpoint_handling` - Full checkpoint protocol
9. `aggregate_results` - Combine all wave results
10. `verify_phase_goal` - Spawn verifier **with explicit routing**
11. `update_roadmap` - Update ROADMAP.md
12. `offer_next` - Clear next steps

Each step has bash commands and explicit logic.

### Coder execute-phase.md (150 lines)

```markdown
# Execute Phase

**Run the CLI command. Follow its output exactly.**

```bash
python3 -m erirpg.cli coder-execute-phase $ARGUMENTS
```

## After CLI Returns

Follow the `instructions` field in the JSON output exactly:
1. For each wave in order, spawn **eri-executor** for each plan
2. Wait for wave completion
3. **MANDATORY: Spawn eri-verifier** after all waves complete
```

### The Problem

- "Follow CLI output exactly" delegates ALL logic to CLI
- If CLI doesn't output comprehensive instructions, steps get skipped
- No explicit wave orchestration logic in skill file
- Verification is "MANDATORY" in docs but not **enforced**
- No explicit STATE.md update during execution (only in completion)

### What Likely Happened in Phase 5

1. CLI returned JSON with phase info
2. Claude spawned executors
3. Executors completed
4. **Verification step was mentioned but not enforced** - likely skipped
5. **Completion section never ran** - STATE.md not updated
6. **Research was skipped** - setting was false or not checked

### Fix Required

1. Move orchestration logic from "trust the CLI" to explicit steps
2. Add checkpoints that **block progress** until verification passes
3. Make STATE.md updates happen at each step, not just completion
4. Add explicit verification enforcement (not just "MANDATORY" comment)

---

## Medium Gap 3: STATE.md Update Flow

### GSD Pattern

STATE.md is updated:
- In `load_project_state` (read and confirm)
- In `aggregate_results` (after execution)
- In `update_roadmap` (with commit)
- Executor updates STATE.md after each plan
- Explicit commit after updates

### Coder Pattern

STATE.md updates are in:
- `plan-phase.md` completion section
- `execute-phase.md` completion section
- `eri-executor.md` state_updates step

**BUT:**
- Completion sections only run if Claude reaches them
- If Claude gets distracted or context compacts, completion is skipped
- No mid-execution STATE.md updates in orchestrator

### Fix Required

1. Add STATE.md update after each wave completes (not just at end)
2. Make STATE.md updates happen BEFORE spawning next agent
3. Add explicit git commits for STATE.md updates

---

## Comparison: What GSD Does Right

### 1. Thick Workflows, Thin Commands

GSD puts logic in workflow files (400-700 lines each). Commands are thin entry points.

Coder inverted this: Skills are thin (~100-150 lines) and say "follow CLI".

**The problem:** When skills say "follow CLI output", they rely on:
- CLI outputting comprehensive instructions
- Claude interpreting JSON correctly
- Claude not skipping steps

### 2. Explicit Step Sequencing

GSD uses `<step name="X">` with explicit ordering and dependencies.

```xml
<step name="load_project_state">
  ...
</step>

<step name="validate_phase">
  ...
</step>
```

Coder uses prose: "After CLI returns, do X, then Y, then Z"

**The problem:** Prose instructions are easier to skip or misinterpret.

### 3. Mandatory Verification Before Proceed

GSD execute-phase.md line 474-570 has explicit verification routing:

```markdown
**Route by status:**

| Status | Action |
|--------|--------|
| `passed` | Continue to update_roadmap |
| `human_needed` | Present items to user, get approval or feedback |
| `gaps_found` | Present gap summary, offer `/gsd:plan-phase {phase} --gaps` |
```

Coder says "MANDATORY: Spawn eri-verifier" but doesn't have explicit routing logic.

### 4. Agent Tracking

GSD has `current-agent-id.txt` and `agent-history.json` to track spawned agents.

Coder doesn't track agent spawns - if an agent fails, there's no record.

---

## Recommendations

### Immediate Fixes

1. **Thicken execute-phase.md** - Add explicit step-by-step logic, not "follow CLI"

2. **Add verification enforcement** - After spawning verifier, check VERIFICATION.md exists and status != gaps_found before proceeding

3. **Add mid-execution STATE.md updates** - After each wave, update STATE.md with progress

4. **Make research conditional but smart** - Detect Level 2-3 indicators and make research mandatory for those

### Structural Changes

1. **Move orchestration logic from CLI to skills** - CLI returns data, skills have the workflow logic

2. **Add explicit step markers** - Use `<step name="X">` pattern from GSD

3. **Add agent tracking** - Record agent spawns in EXECUTION_STATE.json

4. **Add confidence gates** - Stop execution on LOW confidence findings

---

## Phase 5 Post-Mortem

Based on the symptoms:

| Issue | Root Cause | Fix |
|-------|------------|-----|
| No proper research | Research is optional (`settings.workflow.research`) | Make mandatory for external integrations |
| STATUS.md not updated | Completion section never ran | Add mid-execution updates |
| Other errors | Verification likely skipped | Add enforcement that blocks progress |

### Likely Execution Flow

```
1. /coder:plan-phase 5
   - CLI called
   - Research skipped (setting false or not checked)
   - Planner spawned without research context
   - Plans created (possibly inadequate)

2. /coder:execute-phase 5
   - CLI called, returned plans
   - Executors spawned
   - Executors completed (possibly with issues)
   - Verifier NOT spawned (skipped or failed)
   - Completion section NOT reached
   - STATE.md NOT updated

3. User sees incomplete state
   - No VERIFICATION.md
   - STATE.md outdated
   - Phase appears incomplete
```

---

## Files Modified (FIXED)

| File | Change | Status |
|------|--------|--------|
| `erirpg/skills/execute-phase.md` | Added 8 explicit steps with verification enforcement | ✓ DONE (150→430 lines) |
| `erirpg/skills/plan-phase.md` | Added research depth detection, confidence gates | ✓ DONE (140→434 lines) |
| `erirpg/agents/eri-phase-researcher.md` | Added depth levels 1-3, source hierarchy, confidence | ✓ DONE (127→394 lines) |
| `erirpg/cli_commands/coder_cmds.py` | Add verification status check | DEFERRED |
| New: agent tracking in EXECUTION_STATE.json | Track spawned agents | DEFERRED |

---

## Appendix: Line Counts

| File | GSD | Coder |
|------|-----|-------|
| execute-phase orchestrator | 672 | 150 |
| execute-plan/eri-executor | ~700 | 868 |
| verify-phase/eri-verifier | 289+ | 950 |
| discovery-phase/eri-phase-researcher | 290 | 127 |
| plan-phase (in workflows vs skills) | ~500 | 140 |

Coder has thicker agents but thinner orchestrators. The orchestration gap is the problem.
