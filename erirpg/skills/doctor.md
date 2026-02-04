---
name: coder:doctor
description: Diagnose workflow health and identify issues
argument-hint: "[--fix] [--fix-research] [--fix-verification] [--reinstall-hooks] [--rebuild-state]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
---

# Coder Doctor

Diagnose the health of your coder workflow setup. Identifies issues that cause failures like Phase 5 (no research, status not updated, verification skipped).

<process>

<step name="1_header">
## Coder Workflow Health Check

```
╔════════════════════════════════════════════════════════════════╗
║  🩺 CODER DOCTOR                                                ║
╚════════════════════════════════════════════════════════════════╝
```
</step>

<step name="2_global_state">
## Check 1: Global State

```bash
cat ~/.eri-rpg/state.json 2>/dev/null
```

**Verify:**
- [ ] File exists
- [ ] `target_project_path` is set and points to valid directory
- [ ] `target_project` matches directory name

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| File missing | `/coder:init` fails | Run any coder command to create |
| `target_project_path` stale | Wrong project after `/clear` | Edit file or run `/coder:switch-project` |
| Invalid JSON | All commands fail | Delete and recreate |

```
Global State: {OK | WARN | ERROR}
  - target_project: {name}
  - target_project_path: {path}
  - path_valid: {yes|no}
```
</step>

<step name="3_project_state">
## Check 2: Project State

```bash
# Check .planning/ exists
ls -la .planning/ 2>/dev/null

# Check required files
cat .planning/PROJECT.md 2>/dev/null | head -5
cat .planning/ROADMAP.md 2>/dev/null | head -10
cat .planning/STATE.md 2>/dev/null | head -15
cat .planning/config.json 2>/dev/null
```

**Verify:**
- [ ] `.planning/` directory exists
- [ ] `PROJECT.md` exists with project name
- [ ] `ROADMAP.md` exists with phases
- [ ] `STATE.md` exists with current position
- [ ] `config.json` exists (optional but recommended)

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| No .planning/ | Not a coder project | Run `/coder:new-project` or `/coder:add-feature` |
| Missing STATE.md | Can't resume | Run `/coder:init` to reconstruct |
| Missing ROADMAP.md | No phases defined | Critical - need to recreate project |
| Stale STATE.md | Position doesn't match reality | Run `/coder:init` to resync |

```
Project State: {OK | WARN | ERROR}
  - .planning/ exists: {yes|no}
  - PROJECT.md: {ok|missing}
  - ROADMAP.md: {ok|missing} ({N} phases)
  - STATE.md: {ok|missing|stale}
  - config.json: {ok|missing}
```
</step>

<step name="4_execution_state">
## Check 3: Execution State

```bash
cat .planning/EXECUTION_STATE.json 2>/dev/null
```

**Verify:**
- [ ] If exists: mid-execution, hooks allow edits
- [ ] If missing: not executing, hooks block edits (expected)

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| Stale EXECUTION_STATE.json | Edits allowed when shouldn't be | `python3 -m erirpg.cli coder-end-plan --force` |
| Missing during execute-phase | Hooks block edits | CLI should auto-create; check CLI output |

```
Execution State: {ACTIVE | IDLE}
  - EXECUTION_STATE.json: {exists|missing}
  - Phase: {N if active}
  - Started: {timestamp if active}
```
</step>

<step name="5_phase_health">
## Check 4: Phase Health

```bash
# List all phases
ls -d .planning/phases/*/ 2>/dev/null

# For each phase, check artifacts
for phase in .planning/phases/*/; do
  echo "=== $phase ==="
  ls -1 "$phase"/*.md 2>/dev/null
done
```

**For each phase, verify:**
- [ ] Has PLAN.md file(s)
- [ ] Plans have SUMMARY.md (if executed)
- [ ] Has VERIFICATION.md (if executed)
- [ ] VERIFICATION.md status is `passed` (if complete)

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| Plans without SUMMARY | Execution incomplete | Re-run `/coder:execute-phase N` |
| No VERIFICATION.md | Verification skipped | Re-run `/coder:execute-phase N` (will verify) |
| VERIFICATION.md gaps_found | Phase not truly complete | `/coder:plan-phase N --gaps` then execute |
| RESEARCH.md missing (Level 2-3) | Poor planning | Re-run `/coder:plan-phase N` |

