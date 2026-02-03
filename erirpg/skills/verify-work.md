---
name: coder:verify-work
description: Manual user acceptance testing for a completed phase
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Task
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to gather verification context:**
```bash
erirpg coder-verify-work 3
```

This returns JSON with:
- `phase`: Phase number
- `phase_goal`: Goal from ROADMAP.md
- `phase_dir`: Path to phase directory
- `must_haves`: Object with truths, artifacts, key_links
- `has_verification`: Whether VERIFICATION.md already exists
- `verification_status`: Status of existing verification

Use this data to create the verification checklist for the user.

---

<objective>
Guide user through manual acceptance testing of a completed phase.
User tests each deliverable, reports results.
Any failures trigger eri-debugger to find root cause.
</objective>

<context>
Phase number: $ARGUMENTS
Read: VERIFICATION.md, ROADMAP.md (phase goal), must_haves from PLANs
Output: .planning/phases/{XX-name}/{phase}-UAT.md
</context>

<process>
## Step 1: Load Phase Info
```bash
cat .planning/phases/{XX-name}/{phase}-VERIFICATION.md
cat .planning/ROADMAP.md
```

Extract:
- Phase goal
- Must-haves (truths, artifacts, key_links)
- Testable deliverables

## Step 2: Present Test Checklist
For each truth (observable behavior):

```
## Test {N}: {truth description}

**How to test:**
1. {step 1}
2. {step 2}
3. {expected outcome}

**Your result:** [ ] Works [ ] Broken
```

Use AskUserQuestion:
- "Does {truth} work as expected?"
- Options: "Works perfectly", "Works with minor issues", "Broken", "Can't test"

## Step 3: Collect Results
For each deliverable user tests:
- Record result (works / broken + description)
- If "broken" selected, ask for details

## Step 4: Debug Failures
For each broken item, spawn eri-debugger agent in `find_root_cause_only` mode:
- Pass: symptom description, expected vs actual
- Debugger investigates and returns ROOT CAUSE
- Does NOT fix (that's for re-planning)

Collect all diagnoses.

## Step 5: Write UAT.md
Create .planning/phases/{XX-name}/{phase}-UAT.md:

```markdown
---
phase: XX-name
tested: {timestamp}
status: passed | failed | partial
tester: user
---

# Phase {N}: User Acceptance Testing

## Test Results

### Passed
| Test | Description | Notes |
|------|-------------|-------|
| T1 | User can log in | Works on Chrome and Firefox |

### Failed
| Test | Description | Issue | Root Cause |
|------|-------------|-------|------------|
| T3 | Password reset | Email not sent | SMTP config missing |

## Diagnoses

### Issue 1: {title}
**Symptom:** {what user observed}
**Expected:** {what should happen}
**Root Cause:** {from debugger}
**Fix Approach:** {suggested fix}

## Recommendation
{passed: proceed to next phase}
{failed: run /coder:plan-phase N --gaps to address issues}
```

## Step 6: Route by Status
- **All passed** → Mark phase verified, suggest next phase or milestone
- **Some failed** → Offer `/coder:plan-phase {N} --gaps` to close gaps
- **Can't test** → Note what needs manual setup, pause for user
</process>

<completion>
When UAT complete:
1. Show pass/fail summary
2. For failures: show root causes found
3. Suggest next action:
   - All pass → `/coder:complete-milestone` (if last phase) or next phase
   - Failures → `/coder:plan-phase {N} --gaps`
</completion>
