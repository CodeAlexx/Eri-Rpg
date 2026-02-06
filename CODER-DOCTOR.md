# /coder:doctor - Workflow Health Diagnostics

Diagnose and repair coder workflow issues. Created after Phase 5 failure analysis revealed gaps in research enforcement, verification blocking, and state updates.

## Quick Start

```bash
# Run diagnostics
/coder:doctor

# Run diagnostics with basic auto-fix
/coder:doctor --fix

# Fix specific issues
/coder:doctor --fix-research        # Spawn researcher for missing RESEARCH.md
/coder:doctor --fix-verification    # Re-run verification for incomplete phases
/coder:doctor --reinstall-hooks     # Reinstall hooks from package
/coder:doctor --rebuild-state       # Reconstruct STATE.md from artifacts
```

## Health Checks

Doctor runs 8 health checks to identify workflow issues:

### Check 1: Global State

**File:** `~/.eri-rpg/state.json`

| What | How |
|------|-----|
| File exists | Must exist for session recovery |
| `target_project_path` valid | Points to directory with .planning/ |
| `target_project` matches | Consistent with directory name |

**Common Issues:**
- Stale path after `/clear` → Run `/coder:switch-project`
- Invalid JSON → Delete and recreate
- File missing → Run any coder command to create

### Check 2: Project State

**Directory:** `.planning/`

| File | Required | Purpose |
|------|----------|---------|
| PROJECT.md | Yes | Project name and description |
| ROADMAP.md | Yes | Phase definitions and goals |
| STATE.md | Yes | Current position and progress |
| config.json | Recommended | Workflow settings |

**Common Issues:**
- No `.planning/` → Not a coder project, run `/coder:new-project`
- Missing STATE.md → Run `/coder:init` to reconstruct
- Stale STATE.md → Run `/coder:init` to resync

### Check 3: Execution State

**File:** `.planning/EXECUTION_STATE.json`

| State | Meaning |
|-------|---------|
| Exists | Mid-execution, hooks allow file edits |
| Missing | Not executing, hooks block edits (expected) |

**Common Issues:**
- Stale file after crash → `python3 -m erirpg.cli coder-end-plan --force`
- Missing during execute-phase → CLI should auto-create; check CLI output

### Check 4: Phase Health

**Directory:** `.planning/phases/*/`

For each phase, checks:
- Has PLAN.md file(s)
- Plans have SUMMARY.md (if executed)
- Has VERIFICATION.md (if executed)
- VERIFICATION.md status is `passed` (if complete)

**Common Issues:**
- Plans without SUMMARY → Re-run `/coder:execute-phase N`
- No VERIFICATION.md → Re-run `/coder:execute-phase N` (will verify)
- VERIFICATION.md gaps_found → `/coder:plan-phase N --gaps` then execute

### Check 5: Research Gaps

Detects phases that need research but don't have RESEARCH.md.

**Level 2-3 Indicators (require research):**
- Keywords: architect, design, system, security, auth, database, schema
- Keywords: integrate, api, external, library, choose, select, evaluate

**Common Issues:**
- Level 2-3 phase without RESEARCH.md → Re-run `/coder:plan-phase N`

### Check 6: Verification Status

Checks VERIFICATION.md status for each phase:

| Status | Meaning | Action |
|--------|---------|--------|
| `passed` | Phase complete | None needed |
| `gaps_found` | Phase incomplete | `/coder:plan-phase N --gaps` |
| `human_needed` | Awaiting user testing | Complete manual verification |

### Check 7: Hooks Installation

**Directory:** `~/.claude/hooks/`

| Hook | Purpose |
|------|---------|
| sessionstart.py | Auto-recovery after /clear |
| pretooluse.py | Edit enforcement (blocks edits without plan) |
| posttooluse.py | State tracking |

**Common Issues:**
- Hooks dir missing → Create `~/.claude/hooks/`
- Missing hooks → Reinstall erirpg or use `--reinstall-hooks`

### Check 8: Skills Installation

**Directory:** `~/.claude/commands/coder/`

Checks for key skills:
- init.md
- plan-phase.md
- execute-phase.md
- doctor.md

## Repair Capabilities

### --fix (Basic Auto-Fix)

Safe automatic repairs:
- Remove stale EXECUTION_STATE.json
- Update global state to current project
- Sync target_project_path

```bash
/coder:doctor --fix
```

### --fix-research

Spawns eri-phase-researcher for phases missing RESEARCH.md that have Level 2-3 indicators.

