# Doctor Reference

Detailed documentation for health checks and repairs.

---

## Health Checks

### Check 0: Contract Lint

Run workflow linter to catch skill/command contract drift:

```bash
python3 -m erirpg.cli coder-linter --verbose
```

**If fails:** Mark diagnosis as WARN. Recommend fixing linter failures before deeper repairs.

### Check 1: Global State

**File:** `~/.eri-rpg/state.json`

**Verify:**
- File exists
- `target_project_path` points to valid directory
- `target_project` matches directory name

**Issues:**

| Problem | Symptom | Fix |
|---------|---------|-----|
| File missing | `/coder:init` fails | Run any coder command |
| Stale path | Wrong project after `/clear` | `/coder:switch-project` |
| Invalid JSON | All commands fail | Delete and recreate |

### Check 2: Project State

**Directory:** `.planning/`

**Required files:**
- `PROJECT.md` - project name
- `ROADMAP.md` - phase definitions
- `STATE.md` - current position
- `config.json` - settings (optional)

**Issues:**

| Problem | Symptom | Fix |
|---------|---------|-----|
| No .planning/ | Not a coder project | `/coder:new-project` |
| Missing STATE.md | Can't resume | `/coder:init` |
| Missing ROADMAP.md | Critical | Recreate project |

### Check 3: Execution State

**File:** `.planning/EXECUTION_STATE.json`

| State | Meaning |
|-------|---------|
| Exists | Mid-execution, hooks allow edits |
| Missing | Not executing, hooks block edits |

**Issues:**

| Problem | Fix |
|---------|-----|
| Stale file | `python3 -m erirpg.cli coder-end-plan --force` |
| Missing during execute | CLI should auto-create |

### Check 4: Phase Health

For each phase in `.planning/phases/*/`:

- Has PLAN.md file(s)
- Plans have SUMMARY.md (if executed)
- Has VERIFICATION.md (if executed)
- VERIFICATION.md status is `passed`

**Issues:**

| Problem | Fix |
|---------|-----|
| Plans without SUMMARY | Re-run `/coder:execute-phase N` |
| No VERIFICATION.md | Re-run `/coder:execute-phase N` |
| gaps_found status | `/coder:plan-phase N --gaps` |

### Check 5: Research Gaps

Detect phases needing research (Level 2-3 indicators) but missing RESEARCH.md.

**Level 2-3 indicators:** architect, design, system, security, auth, database, schema, integrate, api, external, library

### Check 6: Verification Status

Check VERIFICATION.md status for each phase:

| Status | Meaning | Action |
|--------|---------|--------|
| `passed` | Complete | None |
| `gaps_found` | Incomplete | `/coder:plan-phase N --gaps` |
| `human_needed` | Needs testing | Manual verification |

### Check 7: Hooks Installation

**Directory:** `~/.claude/hooks/`

**Required hooks:**
- `sessionstart.py` - auto-recovery after /clear
- `pretooluse.py` - edit enforcement
- `posttooluse.py` - state tracking

### Check 8: Skills Installation

**Directory:** `~/.claude/commands/coder/`

**Key skills:** init.md, plan-phase.md, execute-phase.md, doctor.md

---

## Repair Procedures

### --fix-research

1. **Find gaps:**
```bash
for phase_dir in .planning/phases/*/; do
  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  [ -f "${phase_dir}RESEARCH.md" ] && continue

  goal=$(grep -A 5 "Phase $phase_num" .planning/ROADMAP.md 2>/dev/null)

  if echo "$goal" | grep -qiE "architect|design|system|security|auth|database|schema|integrat|api|external|library|choose|select|evaluat"; then
    echo "$phase_num:$phase_name"
  fi
done
```

2. **Confirm with user**

3. **Spawn researcher:**
```
Task(
  subagent_type="eri-phase-researcher",
  prompt="Research implementation for phase {N}: {name}

<depth>{2 or 3}</depth>
<phase_goal>{goal}</phase_goal>
<context_md>{CONTEXT.md or 'None'}</context_md>

Create {phase_dir}/RESEARCH.md with approach, confidence, pitfalls."
)
```