```
Phase Health:
  - Phase 1: {status} - {N}/{M} plans complete, verification: {status}
  - Phase 2: {status} - {N}/{M} plans complete, verification: {status}
  ...
```
</step>

<step name="6_research_gaps">
## Check 5: Research Gaps

For each phase, detect if research was needed but missing:

```bash
for phase_dir in .planning/phases/*/; do
  phase_name=$(basename "$phase_dir")

  # Get phase goal from ROADMAP
  goal=$(grep -A 3 "$phase_name" .planning/ROADMAP.md 2>/dev/null | head -4)

  # Check for Level 2-3 indicators
  if echo "$goal" | grep -qiE "architect|design|system|security|auth|database|schema|integrat|api|external|library"; then
    # Should have research
    if [ ! -f "${phase_dir}RESEARCH.md" ]; then
      echo "WARN: $phase_name needs research (Level 2-3 indicators) but has no RESEARCH.md"
    fi
  fi
done
```

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| Level 2-3 phase without RESEARCH.md | Plans may be inadequate | Re-run `/coder:plan-phase N` (will research) |

```
Research Gaps:
  - Phase 3 (authentication): MISSING - Level 3 indicators found
  - Phase 5 (api-integration): MISSING - Level 2 indicators found
```
</step>

<step name="7_verification_status">
## Check 6: Verification Status

```bash
for phase_dir in .planning/phases/*/; do
  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
    score=$(grep "^score:" "${phase_dir}VERIFICATION.md" | cut -d: -f2)
    echo "$(basename $phase_dir): $status ($score)"
  fi
done
```

**Issues:**
| Status | Meaning | Action |
|--------|---------|--------|
| `passed` | Phase complete | None needed |
| `gaps_found` | Phase incomplete | `/coder:plan-phase N --gaps` |
| `human_needed` | Awaiting user testing | Complete manual verification |

```
Verification Status:
  - Phase 1: passed (5/5)
  - Phase 2: passed (3/3)
  - Phase 3: gaps_found (2/4) ⚠️
  - Phase 4: human_needed (4/4, 2 manual checks pending) ⚠️
```
</step>

<step name="8_hooks_status">
## Check 7: Hooks Installation

```bash
# Check Claude Code hooks
ls -la ~/.claude/hooks/ 2>/dev/null

# Check if our hooks are installed
grep -l "erirpg" ~/.claude/hooks/*.py 2>/dev/null
```

**Verify:**
- [ ] `~/.claude/hooks/` exists
- [ ] `sessionstart.py` contains erirpg import
- [ ] `posttooluse.py` contains erirpg import (if using edit enforcement)
- [ ] `pretooluse.py` contains erirpg import (if using edit enforcement)

**Issues:**
| Problem | Symptom | Fix |
|---------|---------|-----|
| Hooks dir missing | No automation | Create `~/.claude/hooks/` |
| Missing sessionstart hook | No auto-recovery after /clear | Reinstall erirpg |
| Missing pretooluse hook | Edit enforcement disabled | Reinstall erirpg |

```
Hooks Status: {OK | WARN | ERROR}
  - sessionstart.py: {installed|missing}
  - posttooluse.py: {installed|missing}
  - pretooluse.py: {installed|missing}
```
</step>

<step name="9_skills_status">
## Check 8: Skills Installation

```bash
# Check coder skills are installed
ls -la ~/.claude/commands/coder/ 2>/dev/null | head -20

# Count skills
skill_count=$(ls -1 ~/.claude/commands/coder/*.md 2>/dev/null | wc -l)
echo "Installed skills: $skill_count"
```

**Verify:**
- [ ] `~/.claude/commands/coder/` exists
- [ ] Key skills present: init.md, plan-phase.md, execute-phase.md, doctor.md

```
Skills Status: {OK | WARN | ERROR}
  - Directory: {exists|missing}
  - Skill count: {N}
  - Key skills: {all present | missing: X, Y}
```
</step>