**Process:**
1. Scans phases for Level 2-3 keywords in goals
2. Identifies phases without RESEARCH.md
3. Confirms with user before spawning
4. Spawns eri-phase-researcher with detected depth
5. Verifies RESEARCH.md created with confidence rating

```bash
/coder:doctor --fix-research
```

**Example output:**
```
Found 2 phases needing research:
  - Phase 3: authentication (Level 3 - security indicators)
  - Phase 5: api-integration (Level 2 - external API)

Spawn researcher for each? (yes/no/select)
```

### --fix-verification

Re-runs verification for phases that were executed but have missing or failed verification.

**Process:**
1. Identifies phases with SUMMARY.md but no/failed VERIFICATION.md
2. Confirms with user
3. Spawns eri-verifier for each phase
4. Reports results (passed/gaps_found/human_needed)

```bash
/coder:doctor --fix-verification
```

**Example output:**
```
Found 2 phases needing verification:
  - Phase 2: VERIFICATION.md missing
  - Phase 4: gaps_found (2/5 must-haves)

Verification Results:
  - Phase 2: passed (5/5 must-haves)
  - Phase 4: gaps_found (3/5) - run /coder:plan-phase 4 --gaps
```

### --reinstall-hooks

Reinstalls hooks from the erirpg package to ~/.claude/hooks/.

**Process:**
1. Shows current hook status
2. Lists what will be installed
3. Backs up existing hooks (*.backup.{timestamp})
4. Copies hooks from package
5. Verifies installation

```bash
/coder:doctor --reinstall-hooks
```

### --rebuild-state

Full STATE.md reconstruction when the file is missing, corrupted, or severely out of sync.

**Process:**
1. Scans all artifacts (PROJECT.md, ROADMAP.md, phases)
2. Counts plans, summaries, verification status per phase
3. Determines current position (first incomplete phase)
4. Generates new STATE.md with full phase summary
5. Backs up existing STATE.md if present

```bash
/coder:doctor --rebuild-state
```

**Reconstructed STATE.md includes:**
- Project name and milestone
- Current position (phase and status)
- Phase summary table (status, plans, verification)
- Accumulated decisions (from CONTEXT.md files)
- Next step recommendation

## Common Issues Reference

### "Edits blocked by hook"

**Cause:** No EXECUTION_STATE.json but trying to edit files.

**Fix:** Run `/coder:execute-phase N` or `/coder:quick` for ad-hoc work.

### "Wrong project after /clear"

**Cause:** Stale `target_project_path` in global state.

**Fix:** Edit `~/.eri-rpg/state.json` or run `/coder:switch-project`.

### "Phase complete but verification failed"

**Cause:** Verification step was skipped (old workflow bug, now fixed).

**Fix:** Re-run `/coder:execute-phase N` - will run verification.

### "Research not done for external integration"

**Cause:** Research was optional in old workflow (now mandatory for Level 2-3).

**Fix:** Re-run `/coder:plan-phase N` - will detect depth and research.

### "STATE.md not updated"

**Cause:** Completion section not reached during execution.

**Fix:** Run `/coder:init` to resync from artifacts, or `--rebuild-state` for full reconstruction.

## Output Format

Doctor produces a summary box after all checks:

```
╔════════════════════════════════════════════════════════════════╗
║  DIAGNOSIS COMPLETE                                             ║
╠════════════════════════════════════════════════════════════════╣
║  Global State:     OK                                           ║
║  Project State:    OK                                           ║
║  Execution State:  IDLE                                         ║
║  Phase Health:     4/5 phases healthy                           ║
║  Research Gaps:    1 phases missing research                    ║
║  Verification:     1 phases need attention                      ║
║  Hooks:            OK                                           ║
║  Skills:           OK                                           ║
╚════════════════════════════════════════════════════════════════╝

### Issues Found

1. **HIGH** Phase 3 missing RESEARCH.md (Level 3 indicators)
2. **MEDIUM** Phase 4 verification gaps_found

### Recommended Actions

1. **HIGH** Run `/coder:plan-phase 3` to research authentication
2. **MEDIUM** Run `/coder:plan-phase 4 --gaps` to close verification gaps
```

## Background: Why Doctor Exists

Doctor was created after analyzing Phase 5 execution failures. The audit found:

1. **Research was optional** - External integrations proceeded without proper research
2. **Verification wasn't enforced** - Phases marked complete despite gaps
3. **STATE.md only updated at completion** - Progress lost on interruption
4. **Orchestrator skills too thin** - "Follow CLI output" delegated too much

Doctor provides visibility into these issues and tools to repair them.
