---
name: coder:doctor
description: Diagnose workflow health and identify issues. Use when things seem broken or before resuming stale work.
argument-hint: "[--fix] [--fix-research] [--fix-verification] [--reinstall-hooks] [--rebuild-state]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
---

# Coder Doctor

Diagnose and repair coder workflow health.

## Dynamic Context

**Global state:**
!`cat ~/.eri-rpg/state.json 2>/dev/null || echo '{"error": "missing"}'`

**Project state:**
!`ls .planning/*.md .planning/*.json 2>/dev/null | head -10`

**Execution state:**
!`cat .planning/EXECUTION_STATE.json 2>/dev/null || echo "IDLE"`

**Phase count:**
!`ls -d .planning/phases/*/ 2>/dev/null | wc -l`

---

## Health Checks

Run all checks and build diagnosis:

### Check 0: Contract Lint
```bash
python3 -m erirpg.cli coder-linter --verbose 2>/dev/null || echo "Linter not available"
```

### Check 1-8: Run Diagnostic Script
```bash
./scripts/run-checks.sh
```

See [reference.md](reference.md) for detailed check documentation.

---

## Diagnosis Output

Use [templates/summary-box.md](templates/summary-box.md) format:

```
╔════════════════════════════════════════════════════════════════╗
║  DIAGNOSIS COMPLETE                                             ║
╠════════════════════════════════════════════════════════════════╣
║  Contract Lint:    {PASS|FAIL}                                  ║
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

List issues by severity (CRITICAL → HIGH → MEDIUM) with fix commands.

---

## Repair Flags

### --fix (Basic Auto-Fix)

Safe repairs without confirmation:
- Remove stale EXECUTION_STATE.json
- Update global state to current project

```bash
./scripts/basic-fix.sh
```

### --fix-research

Spawn eri-phase-researcher for phases missing RESEARCH.md.

1. Run `./scripts/find-research-gaps.sh`
2. Confirm with user
3. For each phase, spawn researcher (see [reference.md](reference.md#fix-research))
4. Verify RESEARCH.md created

### --fix-verification

Spawn eri-verifier for phases with missing/failed verification.

1. Run `./scripts/find-verification-gaps.sh`
2. Confirm with user
3. For each phase, spawn verifier (see [reference.md](reference.md#fix-verification))
4. Report results

### --reinstall-hooks

Reinstall hooks from erirpg package.

1. Backup existing hooks
2. Copy from package to ~/.claude/hooks/
3. Verify installation

See [reference.md](reference.md#reinstall-hooks) for details.

### --rebuild-state

Full STATE.md reconstruction from artifacts.

1. Scan all phases for plans/summaries/verification
2. Determine current position
3. Generate new STATE.md
4. Backup and write

See [reference.md](reference.md#rebuild-state) for details.

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Edits blocked by hook | No EXECUTION_STATE.json | `/coder:execute-phase N` or `/coder:quick` |
| Wrong project after /clear | Stale global state | `/coder:switch-project` |
| Phase complete but gaps | Verification skipped | Re-run `/coder:execute-phase N` |
| No research for API work | Research was optional | Re-run `/coder:plan-phase N` |
| STATE.md not updated | Completion not reached | `/coder:init` to resync |

See [reference.md](reference.md#common-issues) for full troubleshooting guide.