<step name="10_summary">
## Summary

```
╔════════════════════════════════════════════════════════════════╗
║  DIAGNOSIS COMPLETE                                             ║
╠════════════════════════════════════════════════════════════════╣
║  Global State:     {OK|WARN|ERROR}                              ║
║  Project State:    {OK|WARN|ERROR}                              ║
║  Execution State:  {ACTIVE|IDLE}                                ║
║  Phase Health:     {N}/{M} phases healthy                       ║
║  Research Gaps:    {N} phases missing research                  ║
║  Verification:     {N} phases need attention                    ║
║  Hooks:            {OK|WARN|ERROR}                              ║
║  Skills:           {OK|WARN|ERROR}                              ║
╚════════════════════════════════════════════════════════════════╝
```

### Issues Found

{List all issues with severity}

### Recommended Actions

{Prioritized list of fixes}

1. **{CRITICAL}** {issue} → {fix command}
2. **{HIGH}** {issue} → {fix command}
3. **{MEDIUM}** {issue} → {fix command}
</step>

<step name="11_auto_fix">
## Auto-Fix (if --fix flag)

If user passed `--fix`, attempt automatic repairs:

**Safe to auto-fix:**
- Reconstruct STATE.md from artifacts
- Remove stale EXECUTION_STATE.json
- Update global state to current project

**Requires confirmation:**
- Re-run research for missing RESEARCH.md
- Re-run verification for phases with gaps

**Cannot auto-fix:**
- Missing .planning/ directory
- Missing ROADMAP.md
- Corrupted config.json

```bash
# Example auto-fixes
if [ "$FIX_MODE" = "true" ]; then
  # Fix stale execution state
  if [ -f ".planning/EXECUTION_STATE.json" ]; then
    echo "Removing stale EXECUTION_STATE.json..."
    python3 -m erirpg.cli coder-end-plan --force
  fi

  # Fix global state
  echo "Updating global state..."
  python3 -m erirpg.cli switch "$(pwd)"
fi
```
</step>

<step name="12_fix_research">
## Repair: --fix-research

Auto-spawn researcher for phases missing RESEARCH.md that need it (Level 2-3 indicators).

**When to use:** Doctor found "RESEARCH.md missing" for phases with external integrations, APIs, or architectural decisions.

### Process

1. **Identify phases needing research:**

```bash
PHASES_NEED_RESEARCH=()
for phase_dir in .planning/phases/*/; do
  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  # Skip if RESEARCH.md exists
  [ -f "${phase_dir}RESEARCH.md" ] && continue

  # Get phase goal
  goal=$(grep -A 5 "Phase $phase_num" .planning/ROADMAP.md 2>/dev/null)

  # Check for Level 2-3 indicators
  if echo "$goal" | grep -qiE "architect|design|system|security|auth|database|schema|integrat|api|external|library|choose|select|evaluat"; then
    PHASES_NEED_RESEARCH+=("$phase_num:$phase_name")
  fi
done
```

2. **Confirm with user:**

```
Found {N} phases needing research:
  - Phase 3: authentication (Level 3 - security indicators)
  - Phase 5: api-integration (Level 2 - external API)

Spawn researcher for each? (yes/no/select)
```

3. **For each confirmed phase, spawn eri-phase-researcher:**

```
Task(
  subagent_type="eri-phase-researcher",
  prompt="Research implementation for phase {phase_number}: {phase_name}

<depth>{detected_depth}</depth>

<phase_goal>
{goal from ROADMAP.md}
</phase_goal>

<context_md>
{CONTEXT.md content if exists, else 'None'}
</context_md>

<existing_patterns>
{Key patterns from codebase}
</existing_patterns>

Create {phase_dir}/RESEARCH.md with recommended approach, confidence level, and pitfalls."
)
```

4. **Verify research created:**

```bash
for phase in $FIXED_PHASES; do
  if [ -f ".planning/phases/${phase}/RESEARCH.md" ]; then
    confidence=$(grep "^confidence:" ".planning/phases/${phase}/RESEARCH.md" | cut -d: -f2 | tr -d ' ')
    echo "✅ Phase ${phase}: RESEARCH.md created (confidence: $confidence)"
  else
    echo "❌ Phase ${phase}: Research failed"
  fi
done
```
</step>

