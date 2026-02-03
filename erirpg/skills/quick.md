# /coder:quick - Ad-Hoc Task with Guarantees

Execute a quick task outside the phase structure while maintaining ERI guarantees (planning, verification, atomic commits).

## CLI Integration

**First, call the CLI to manage quick tasks:**
```bash
# Create new quick task
erirpg coder-quick "Fix the login button styling" [--scope src/components/]

# List quick tasks
erirpg coder-quick --list

# Resume a quick task
erirpg coder-quick --resume 003
```

This returns JSON with:
- For new task: `id`, `slug`, `dir`, `description`, `scope`, `status`
- For list: `tasks` array with id, status, description, commit
- For resume: `resume: true`, `task` object

Use this data to drive the workflow below.

---

## Usage

```
/coder:quick "Fix the login button styling"
/coder:quick "Add error handling to API calls" --scope src/api/
/coder:quick --list                    # List previous quick tasks
/coder:quick --resume 003              # Resume incomplete quick task
```

## When to Use

- Bug fixes that don't fit current phase
- Small improvements noticed during development
- Urgent hotfixes
- Experiments or spikes
- Tasks < 30 minutes

**Not for:**
- Features requiring multiple files and tests (use phases)
- Architectural changes (use proper planning)
- Tasks requiring user decisions (use checkpoints)

## Execution Steps

### Step 1: Initialize Quick Task

Create quick task directory:
```
.planning/quick/
└── {NNN}-{slug}/
    ├── PLAN.md
    └── SUMMARY.md (after completion)
```

Generate task ID:
```python
existing = glob(".planning/quick/*/")
next_id = max([int(d.split("-")[0]) for d in existing], default=0) + 1
slug = slugify(task_description)[:30]
task_dir = f".planning/quick/{next_id:03d}-{slug}/"
```

### Step 2: Quick Planning

Spawn lightweight planning (no full planner agent):

```markdown
---
type: quick
id: {NNN}
created: YYYY-MM-DDTHH:MM:SSZ
scope: [file patterns or "auto"]
status: planned
---

# Quick Task: {description}

## Objective
{User's description expanded}

## Files to Modify
- `{detected or specified files}`

## Approach
1. {Step 1}
2. {Step 2}
3. {Verification step}

## Verification
- [ ] {How to verify completion}

## Rollback
If issues arise: `git revert HEAD`
```

**Auto-scope detection:**
- Parse task description for file references
- Check recent git history for related files
- Limit to 5 files max for quick tasks

### Step 3: User Confirmation

```markdown
## Quick Task Plan

**Task:** {description}
**Files:** {count} files
**Estimated:** {simple | moderate}

### Will Modify
- `src/components/Button.tsx` - Style fixes
- `src/styles/buttons.css` - Color updates

### Approach
1. Update button padding and colors
2. Fix hover state
3. Verify in browser

Proceed? (yes/no/edit)
```

### Step 4: Execute Task

Apply same guarantees as phase execution:

1. **Pre-flight check:**
   ```bash
   git status  # Must be clean
   ```

2. **Execute changes:**
   - Make modifications
   - Run linting if configured
   - Run affected tests

3. **Atomic commit:**
   ```bash
   git add {files}
   git commit -m "fix({scope}): {description}

   Quick task #{NNN}

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

4. **Verify:**
   - Check task verification criteria
   - Run quick smoke test if applicable

### Step 5: Create Summary

Write `.planning/quick/{NNN}-{slug}/SUMMARY.md`:

```markdown
---
id: {NNN}
status: complete
duration: {minutes}
commit: {hash}
completed: YYYY-MM-DDTHH:MM:SSZ
---

# Quick Task #{NNN}: {description}

**One-liner:** {What was actually done}

## Changes Made
| File | Change |
|------|--------|
| `src/components/Button.tsx` | Fixed padding, updated colors |

## Commit
`{hash}` - {commit message first line}

## Verification
- [x] Button displays correctly
- [x] Hover state works

## Notes
{Any observations or follow-up needed}
```

### Step 6: Update State

Add to STATE.md Accumulated Context:
```markdown
### Recent Quick Tasks
- #{NNN}: {description} ({date})
```

## Quick Task Limits

Enforce quick task constraints:

| Constraint | Limit | Action if Exceeded |
|------------|-------|-------------------|
| Files | 5 max | Suggest phase instead |
| Duration | 30 min | Warn, offer to convert to phase |
| Complexity | Simple | Suggest proper planning |
| Dependencies | None | Must not require other tasks |

**Escalation prompt:**
```markdown
This task seems too complex for /coder:quick:
- Touches {N} files (limit: 5)
- Requires {dependency}
- May need testing infrastructure

Recommend converting to proper phase:
`/coder:add-phase "Hotfix: {description}"`

Continue as quick task anyway? (yes/no)
```

## List Quick Tasks

`/coder:quick --list`:
```markdown
# Quick Tasks

| ID | Description | Status | Date | Commit |
|----|-------------|--------|------|--------|
| 003 | Fix login button | ✅ Complete | 2026-01-30 | abc123 |
| 002 | Add loading spinner | ✅ Complete | 2026-01-29 | def456 |
| 001 | Update README | ✅ Complete | 2026-01-28 | 789abc |

**In Progress:** None

**Total:** 3 quick tasks completed
```

## Resume Incomplete

`/coder:quick --resume 003`:
```markdown
## Resuming Quick Task #003

**Task:** Fix login button styling
**Status:** In progress (started 10 min ago)
**Files modified:** 1 of 2

### Completed
- [x] Updated Button.tsx

### Remaining
- [ ] Update buttons.css
- [ ] Verify in browser

Continuing execution...
```

## Integration Points

- Creates: `.planning/quick/{NNN}-{slug}/`
- Updates: STATE.md (accumulated context)
- Commits: Atomic with quick task reference
- Rollback: Standard git revert
