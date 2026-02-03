# /coder:replay - Re-Run With Different Parameters

Re-execute a phase or plan with modified parameters, different approach, or updated context.

## CLI Integration

**First, call the CLI to get replay context:**
```bash
# Get context for entire phase
erirpg coder-replay 2

# Get context for specific plan
erirpg coder-replay 2 --plan 3
```

This returns JSON with:
- `phase`: Phase number
- `phase_dir`: Path to phase directory
- `plans`: Array of {path, name} for PLAN.md files
- `summaries`: Array of {path, name} for SUMMARY.md files

Use this context to prepare for re-execution.

---

## Usage

```
/coder:replay 2                    # Replay phase 2
/coder:replay 2 --plan 03          # Replay specific plan
/coder:replay 2 --from-scratch     # Regenerate plans entirely
/coder:replay 2 --with "use Redis" # Replay with new constraint
/coder:replay 2 --keep-decisions   # Preserve previous decisions
```

## When to Use

- Verification failed, need different approach
- New requirement discovered mid-phase
- Want to try alternative implementation
- Context changed (new dependency, API change)
- Learning from mistakes in original run

## Execution Steps

### Step 1: Analyze Original Execution

```python
original = {
    "phase": load_phase(2),
    "plans": load_phase_plans(2),
    "summaries": load_phase_summaries(2),
    "decisions": extract_decisions(2),
    "issues": extract_issues(2),
    "duration": calculate_duration(2)
}
```

### Step 2: Present Replay Options

```markdown
## Replay Options: Phase 2

**Original Execution:**
- Duration: 45 minutes
- Plans: 3
- Status: gaps_found (verification failed)

### Issues from Original Run
1. API validation too strict (Plan 02-02)
2. Auth middleware missing refresh logic (Plan 02-03)
3. Integration tests incomplete (Plan 02-03)

### Replay Modes

**A. Fix Issues Only** (Recommended)
- Keep successful work
- Regenerate failed plans only
- Apply lessons learned
- Est. time: 15 minutes

**B. Different Approach**
- Keep phase goal
- Regenerate all plans with new context
- Apply your specified changes
- Est. time: 30 minutes

**C. From Scratch**
- Rollback all phase work
- Re-plan with fresh perspective
- Ignore previous decisions
- Est. time: 45 minutes

Select mode (A/B/C) or specify custom:
```

### Step 3: Prepare Replay Context

**Lessons Learned Document:**
```markdown
---
replay_of: phase-02
original_run: 2026-01-30T10:00:00Z
---

# Lessons from Phase 2 Original Run

## What Worked
- Database schema design (Plan 02-01)
- User model implementation (Plan 02-01)
- Basic route structure (Plan 02-02)

## What Failed
- Validation was too strict for legacy data
- Auth middleware didn't handle token refresh
- Tests didn't cover edge cases

## Decisions to Preserve
- Use Prisma for database (worked well)
- JWT for auth tokens (keep)
- Zod for validation (keep, but loosen rules)

## Decisions to Reconsider
- Validation strictness: Loosen for optional fields
- Token refresh: Add sliding window refresh
- Test coverage: Add edge case tests

## New Context
{User's --with parameter if specified}
```

### Step 4: Execute Replay

**Mode A: Fix Issues Only**
```python
def replay_fix_issues(phase, issues):
    # Identify failed plans
    failed_plans = [p for p in phase.plans if has_gaps(p)]

    for plan in failed_plans:
        # Create fix version
        fix_plan = regenerate_plan_with_fixes(
            plan,
            issues=issues,
            lessons=lessons_learned
        )

        # Execute fix
        execute_plan(fix_plan)

        # Verify
        verify_plan(fix_plan)
```

**Mode B: Different Approach**
```python
def replay_different_approach(phase, new_context):
    # Rollback existing work
    rollback_phase(phase, keep_decisions=True)

    # Re-plan with new context
    new_plans = replan_phase(
        phase,
        additional_context=new_context,
        lessons=lessons_learned
    )

    # Execute new plans
    execute_phase(phase)
```

**Mode C: From Scratch**
```python
def replay_from_scratch(phase):
    # Full rollback
    rollback_phase(phase, keep_decisions=False)

    # Clear all planning artifacts
    clear_phase_plans(phase)

    # Start fresh
    plan_phase(phase)
    execute_phase(phase)
```

### Step 5: Apply User Modifications

If `--with` specified:
```python
# Parse modification
modification = parse_with_arg(args.with_context)

# Add to phase context
phase.additional_context.append({
    "type": "replay_modification",
    "content": modification,
    "applied": timestamp
})

# Regenerate affected plans
for plan in phase.plans:
    if affects_plan(modification, plan):
        regenerate_plan(plan, modification)
```

### Step 6: Track Replay

```markdown
## STATE.md Update

### Replay History
- 2026-01-30 14:00: Replayed Phase 2
  Mode: Fix Issues Only
  Original duration: 45 min
  Replay duration: 15 min
  Changes:
    - Loosened validation rules
    - Added token refresh logic
    - Expanded test coverage
  Result: All verification passed
```

### Step 7: Report

```markdown
## Replay Complete: Phase 2

**Mode:** Fix Issues Only
**Duration:** 15 minutes (vs 45 original)

### Fixed Issues
| Issue | Fix Applied | Status |
|-------|-------------|--------|
| Validation too strict | Loosened optional field rules | ✅ |
| Missing token refresh | Added sliding window refresh | ✅ |
| Incomplete tests | Added 12 edge case tests | ✅ |

### Verification
All must-haves now pass:
- [x] User registration works
- [x] Login returns valid token
- [x] Token refresh works
- [x] Protected routes enforce auth

### Commits
- abc123: fix(02-02): Loosen validation for optional fields
- def456: feat(02-03): Add token refresh middleware
- 789xyz: test(02-03): Add auth edge case tests

### Next Steps
Continue to Phase 3: `/coder:plan-phase 3`
```

## Replay Comparison

After replay, compare with original:

```markdown
## Replay vs Original

| Metric | Original | Replay | Δ |
|--------|----------|--------|---|
| Duration | 45 min | 15 min | -67% |
| Commits | 12 | 3 | -75% |
| Files changed | 15 | 5 | -67% |
| Tests added | 8 | 12 | +50% |
| Verification | Failed | Passed | ✅ |

### Key Improvements
1. Token refresh now handles edge cases
2. Validation accepts null optional fields
3. Test coverage increased to 85%
```

## Partial Replay

Replay only specific plans:
```
/coder:replay 2 --plan 03 --plan 04
```

## Keep Decisions

Preserve decisions from original run:
```
/coder:replay 2 --keep-decisions
```

Loads decisions from original SUMMARY files and applies them to new plans.

## Integration Points

- Reads: Original plans, summaries, verification results
- Creates: Lessons learned document, new plans
- Modifies: Existing plans if --fix-only
- Rollback: If --from-scratch
- Updates: STATE.md with replay history