<step name="13_fix_verification">
## Repair: --fix-verification

Re-run verification for phases that were executed but have no VERIFICATION.md or have `gaps_found` status.

**When to use:** Doctor found phases with completed plans but missing/failed verification.

### Process

1. **Identify phases needing verification:**

```bash
PHASES_NEED_VERIFY=()
for phase_dir in .planning/phases/*/; do
  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  # Check if any plans were executed (have SUMMARY.md)
  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)
  [ "$summary_count" -eq 0 ] && continue  # Not executed

  # Check verification status
  if [ ! -f "${phase_dir}VERIFICATION.md" ]; then
    PHASES_NEED_VERIFY+=("$phase_num:missing")
  else
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
    if [ "$status" = "gaps_found" ]; then
      PHASES_NEED_VERIFY+=("$phase_num:gaps_found")
    fi
  fi
done
```

2. **Confirm with user:**

```
Found {N} phases needing verification:
  - Phase 2: VERIFICATION.md missing
  - Phase 4: gaps_found (2/5 must-haves)

Run verification for each? (yes/no/select)
```

3. **For each confirmed phase, spawn eri-verifier:**

```bash
# Get phase goal
PHASE_GOAL=$(grep -A 5 "Phase $PHASE_NUM" .planning/ROADMAP.md | head -6)
```

```
Task(
  subagent_type="eri-verifier",
  prompt="Verify phase {phase_number} goal achievement.

Phase directory: {phase_dir}
Phase goal: {phase_goal}

Check must_haves against actual codebase (not SUMMARY claims).
Create VERIFICATION.md with status: passed/gaps_found/human_needed.
Return status and gap summary if any."
)
```

4. **Report results:**

```
Verification Results:
  - Phase 2: ✅ passed (5/5 must-haves)
  - Phase 4: ⚠️ gaps_found (3/5) - run /coder:plan-phase 4 --gaps
```
</step>

<step name="14_reinstall_hooks">
## Repair: --reinstall-hooks

Reinstall hooks from the erirpg package to ~/.claude/hooks/.

**When to use:** Doctor found hooks missing or outdated.

### Process

1. **Check current hook status:**

```bash
echo "Current hooks:"
ls -la ~/.claude/hooks/*.py 2>/dev/null || echo "  (none)"

echo ""
echo "EriRPG hook sources:"
ERIRPG_PATH=$(python3 -c "import erirpg; print(erirpg.__path__[0])" 2>/dev/null)
ls -la "${ERIRPG_PATH}/hooks/"*.py 2>/dev/null || echo "  (not found)"
```

2. **Show what will be installed:**

```
Will install/update these hooks:
  - sessionstart.py (auto-recovery after /clear)
  - pretooluse.py (edit enforcement)
  - posttooluse.py (state tracking)

Existing hooks will be backed up to *.backup.{timestamp}

Proceed? (yes/no)
```

3. **Backup and install:**

```bash
TIMESTAMP=$(date +%Y%m%d%H%M%S)
ERIRPG_PATH=$(python3 -c "import erirpg; print(erirpg.__path__[0])")

# Ensure hooks directory exists
mkdir -p ~/.claude/hooks

# Backup existing
for hook in sessionstart pretooluse posttooluse; do
  if [ -f ~/.claude/hooks/${hook}.py ]; then
    cp ~/.claude/hooks/${hook}.py ~/.claude/hooks/${hook}.py.backup.${TIMESTAMP}
  fi
done

# Copy from package
cp "${ERIRPG_PATH}/hooks/"*.py ~/.claude/hooks/

echo "✅ Hooks installed"
```

4. **Verify installation:**

```bash
for hook in sessionstart pretooluse posttooluse; do
  if [ -f ~/.claude/hooks/${hook}.py ]; then
    if grep -q "erirpg" ~/.claude/hooks/${hook}.py; then
      echo "✅ ${hook}.py: installed with erirpg integration"
    else
      echo "⚠️ ${hook}.py: exists but no erirpg import"
    fi
  else
    echo "❌ ${hook}.py: missing"
  fi
done
```
</step>

