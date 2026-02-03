# /coder:split - Break Plan Into Smaller Plans

Split a large or problematic plan into smaller, more manageable plans.

## CLI Integration

**First, call the CLI to analyze plan for splitting:**
```bash
erirpg coder-split .planning/phases/02-auth/02-03-PLAN.md
```

This returns JSON with:
- `path`: Plan file path
- `tasks`: Number of tasks in plan
- `lines`: Total lines
- `files_mentioned`: Number of files referenced
- `suggest_split`: Boolean - whether split is recommended
- `suggested_parts`: Recommended number of parts

Use this analysis to determine if and how to split the plan.

---

## Usage

```
/coder:split 2-03                  # Split plan interactively
/coder:split 2-03 --at-task 3      # Split after task 3
/coder:split 2-03 --by-file        # One plan per file group
/coder:split 2-03 --by-domain      # Split by technical domain
```

## When to Use

- Plan is too large (>3 tasks, >8 files)
- Execution failed mid-plan
- Want parallel execution of independent parts
- Context exhaustion during execution

## Execution Steps

### Step 1: Load Plan

```python
plan = load_plan("02-03")
tasks = plan.tasks
files = plan.files_modified
wave = plan.wave
```

### Step 2: Analyze Split Points

```markdown
## Plan Analysis: 02-03 (API Endpoints)

**Current State:**
- Tasks: 5
- Files: 12
- Complexity: High
- Recommendation: Split into 2-3 plans

### Tasks
| # | Name | Files | Domain | Dependencies |
|---|------|-------|--------|--------------|
| 1 | User model | 2 | database | none |
| 2 | User routes | 3 | api | task 1 |
| 3 | Validation | 2 | api | task 2 |
| 4 | Auth middleware | 2 | auth | task 1 |
| 5 | Integration | 3 | wiring | tasks 2,3,4 |

### Suggested Splits

**Option A: By Dependency**
- Plan 02-03a: Tasks 1-3 (User API)
- Plan 02-03b: Task 4 (Auth) - parallel with 02-03a
- Plan 02-03c: Task 5 (Integration) - after both

**Option B: After Task 3**
- Plan 02-03a: Tasks 1-3 (already complete)
- Plan 02-03b: Tasks 4-5 (remaining)

**Option C: By Domain**
- Plan 02-03a: Database tasks
- Plan 02-03b: API tasks
- Plan 02-03c: Integration tasks

Select option (A/B/C) or specify custom:
```

### Step 3: Execute Split

```python
def split_plan(original, split_points):
    new_plans = []

    for i, (start, end) in enumerate(split_points):
        new_plan = {
            "phase": original.phase,
            "plan": f"{original.plan}{chr(ord('a') + i)}",  # 02-03a, 02-03b
            "type": "execute",
            "wave": calculate_wave(start, end, original),
            "depends_on": calculate_dependencies(i, new_plans),
            "tasks": original.tasks[start:end],
            "files_modified": get_files_for_tasks(original.tasks[start:end]),
            "must_haves": extract_must_haves(original, start, end)
        }
        new_plans.append(new_plan)

    return new_plans
```

### Step 4: Write New Plans

Create new PLAN.md files:

**02-03a-PLAN.md:**
```markdown
---
phase: 02-auth
plan: 03a
type: execute
wave: 2
depends_on: ["02-02"]
files_modified: ["src/models/user.ts", "src/api/users.ts", "src/api/validation.ts"]
split_from: "02-03"
---

# Plan 02-03a: User API (Split 1/2)

<objective>
Create user model and API endpoints with validation.
Split from original Plan 02-03 for better context management.
</objective>

<tasks>
[Tasks 1-3 from original]
</tasks>
```

**02-03b-PLAN.md:**
```markdown
---
phase: 02-auth
plan: 03b
type: execute
wave: 3
depends_on: ["02-03a"]
files_modified: ["src/middleware/auth.ts", "src/routes/index.ts"]
split_from: "02-03"
---

# Plan 02-03b: Auth & Integration (Split 2/2)

<objective>
Add auth middleware and wire up user routes.
Continues from Plan 02-03a.
</objective>

<tasks>
[Tasks 4-5 from original]
</tasks>
```

### Step 5: Archive Original

```bash
# Move original to archived
mv .planning/phases/02-auth/02-03-PLAN.md \
   .planning/phases/02-auth/archived/02-03-PLAN.original.md
```

### Step 6: Update State

```markdown
## STATE.md Update

### Split History
- 2026-01-30 14:00: Split Plan 02-03 into 02-03a, 02-03b
  Reason: Context exhaustion at task 3
  Original tasks: 5
  New plans: 2 (3 tasks, 2 tasks)
```

### Step 7: Report

```markdown
## Split Complete

**Original:** Plan 02-03 (5 tasks, 12 files)
**New Plans:**

| Plan | Tasks | Files | Wave | Status |
|------|-------|-------|------|--------|
| 02-03a | 3 | 7 | 2 | Ready |
| 02-03b | 2 | 5 | 3 | Waiting on 02-03a |

### Next Steps
1. Execute split plans: `/coder:execute-phase 2`
2. Or execute individually:
   - `/coder:execute-phase 2 --plan 02-03a`
   - `/coder:execute-phase 2 --plan 02-03b`

Original plan archived to:
`.planning/phases/02-auth/archived/02-03-PLAN.original.md`
```

## Split Strategies

### --at-task N
Split after task N:
- Plan A: Tasks 1 to N
- Plan B: Tasks N+1 to end

### --by-file
Group tasks by file clusters:
- Analyze file overlap between tasks
- Group tasks that share files
- Create plan per cluster

### --by-domain
Split by technical domain:
- Database tasks
- API tasks
- UI tasks
- Test tasks
- Integration tasks

### --preserve-completed
When splitting mid-execution:
- Keep completed tasks in first plan
- Mark first plan as complete
- Move remaining to new plan

## Mid-Execution Split

When a plan fails during execution:

```python
if execution_failed:
    completed_tasks = get_completed_tasks()
    remaining_tasks = get_remaining_tasks()

    # Create summary for completed work
    create_partial_summary(completed_tasks)

    # Split remaining into new plan
    new_plan = create_plan_from_tasks(remaining_tasks)

    # Update state
    update_state(completed=completed_tasks, pending=new_plan)
```

## Wave Recalculation

After split, recalculate waves:
```python
def recalculate_waves(phase_plans):
    for plan in phase_plans:
        if not plan.depends_on:
            plan.wave = 1
        else:
            max_dep_wave = max(
                get_plan(dep).wave for dep in plan.depends_on
            )
            plan.wave = max_dep_wave + 1
```

## Integration Points

- Reads: Original PLAN.md
- Creates: Split PLAN.md files (02-03a, 02-03b, etc.)
- Archives: Original plan to archived/
- Updates: STATE.md with split history
- Recalculates: Wave assignments
