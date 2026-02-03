# /coder:merge - Combine Multiple Plans

Merge multiple small plans into a single larger plan.

## CLI Integration

**First, call the CLI to analyze plans for merging:**
```bash
erirpg coder-merge .planning/phases/02-auth/02-01-PLAN.md .planning/phases/02-auth/02-02-PLAN.md
```

This returns JSON with:
- `plans`: Array of {path, tasks, lines} for each plan
- `total_tasks`: Combined task count
- `total_lines`: Combined line count
- `can_merge`: Boolean - whether merge is advisable
- `merge_warning`: Warning message if too complex

Use this analysis to determine if plans can be safely merged.

---

## Usage

```
/coder:merge 2-01 2-02             # Merge two plans
/coder:merge 2-01 2-02 2-03        # Merge three plans
/coder:merge --phase 2 --wave 1    # Merge all wave 1 plans in phase 2
/coder:merge --auto                # Auto-detect mergeable plans
```

## When to Use

- Multiple tiny plans that could run together
- Plans with overlapping files
- Reduce overhead of separate executions
- Consolidate after excessive splitting

## Execution Steps

### Step 1: Validate Merge

```python
def validate_merge(plans):
    # Check same phase
    phases = set(p.phase for p in plans)
    if len(phases) > 1:
        error("Cannot merge plans from different phases")

    # Check no circular dependencies
    for plan in plans:
        for dep in plan.depends_on:
            if dep in [p.id for p in plans]:
                error(f"Plan {plan.id} depends on {dep} - cannot merge")

    # Check compatible waves
    waves = [p.wave for p in plans]
    if max(waves) - min(waves) > 1:
        warn("Plans span multiple waves - merged plan will use latest wave")

    return True
```

### Step 2: Preview Merge

```markdown
## Merge Preview

**Plans to merge:** 02-01, 02-02
**Resulting plan:** 02-01 (combined)

### Original Plans
| Plan | Tasks | Files | Wave |
|------|-------|-------|------|
| 02-01 | 2 | 4 | 1 |
| 02-02 | 2 | 3 | 1 |

### Merged Result
| Metric | Value |
|--------|-------|
| Tasks | 4 |
| Files | 6 (1 overlap) |
| Wave | 1 |
| Est. Context | 35% |

### Task Order
1. (from 02-01) Create database schema
2. (from 02-01) Add migrations
3. (from 02-02) Create User model
4. (from 02-02) Add model tests

### File Overlap
- `prisma/schema.prisma` - modified by both plans
  → Tasks will be sequenced correctly

Proceed with merge? (yes/no)
```

### Step 3: Execute Merge

```python
def merge_plans(plans):
    # Sort by dependencies and wave
    sorted_plans = topological_sort(plans)

    merged = {
        "phase": plans[0].phase,
        "plan": plans[0].plan,  # Use first plan's number
        "type": "execute",
        "wave": max(p.wave for p in plans),
        "depends_on": collect_external_deps(plans),
        "files_modified": dedupe_files(plans),
        "merged_from": [p.id for p in plans],
        "must_haves": merge_must_haves(plans),
        "tasks": []
    }

    # Combine tasks in dependency order
    for plan in sorted_plans:
        for task in plan.tasks:
            # Add source annotation
            task.source_plan = plan.id
            merged["tasks"].append(task)

    return merged
```

### Step 4: Write Merged Plan

```markdown
---
phase: 02-auth
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: ["prisma/schema.prisma", "src/models/user.ts", ...]
merged_from: ["02-01", "02-02"]
must_haves:
  truths:
    - "Database schema created"
    - "User model functional"
  artifacts:
    - path: "prisma/schema.prisma"
    - path: "src/models/user.ts"
---

# Plan 02-01: Database & User Model (Merged)

<objective>
Combined plan merging database setup and user model creation.
Originally: Plans 02-01 and 02-02.
</objective>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
</context>

<tasks>

<!-- From Plan 02-01 -->
<task type="auto" source="02-01">
  <name>Task 1: Create database schema</name>
  ...
</task>

<task type="auto" source="02-01">
  <name>Task 2: Add migrations</name>
  ...
</task>

<!-- From Plan 02-02 -->
<task type="auto" source="02-02">
  <name>Task 3: Create User model</name>
  ...
</task>

<task type="auto" source="02-02">
  <name>Task 4: Add model tests</name>
  ...
</task>

</tasks>
```

### Step 5: Archive Original Plans

```bash
# Archive merged plans
mkdir -p .planning/phases/02-auth/archived/
mv .planning/phases/02-auth/02-02-PLAN.md \
   .planning/phases/02-auth/archived/02-02-PLAN.merged.md
```

### Step 6: Update State

```markdown
## STATE.md Update

### Merge History
- 2026-01-30 14:00: Merged Plans 02-01, 02-02 into 02-01
  Reason: Small related plans
  Original: 2 plans, 4 tasks
  Merged: 1 plan, 4 tasks
```

### Step 7: Report

```markdown
## Merge Complete

**Merged:** 02-01, 02-02 → 02-01
**Tasks:** 4 (from 2 + 2)
**Files:** 6 (was 7, 1 deduplicated)

### Archived
- `.planning/phases/02-auth/archived/02-02-PLAN.merged.md`

### Next Steps
Execute merged plan:
```
/coder:execute-phase 2
```
```

## Auto-Merge Detection

`/coder:merge --auto`:

```python
def find_mergeable(phase):
    candidates = []

    # Group by wave
    waves = group_by_wave(phase.plans)

    for wave, plans in waves.items():
        # Check if plans could merge
        for combo in combinations(plans, 2):
            if can_merge(combo[0], combo[1]):
                candidates.append({
                    "plans": combo,
                    "benefit": calculate_merge_benefit(combo),
                    "reason": why_mergeable(combo)
                })

    return sorted(candidates, key=lambda x: x["benefit"], reverse=True)
```

```markdown
## Auto-Merge Suggestions

Found 2 merge opportunities:

### 1. Plans 02-01 + 02-02 (Recommended)
**Benefit:** 25% context savings
**Reason:** Same wave, no dependencies, overlapping files
**Action:** `/coder:merge 02-01 02-02`

### 2. Plans 02-04 + 02-05
**Benefit:** 15% context savings
**Reason:** Sequential tasks, same domain
**Action:** `/coder:merge 02-04 02-05`

Apply suggestions? (1/2/both/none)
```

## Merge Constraints

### Cannot Merge If:
- Different phases
- Circular dependencies between plans
- Both have checkpoints (would complicate flow)
- Combined size > 50% context budget

### Warnings For:
- Different waves (will use max wave)
- Many overlapping files (potential conflicts)
- Large combined task count (>5)

## Context Budget Check

```python
def check_context_budget(merged):
    estimated_context = (
        len(merged.tasks) * 2000 +  # ~2K per task
        len(merged.files) * 500 +    # ~500 per file
        5000                          # Overhead
    )

    budget = 100000  # 100K tokens
    usage_percent = (estimated_context / budget) * 100

    if usage_percent > 50:
        warn(f"Merged plan may use {usage_percent:.0f}% context")
        return False

    return True
```

## Integration Points

- Reads: Multiple PLAN.md files
- Creates: Single merged PLAN.md
- Archives: Original plans to archived/
- Updates: STATE.md with merge history
- Recalculates: Plan numbering if needed
