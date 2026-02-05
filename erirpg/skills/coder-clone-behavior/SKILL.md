---
name: coder:clone-behavior
description: Clone a program by extracting behaviors and reimplementing from scratch
argument-hint: "<source-path> <new-project-name> [--language rust] [--framework candle]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

# Coder Clone-Behavior

Clone an entire program by extracting WHAT it does (behavior), not HOW it's coded.
Then reimplement from scratch - same functionality, completely different code.

## Dynamic Context

**CLI analysis:**
!`python3 -m erirpg.commands.clone_behavior $ARGUMENTS --json 2>/dev/null || echo '{"error": "CLI failed or dry-run needed"}'`

**Clone state (if resuming):**
!`cat clone-state.json 2>/dev/null || echo '{"status": "not_started"}'`

---

## CLI Options

```bash
python3 -m erirpg.commands.clone_behavior <source-path> <new-project-name> [options] --json
```

| Option | Description |
|--------|-------------|
| `--language <lang>` | Target language (default: same as source) |
| `--framework <framework>` | Target framework |
| `--skip-tests` | Don't extract test contracts |
| `--dry-run` | Show plan without executing |
| `--modules <list>` | Only clone specific modules (comma-separated) |
| `--exclude <list>` | Skip specific modules (comma-separated) |

---

## The 5 Phases

```
SOURCE ──► SCAN ──► PLAN ──► IMPLEMENT ──► VERIFY ──► COMPLETE ──► TARGET
         (extract)  (roadmap)  (build)     (diff)    (finalize)
```

### Phase 1: SCAN - Extract Behaviors

1. Map source codebase with `eri-codebase-mapper`
2. Extract BEHAVIOR.md for each module with `eri-behavior-extractor`
3. Verify all behaviors extracted

**Parallel execution:** Up to 4 behavior extraction agents.

See [reference.md](reference.md#phase-1-scan) for details.

### Phase 2: PLAN - Create Roadmap

1. Initialize target project directory
2. Copy BEHAVIOR.md files to target
3. Create PROJECT.md with clone context
4. Create REQUIREMENTS.md from behaviors
5. Generate ROADMAP.md with `eri-roadmapper`

See [reference.md](reference.md#phase-2-plan) for details.

### Phase 3: IMPLEMENT - Build From Behaviors

For each module phase:
1. `/coder:plan-phase N` - Plan from BEHAVIOR.md (NOT source code)
2. `/coder:execute-phase N` - Implement in target language idioms
3. `/coder:verify-work N` - Quick verification

**Key principle:** Code should look like it was written by someone who never saw the source.

See [reference.md](reference.md#phase-3-implement) for details.

### Phase 4: VERIFY - Behavior Diff

For each module:
1. Run behavior verification
2. Check interface, state machine, tests, resources, ownership
3. Fix any ❌ violations before proceeding
4. Document ⚠️ manual checks

See [reference.md](reference.md#phase-4-verify) for details.

### Phase 5: COMPLETE - Finalize

1. Generate CLONE-VERIFICATION.md report
2. Tag release with `/coder:complete-milestone v1.0`
3. Final commit

See [reference.md](reference.md#phase-5-complete) for details.

---

## Agent Strategy

| Phase | Agent | Model |
|-------|-------|-------|
| SCAN | eri-codebase-mapper, eri-behavior-extractor | sonnet |
| PLAN | eri-roadmapper | sonnet |
| IMPLEMENT | eri-planner, eri-executor | opus (complex), sonnet (simple) |
| VERIFY | Built-in verification | sonnet |

---

## Error Recovery

Check progress:
```bash
python3 -m erirpg.commands.clone_behavior progress --json
```

Resume from failed step (not beginning).

---

## Completion

Use [templates/completion-box.md](templates/completion-box.md) format.

Update STATE.md with:
- Modules cloned count
- Behaviors verified count
- Next step: Run and compare with source
