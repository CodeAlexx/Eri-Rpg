# /coder:diff - Show Changes Since Checkpoint

Display what changed since the last checkpoint, phase start, or specified point.

## CLI Integration

**First, call the CLI to get diff statistics:**
```bash
# Default (since last commit)
erirpg coder-diff

# Since phase start
erirpg coder-diff --phase 2

# Since specific commit/time
erirpg coder-diff --since "HEAD~5"
erirpg coder-diff --since "1 hour ago"

# Output modes
erirpg coder-diff --files    # File list only
erirpg coder-diff --stat     # Statistics only
```

This returns JSON with:
- `reference`: The reference point used
- `commits`: Array of commit hashes/messages
- `commit_count`: Number of commits
- `files`: Array of {file, status} (created/modified/deleted)
- `file_count`: Number of files changed
- `insertions`, `deletions`, `net_change`: Line statistics
- `stat_output`: Full git stat output

Use this data to render the diff display below.

---

## Usage

```
/coder:diff                        # Since last checkpoint
/coder:diff --phase 2              # Since phase 2 started
/coder:diff --plan 2-03            # Changes in specific plan
/coder:diff --since <commit>       # Since specific commit
/coder:diff --files                # File list only
/coder:diff --stat                 # Statistics only
```

## Execution Steps

### Step 1: Determine Reference Point

```python
if args.since:
    ref = args.since
elif args.plan:
    ref = find_plan_start_commit(args.plan)
elif args.phase:
    ref = find_phase_start_commit(args.phase)
else:
    # Last checkpoint or phase start
    ref = find_last_checkpoint() or find_current_phase_start()
```

### Step 2: Gather Changes

```bash
# Get commit list
git log --oneline {ref}..HEAD

# Get file changes
git diff --stat {ref}..HEAD

# Get detailed diff
git diff {ref}..HEAD
```

### Step 3: Present Summary

```markdown
## Changes Since: Phase 2 Start

**Reference:** `abc123` (2026-01-30 10:00)
**Current:** `xyz789` (2026-01-30 14:30)
**Duration:** 4h 30m

### Commits (12)
| Hash | Type | Message | Files |
|------|------|---------|-------|
| xyz789 | feat | Add user validation | 2 |
| uvw456 | test | User endpoint tests | 1 |
| rst123 | feat | Create user endpoints | 3 |
| ... | ... | ... | ... |

### Statistics
```
 15 files changed, 847 insertions(+), 23 deletions(-)
```

### Files Changed
| File | Status | +/- |
|------|--------|-----|
| `src/api/users.ts` | Created | +120 |
| `src/api/validation.ts` | Created | +45 |
| `src/middleware/auth.ts` | Modified | +30/-5 |
| `tests/users.test.ts` | Created | +80 |
| `src/routes/index.ts` | Modified | +12/-2 |

### By Category
| Category | Files | Lines |
|----------|-------|-------|
| Source | 8 | +450 |
| Tests | 4 | +280 |
| Config | 2 | +95 |
| Docs | 1 | +22 |
```

### Step 4: Detailed View (if requested)

```markdown
## Detailed Changes

### src/api/users.ts (Created)
```typescript
// Full file content or key sections
export async function createUser(data: UserInput) {
  // Validate input
  validateUserInput(data);

  // Hash password
  const hashedPassword = await hash(data.password, 12);

  // Create in database
  return db.user.create({
    email: data.email,
    password: hashedPassword
  });
}
```

### src/middleware/auth.ts (Modified)
```diff
@@ -45,6 +45,12 @@ export function authMiddleware(req, res, next) {
+  // Added: Token refresh logic
+  if (isTokenExpiringSoon(token)) {
+    const newToken = refreshToken(token);
+    res.setHeader('X-New-Token', newToken);
+  }
+
   next();
 }
```
```

## Output Modes

### --files (File List Only)
```
src/api/users.ts (new)
src/api/validation.ts (new)
src/middleware/auth.ts (modified)
tests/users.test.ts (new)
src/routes/index.ts (modified)
```

### --stat (Statistics Only)
```
Phase 2 Progress:
  Commits: 12
  Files changed: 15
  Lines added: 847
  Lines removed: 23
  Net change: +824 lines

By plan:
  02-01: 4 commits, +250 lines
  02-02: 5 commits, +380 lines
  02-03: 3 commits, +194 lines
```

### Default (Summary + Key Changes)
Full summary with commit table, file list, and statistics.

## Comparison Modes

### Phase vs Phase
```
/coder:diff --compare-phases 1 2
```
```markdown
## Phase Comparison: 1 vs 2

| Metric | Phase 1 | Phase 2 |
|--------|---------|---------|
| Commits | 8 | 12 |
| Files | 10 | 15 |
| Lines added | 520 | 847 |
| Duration | 2h | 4.5h |
| Plans | 2 | 3 |
```

### Plan vs Plan
```
/coder:diff --compare-plans 2-01 2-02
```

## Integration with Workflow

### Before Verify
```
/coder:diff --phase 2
# See all changes before running /coder:verify-work 2
```

### Before Rollback
```
/coder:diff --plan 2-03
# Review what would be rolled back
/coder:rollback --plan 2-03
```

### Debug Context
```
/coder:diff --since "1 hour ago"
# What changed in the last hour?
```

## Git Integration

Uses git commands internally:
```bash
# Log with stats
git log --oneline --stat {ref}..HEAD

# Diff summary
git diff --stat {ref}..HEAD

# Full diff
git diff {ref}..HEAD

# File status
git diff --name-status {ref}..HEAD
```

## Time-Based References

```
/coder:diff --since "1 hour ago"
/coder:diff --since "yesterday"
/coder:diff --since "2026-01-30"
```

Uses `git log --since` for time parsing.

## Output Formats

### Terminal (Default)
Colored, formatted for CLI viewing.

### Markdown
```
/coder:diff --format md > changes.md
```

### JSON
```
/coder:diff --format json
```
```json
{
  "reference": "abc123",
  "current": "xyz789",
  "commits": 12,
  "files": {
    "created": ["src/api/users.ts"],
    "modified": ["src/routes/index.ts"],
    "deleted": []
  },
  "stats": {
    "insertions": 847,
    "deletions": 23
  }
}
```
