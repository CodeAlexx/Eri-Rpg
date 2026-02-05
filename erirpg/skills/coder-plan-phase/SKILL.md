---
name: coder:plan-phase
description: Create executable plans with verification criteria for a phase. Use after discussing phase requirements.
argument-hint: "<phase-number> [--gaps]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
---

# Plan Phase

Create executable plans for a phase. Orchestrates research → planning → validation.

## Dynamic Context

**Phase info from CLI:**
!`python3 -m erirpg.cli coder-plan-phase $ARGUMENTS 2>/dev/null || echo '{"error": "CLI failed"}'`

**Project state:**
!`cat .planning/STATE.md 2>/dev/null | head -20`

**Phase goal from ROADMAP:**
!`grep -A 5 "Phase $0" .planning/ROADMAP.md 2>/dev/null | head -6`

**Existing research:**
!`ls .planning/phases/$0-*/RESEARCH.md 2>/dev/null && echo "exists" || echo "none"`

**Existing context:**
!`ls .planning/phases/$0-*/CONTEXT.md 2>/dev/null && echo "exists" || echo "none"`

---

## Planning Flow

### 1. Parse CLI Response

Extract: `phase_number`, `phase_name`, `phase_dir`, `goal`, `has_context`, `has_research`

### 2. Detect Research Depth

**Level 0 - Skip:** Pure internal work, existing patterns only
**Level 1 - Quick:** Confirm known library syntax (2-5 min)
**Level 2 - Standard:** New library, external API, choose between options (15-30 min)
**Level 3 - Deep:** Architecture, security, database design (1+ hour)

Run detection: `./scripts/detect-depth.sh "$goal"`

See [reference.md](reference.md#research-depth-indicators) for full indicator list.

### 3. Execute Research (if depth > 0)

**Level 1:** Inline verification, no agent needed.

**Level 2-3:** Spawn **eri-phase-researcher**:

```
Task(
  subagent_type="eri-phase-researcher",
  prompt="Research implementation for phase {phase_number}: {phase_name}

<depth>{RESEARCH_DEPTH}</depth>
<phase_goal>{goal}</phase_goal>
<context_md>{CONTEXT.md content or 'None'}</context_md>

Create {phase_dir}/RESEARCH.md with:
- Recommended approach with rationale
- Integration points with existing code
- Pitfalls specific to this phase
- Confidence level (HIGH/MEDIUM/LOW)"
)
```

**Confidence gate:**

| Confidence | Action |
|------------|--------|
| HIGH | Proceed to planning |
| MEDIUM | Warn user, proceed |
| LOW | **STOP** — see [low-confidence template](templates/low-confidence.md) |

### 4. Create Plans

Spawn **eri-planner** with full context:

```
Task(
  subagent_type="eri-planner",
  prompt="Create execution plans for phase {phase_number}: {phase_name}

<project>{PROJECT.md content}</project>
<roadmap>{ROADMAP.md content}</roadmap>
<state>{STATE.md content}</state>
<context>{CONTEXT.md or 'No CONTEXT.md'}</context>
<research>{RESEARCH.md or 'Level 0 - no research'}</research>
<mode>{'gap_closure' if --gaps else 'standard'}</mode>

Create PLAN.md files with:
- 2-3 tasks per plan (stay under 50% context)
- Wave assignments for parallel execution
- must_haves in frontmatter (goal-backward derived)
- Runtime verification criteria"
)
```

### 5. Validate Plans (if enabled)

Check `config.json` for `plan_check: true` (default).

Spawn **eri-plan-checker**:

```
Task(
  subagent_type="eri-plan-checker",
  prompt="Validate plans for phase {phase_number}

<phase_dir>{phase_dir}</phase_dir>
<context>{CONTEXT.md content}</context>

Check: requirement coverage, task completeness, dependencies,
key links, scope sanity, must-haves derivation, context compliance.

Return: Issues with severity, or 'PASSED'."
)
```

**If issues:** Spawn planner in revision mode.

### 6. Commit Plans

```bash
git add .planning/phases/{phase_dir}/
git commit -m "plan(phase-{N}): create execution plans for {phase_name}"
```

### 7. Completion

Update STATE.md and show [completion box](templates/completion-box.md).

---

## CONTEXT.md Flow

If CONTEXT.md exists, it flows through entire pipeline:

| Stage | How Used |
|-------|----------|
| Research | Locked: don't research alternatives. Discretion: research freely. Deferred: ignore. |
| Planning | Locked: implement exactly. Discretion: best call. Deferred: exclude. |
| Checking | Verify locked decisions have tasks, deferred excluded. |

**Never skip CONTEXT.md.** Every agent receives it.

---

## Critical Rules

1. **Research mandatory for Level 2-3** — Don't skip external integrations
2. **Stop on LOW confidence** — Get user approval first
3. **CONTEXT.md flows everywhere** — Every agent receives it
4. **Plan check catches issues** — Don't skip validation
5. **Show completion box** — Never say "ready when you are"

For detailed documentation, see [reference.md](reference.md).