<step name="15_rebuild_state">
## Repair: --rebuild-state

Full STATE.md reconstruction from all artifacts when STATE.md is missing, corrupted, or severely out of sync.

**When to use:** STATE.md is missing, unreadable, or doesn't reflect actual project state.

### Process

1. **Gather all artifacts:**

```bash
echo "=== Scanning artifacts ==="

# Project info
PROJECT_NAME=$(grep "^# " .planning/PROJECT.md 2>/dev/null | head -1 | cut -d' ' -f2-)
echo "Project: $PROJECT_NAME"

# Count phases from ROADMAP
TOTAL_PHASES=$(grep -c "^## Phase" .planning/ROADMAP.md 2>/dev/null || echo "0")
echo "Total phases: $TOTAL_PHASES"

# Analyze each phase
for phase_dir in .planning/phases/*/; do
  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  # Count plans
  plan_count=$(ls -1 "${phase_dir}"*-PLAN.md 2>/dev/null | wc -l)
  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)

  # Check verification
  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    verify_status=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
  else
    verify_status="none"
  fi

  # Determine phase status
  if [ "$verify_status" = "passed" ]; then
    status="complete"
  elif [ "$summary_count" -gt 0 ]; then
    status="executed (verification: $verify_status)"
  elif [ "$plan_count" -gt 0 ]; then
    status="planned"
  else
    status="pending"
  fi

  echo "Phase $phase_num: $status ($summary_count/$plan_count plans done)"
done
```

2. **Determine current position:**

```bash
# Find first incomplete phase
CURRENT_PHASE=""
for phase_dir in .planning/phases/*/; do
  phase_num=$(basename "$phase_dir" | cut -d- -f1)

  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
    [ "$status" = "passed" ] && continue
  fi

  # Found incomplete phase
  CURRENT_PHASE="$phase_num"
  break
done

# If all complete, we're done
[ -z "$CURRENT_PHASE" ] && CURRENT_PHASE="complete"
```

3. **Generate STATE.md:**

```markdown
---
project: {PROJECT_NAME}
milestone: v1.0
reconstructed: {YYYY-MM-DDTHH:MM:SSZ}
---

# {PROJECT_NAME} - Workflow State

## Current Position
**Phase {N}: {phase-name}** - {status}

## Phase Summary

| Phase | Status | Plans | Verified |
|-------|--------|-------|----------|
| 1 | {status} | {M}/{N} | {passed/gaps/none} |
| 2 | {status} | {M}/{N} | {passed/gaps/none} |
...

## Accumulated Decisions
{Extract from CONTEXT.md files if they exist}

## Last Action
State reconstructed by /coder:doctor --rebuild-state

## Next Step
{Based on current position}
```

4. **Write and verify:**

```bash
# Backup existing if present
[ -f .planning/STATE.md ] && cp .planning/STATE.md .planning/STATE.md.backup.$(date +%Y%m%d%H%M%S)

# Write new STATE.md
cat > .planning/STATE.md << 'EOF'
{generated content}
EOF

echo "✅ STATE.md reconstructed"
echo ""
echo "Summary:"
cat .planning/STATE.md
```
</step>

</process>

<common_issues>
## Common Issues Reference

### "Edits blocked by hook"
- **Cause:** No EXECUTION_STATE.json but trying to edit
- **Fix:** Run `/coder:execute-phase N` or `/coder:quick` for ad-hoc work

### "Wrong project after /clear"
- **Cause:** Stale `target_project_path` in global state
- **Fix:** Edit `~/.eri-rpg/state.json` or run `/coder:switch-project`

### "Phase complete but verification failed"
- **Cause:** Verification step was skipped (old workflow bug)
- **Fix:** Re-run `/coder:execute-phase N` - will run verification

### "Research not done for external integration"
- **Cause:** Research was optional in old workflow
- **Fix:** Re-run `/coder:plan-phase N` - will detect depth and research

### "STATE.md not updated"
- **Cause:** Completion section not reached
- **Fix:** Run `/coder:init` to resync from artifacts
</common_issues>