4. **Verify:** Check RESEARCH.md created with confidence rating.

### --fix-verification

1. **Find gaps:**
```bash
for phase_dir in .planning/phases/*/; do
  phase_num=$(basename "$phase_dir" | cut -d- -f1)

  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)
  [ "$summary_count" -eq 0 ] && continue

  if [ ! -f "${phase_dir}VERIFICATION.md" ]; then
    echo "$phase_num:missing"
  else
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
    [ "$status" = "gaps_found" ] && echo "$phase_num:gaps_found"
  fi
done
```

2. **Confirm with user**

3. **Spawn verifier:**
```
Task(
  subagent_type="eri-verifier",
  prompt="Verify phase {N} goal achievement.

Phase directory: {phase_dir}
Phase goal: {goal}

Check must_haves against actual codebase.
Create VERIFICATION.md with status."
)
```

4. **Report results**

### --reinstall-hooks

1. **Backup existing:**
```bash
TIMESTAMP=$(date +%Y%m%d%H%M%S)
for hook in sessionstart pretooluse posttooluse; do
  [ -f ~/.claude/hooks/${hook}.py ] && \
    cp ~/.claude/hooks/${hook}.py ~/.claude/hooks/${hook}.py.backup.${TIMESTAMP}
done
```

2. **Copy from package:**
```bash
ERIRPG_PATH=$(python3 -c "import erirpg; print(erirpg.__path__[0])")
mkdir -p ~/.claude/hooks
cp "${ERIRPG_PATH}/hooks/"*.py ~/.claude/hooks/
```

3. **Verify:**
```bash
for hook in sessionstart pretooluse posttooluse; do
  grep -q "erirpg" ~/.claude/hooks/${hook}.py && echo "✅ $hook" || echo "❌ $hook"
done
```

### --rebuild-state

1. **Scan artifacts:**
```bash
PROJECT_NAME=$(grep "^# " .planning/PROJECT.md 2>/dev/null | head -1 | cut -d' ' -f2-)
TOTAL_PHASES=$(grep -c "^## Phase" .planning/ROADMAP.md 2>/dev/null || echo "0")

for phase_dir in .planning/phases/*/; do
  phase_num=$(basename "$phase_dir" | cut -d- -f1)
  plan_count=$(ls -1 "${phase_dir}"*-PLAN.md 2>/dev/null | wc -l)
  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)

  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    verify=$(grep "^status:" "${phase_dir}VERIFICATION.md" | cut -d: -f2 | tr -d ' ')
  else
    verify="none"
  fi

  echo "Phase $phase_num: plans=$plan_count, done=$summary_count, verify=$verify"
done
```

2. **Find current position** (first incomplete phase)

3. **Generate STATE.md** with phase summary table

4. **Backup and write**

---

## Common Issues

### "Edits blocked by hook"

**Cause:** No EXECUTION_STATE.json but trying to edit files.

**Fix:**
- Run `/coder:execute-phase N` for planned work
- Run `/coder:quick` for ad-hoc tasks

### "Wrong project after /clear"

**Cause:** `target_project_path` in global state points to old project.

**Fix:**
- Edit `~/.eri-rpg/state.json` directly
- Or run `/coder:switch-project`

### "Phase complete but verification failed"

**Cause:** Verification step was skipped (old workflow bug, now fixed).

**Fix:** Re-run `/coder:execute-phase N` — will run verification.

### "Research not done for external integration"

**Cause:** Research was optional in old workflow (now mandatory for Level 2-3).

**Fix:** Re-run `/coder:plan-phase N` — will detect depth and research.

### "STATE.md not updated"

**Cause:** Completion section not reached during execution.

**Fix:**
- Run `/coder:init` to resync from artifacts
- Or use `--rebuild-state` for full reconstruction
