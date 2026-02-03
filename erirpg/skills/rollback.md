# /coder:rollback - Undo Execution

Undo the last phase or plan execution using git history.

## CLI Integration

**First, call the CLI to preview rollback:**
```bash
# Preview rollback of last plan
erirpg coder-rollback

# Preview specific plan rollback
erirpg coder-rollback --plan 2-03

# Preview phase rollback
erirpg coder-rollback --phase 2

# Preview to specific commit
erirpg coder-rollback --to abc123

# Dry run (always preview)
erirpg coder-rollback --dry-run --plan 2-03
```

This returns JSON with:
- `scope`: What's being rolled back (plan, phase, commit, last_plan)
- `identifier`: The plan/phase/commit being targeted
- `commits`: Array of commits that would be reverted
- `commit_count`: Number of commits
- `files_affected`: Files that would change
- `file_count`: Number of files
- `git_status`: Current git state (check for dirty)

Use this data to show preview and execute rollback.

---

## Usage

```
/coder:rollback                    # Undo last plan
/coder:rollback --plan 2-03        # Undo specific plan
/coder:rollback --phase 2          # Undo entire phase
/coder:rollback --to <commit>      # Rollback to specific commit
/coder:rollback --dry-run          # Preview without executing
```

## Execution Steps

### Step 1: Analyze Rollback Scope

Determine what to undo:

```python
if args.phase:
    # Find all commits in phase
    scope = find_phase_commits(args.phase)
elif args.plan:
    # Find commits for specific plan
    scope = find_plan_commits(args.plan)
elif args.to:
    # Everything after specified commit
    scope = commits_after(args.to)
else:
    # Default: last plan executed
    scope = find_last_plan_commits()
```

### Step 2: Preview Changes

```markdown
## Rollback Preview

**Scope:** Phase 2, Plan 03 (API Endpoints)
**Commits to undo:** 3
**Files affected:** 5

### Commits
| Hash | Message | Files |
|------|---------|-------|
| abc123 | feat(02-03): Create user endpoints | 2 |
| def456 | feat(02-03): Add validation | 2 |
| 789abc | test(02-03): User endpoint tests | 1 |

### Files to Restore
| File | Action | Current → Previous |
|------|--------|-------------------|
| `src/api/users.ts` | Restore | 120 lines → 0 (delete) |
| `src/api/validation.ts` | Restore | 45 lines → 0 (delete) |
| `tests/users.test.ts` | Restore | 80 lines → 0 (delete) |
| `src/routes/index.ts` | Modify | Remove user routes |

### Artifacts to Update
- `.planning/phases/02-auth/02-03-SUMMARY.md` → Delete
- `.planning/STATE.md` → Update position

Proceed with rollback? (yes/no)
```

### Step 3: Execute Rollback

**Option A: Git Revert (Safe)**
```bash
# Create revert commits (preserves history)
git revert --no-commit abc123 def456 789abc
git commit -m "revert(02-03): Rollback API Endpoints plan

Undoing Plan 02-03 due to [reason]

Reverted commits:
- abc123: feat(02-03): Create user endpoints
- def456: feat(02-03): Add validation
- 789abc: test(02-03): User endpoint tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Option B: Git Reset (Destructive)**
```bash
# Only if user explicitly requests --hard
git reset --hard <commit-before-plan>
# Warning: This rewrites history
```

### Step 4: Update Artifacts

1. **Delete SUMMARY.md** for rolled-back plan:
```bash
rm .planning/phases/02-auth/02-03-SUMMARY.md
```

2. **Update STATE.md**:
```markdown
## Current Position
Phase: [2] of [5]
Plan: [2] of [4]  # Back to before 02-03
Status: Ready to plan

## Rollback History
- 2026-01-30 14:00: Rolled back Plan 02-03 (API Endpoints)
  Reason: User requested
  Commits reverted: 3
```

3. **Update ROADMAP.md** if phase rollback:
```markdown
## Phase 2: Authentication
Status: In Progress  # Was: Complete
```

### Step 5: Report

```markdown
## Rollback Complete

**Reverted:** Plan 02-03 (API Endpoints)
**Commits:** 3 reverted
**Files:** 5 restored to previous state

### Revert Commit
`xyz789` - revert(02-03): Rollback API Endpoints plan

### Current State
- Phase 2, Plan 2 of 4
- Ready to re-plan or continue

### Next Steps
1. Re-plan: `/coder:plan-phase 2` (will regenerate 02-03)
2. Skip plan: `/coder:execute-phase 2` (continues from 02-04)
3. Different approach: `/coder:replay 2 --plan 3`
```

## Rollback Types

### Plan Rollback (Default)
- Reverts commits from single plan
- Deletes plan's SUMMARY.md
- Keeps plan's PLAN.md for re-execution

### Phase Rollback
- Reverts all commits from all plans in phase
- Deletes all SUMMARY.md files
- Resets phase status in ROADMAP.md
- Updates STATE.md position

### Checkpoint Rollback
- Returns to state at last checkpoint
- Uses commit tagged with checkpoint ID
- Preserves work before checkpoint

## Safety Features

### Pre-Rollback Checks
```python
# Ensure clean working directory
if git_dirty():
    error("Uncommitted changes. Commit or stash first.")

# Check for pushed commits
if commits_pushed(scope):
    warn("Some commits already pushed. Use --force to revert anyway.")

# Verify rollback is possible
if merge_conflicts_likely(scope):
    warn("Rollback may cause conflicts. Review carefully.")
```

### Rollback Protection
```python
# Create backup branch before destructive operations
git branch f"backup-before-rollback-{timestamp}"

# Tag rollback point
git tag f"rollback-{timestamp}" -m "Rollback to this point"
```

## Dry Run Mode

`/coder:rollback --dry-run`:
```markdown
## Rollback Simulation (Dry Run)

**No changes will be made.**

Would revert:
- 3 commits
- 5 files

Would update:
- STATE.md
- 1 SUMMARY.md deleted

Run without --dry-run to execute.
```

## Integration Points

- Reads: Git history, STATE.md, ROADMAP.md
- Modifies: Git history (revert commits)
- Deletes: SUMMARY.md files for rolled-back work
- Updates: STATE.md, ROADMAP.md
- Creates: Backup branch, rollback tag
