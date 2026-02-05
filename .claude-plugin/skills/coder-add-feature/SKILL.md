---
name: coder:add-feature
description: Add a feature to an existing codebase (brownfield workflow)
argument-hint: "<feature-name> [description] [--reference <source>/<section>]"
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

# Coder Add-Feature

Add a new feature to an EXISTING codebase using eri-coder workflow.
Designed for brownfield development - modifying projects that already have code.

## Dynamic Context

**CLI analysis:**
!`python3 -m erirpg.commands.add_feature $ARGUMENTS --json 2>/dev/null || echo '{"error": "CLI failed"}'`

**Codebase mapping status:**
!`ls .planning/codebase/*.md 2>/dev/null | head -5 || echo "NOT_MAPPED"`

**Existing features:**
!`ls -d .planning/features/*/ 2>/dev/null | head -5 || echo "none"`

---

## Two Modes

### Standard Mode
Add new features to a codebase:
```bash
python3 -m erirpg.commands.add_feature "<feature-description>" --json
```

### Reference Mode (Feature Porting)
Port a feature from another program using behavior specs:
```bash
python3 -m erirpg.commands.add_feature <target> <feature> "<desc>" --reference <source>/<section> --json
```

Example:
```bash
python3 -m erirpg.commands.add_feature eritrainer sana "Sana model" --reference onetrainer/models/sana --json
```

---

## Prerequisites

1. Must be in a project root (package.json, Cargo.toml, pyproject.toml, go.mod)
2. Codebase should be mapped (auto-runs `/coder:map-codebase` if not)

## Output Structure

```
.planning/features/{feature-name}/
├── SPEC.md      # Feature specification
├── CONTEXT.md   # Discussion decisions (optional)
├── RESEARCH.md  # Technical research (if needed)
├── PLAN-*.md    # Implementation plans
└── SUMMARY.md   # Completion summary
```

---

## Workflow Steps

### Step 1: Validate Environment
Check project root and codebase mapping status.
See [reference.md](reference.md#step-1-validate-environment).

### Step 2: Load Codebase Context
Read STACK.md, ARCHITECTURE.md, CONVENTIONS.md from `.planning/codebase/`.
See [reference.md](reference.md#step-2-load-codebase-context).

### Step 3: Feature Discussion
Ask clarifying questions with AskUserQuestion.
See [reference.md](reference.md#step-3-feature-discussion).

### Step 4: Write Feature Spec
Create SPEC.md with problem, user stories, acceptance criteria.
See [reference.md](reference.md#step-4-write-feature-spec).

### Step 5: Context Discussion (Optional)
Discuss UI, API, or complex decisions if needed.
See [reference.md](reference.md#step-5-context-discussion).

### Step 6: Research Phase (If Needed)
Spawn `eri-phase-researcher` for non-trivial features.
See [reference.md](reference.md#step-6-research-phase).

### Step 7: Create Implementation Plan
Spawn `eri-planner` with full context.
See [reference.md](reference.md#step-7-create-implementation-plan).

### Step 8: Plan Verification
Spawn `eri-plan-checker` to verify coverage.
See [reference.md](reference.md#step-8-plan-verification).

### Step 9: Execute
Show summary, confirm with user, spawn `eri-executor` agents.
See [reference.md](reference.md#step-9-execute).

### Step 10: Verification
Verify criteria met, create SUMMARY.md, commit.
See [reference.md](reference.md#step-10-verification).

---

## Reference Mode Details

For porting features from another program, see [reference.md](reference.md#reference-porting-workflow).

Key insight: **Behavior specs are portable**, implementation details are not.

---

## Agent Strategy

| Task | Agent | Model |
|------|-------|-------|
| Codebase mapping | eri-codebase-mapper | sonnet |
| Research | eri-phase-researcher | sonnet |
| Planning | eri-planner | sonnet/opus |
| Execution | eri-executor | sonnet |
| Verification | eri-verifier | sonnet/haiku |

---

## Key Principles

1. ALWAYS respect existing codebase patterns
2. NEVER create new patterns when existing ones work
3. Read CONVENTIONS.md before writing ANY code
4. Integrate at the RIGHT place (check ARCHITECTURE.md)
5. Update existing tests if modifying tested code

---

## Completion

Use [templates/completion-box.md](templates/completion-box.md) format.
