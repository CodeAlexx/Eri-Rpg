# /coder:debug - Systematic Debugging

Investigate issues using scientific method with structured hypothesis testing.

## CLI Integration

**First, call the CLI to manage debug sessions:**
```bash
# Start new debug session
erirpg coder-debug "Login fails after password reset"

# List sessions
erirpg coder-debug --list

# Resume active session
erirpg coder-debug --resume

# Resolve session
erirpg coder-debug --resolve completed
```

This returns JSON with:
- For new: `initialized`, `path`, `slug`, `description`
- For list: `active` (current session), `resolved` (array of past sessions)
- For resume: `active`, `status`, `trigger`, `content`

Use this data to drive the investigation workflow below.

---

## Usage

```
/coder:debug "Login fails after password reset"
/coder:debug --resume              # Continue active session
/coder:debug --resolve {session}   # Mark session resolved
/coder:debug --list                # List debug sessions
```

## Philosophy

- **User = Reporter**, Claude = Investigator
- Don't ask user what's causing bug (investigate yourself)
- Hypothesis must be falsifiable
- One variable at a time
- Binary search to narrow scope

## Execution Steps

### Step 1: Initialize Debug Session

Create debug session:
```
.planning/debug/
├── active-session.md      # Current investigation
└── resolved/
    └── {timestamp}-{slug}.md
```

Session file structure:
```markdown
---
status: gathering | investigating | fixing | verifying | resolved
trigger: "[verbatim user input]"
created: YYYY-MM-DDTHH:MM:SSZ
updated: YYYY-MM-DDTHH:MM:SSZ
---

# Debug Session: {slug}

## Trigger
> {User's exact words}

## Current Focus
hypothesis: [current theory]
test: [how testing]
next_action: [immediate next step]

## Symptoms
expected: [what should happen]
actual: [what actually happens]
reproducible: [always | sometimes | once]

## Environment
- OS: [if relevant]
- Browser: [if relevant]
- Version: [app version]
- Last working: [commit or date if known]

## Eliminated
[Hypotheses proven wrong]

## Evidence
[What was checked and found]

## Resolution
root_cause: [when found]
fix: [when applied]
commit: [fix commit hash]
```

### Step 2: Gather Symptoms

Ask focused questions:
```markdown
## Symptom Gathering

I'll investigate this issue. First, a few clarifying questions:

1. **When did this start?**
   - After a specific change?
   - After an update?
   - Randomly?

2. **Reproducibility:**
   - Every time?
   - Sometimes (what conditions)?
   - Only once so far?

3. **Error messages:**
   - Any console errors?
   - Any error pages?
   - Network failures?

4. **What you've tried:**
   - Any workarounds attempted?
   - Did anything help temporarily?
```

### Step 3: Form Initial Hypothesis

Based on symptoms, create ranked hypotheses:

```markdown
## Initial Hypotheses

Based on symptoms, ranked by likelihood:

| # | Hypothesis | Likelihood | Test |
|---|------------|------------|------|
| 1 | Session token expired | High | Check token expiry logic |
| 2 | Password hash mismatch | Medium | Verify hash algorithm |
| 3 | Database connection issue | Low | Check connection pool |

**Starting with H1:** Session token expired

**Test:** Check `src/auth/session.ts` for token handling after password reset.
```

### Step 4: Investigation Loop

For each hypothesis:

```markdown
## Investigating: H1 - Session Token Expired

### Test
Checking if password reset invalidates session tokens...

### Evidence Gathered
```
$ grep -n "token" src/auth/session.ts
45: const token = generateToken(user.id)
78: if (isExpired(token)) return null
92: // TODO: Invalidate on password change?
```

### Finding
Line 92 shows TODO comment - tokens NOT invalidated on password reset!

### Conclusion
**H1 CONFIRMED** - Root cause found.
```

**If hypothesis fails:**
```markdown
### Test Result
Token is properly invalidated. Evidence:
- `invalidateUserSessions()` called in `resetPassword()`
- Tested: token rejected after reset

### Conclusion
**H1 ELIMINATED** - Moving to H2.
```

### Step 5: Apply Fix

Once root cause identified:

```markdown
## Root Cause Confirmed

**Issue:** Session tokens not invalidated after password reset
**Location:** `src/auth/password.ts:156`
**Impact:** Users can continue using old sessions after password change

## Proposed Fix

Add session invalidation to password reset flow:

```typescript
// In resetPassword()
await invalidateUserSessions(user.id);
```

**Risk:** Low - Isolated change, no side effects
**Testing:** Unit test + manual verification

Proceed with fix? (yes/no/alternative)
```

### Step 6: Implement and Verify

```markdown
## Fix Applied

**Commit:** `abc123`
**Message:** `fix(auth): invalidate sessions on password reset`

## Verification

1. [x] Unit test added: `password.test.ts`
2. [x] Manual test: Reset password, old session rejected
3. [x] No regression: Normal login still works

## Resolution

**Root Cause:** Session tokens not invalidated during password reset
**Fix:** Added `invalidateUserSessions()` call in `resetPassword()`
**Commit:** `abc123`
**Duration:** 25 minutes
```

### Step 7: Archive Session

Move to resolved:
```bash
mv .planning/debug/active-session.md \
   .planning/debug/resolved/{timestamp}-{slug}.md
```

Update STATE.md:
```markdown
### Recent Debug Sessions
- {date}: {issue} - RESOLVED ({root cause})
```

## Investigation Techniques

### Binary Search
```markdown
## Binary Search: Narrowing Failure Point

**Range:** Commits abc123 (working) to def456 (broken)
**Midpoint:** Testing commit 789xyz

Result: 789xyz works → Bug introduced after 789xyz
New range: 789xyz to def456

[Continue until single commit identified]
```

### Differential Debugging
```markdown
## Differential: Working vs Broken

**Working state:** Production (v1.2.3)
**Broken state:** Development (main)

**Differences found:**
1. New dependency: auth-lib@2.0 (was 1.8)
2. Changed: src/auth/session.ts (+45 lines)
3. Changed: src/api/login.ts (+12 lines)

**Focus:** auth-lib upgrade most likely culprit
```

### Minimal Reproduction
```markdown
## Creating Minimal Reproduction

**Steps to reproduce:**
1. Create new user
2. Login (get session)
3. Reset password
4. Try accessing protected route with old session
5. BUG: Access granted (should be denied)

**Minimal code:**
```typescript
const session = await login(user, password);
await resetPassword(user, newPassword);
const result = await accessProtected(session); // Should fail
assert(result.status === 401); // FAILS - returns 200
```
```

## Debug Modes

Spawn `eri-debugger` agent with mode:

| Mode | Purpose | Output |
|------|---------|--------|
| `find_root_cause_only` | Diagnose but don't fix | Root cause report |
| `find_and_fix` | Full cycle (default) | Fix + verification |

For UAT failures (from `/coder:verify-work`):
```
Spawn eri-debugger with mode=find_root_cause_only
```

## List Debug Sessions

`/coder:debug --list`:
```markdown
# Debug Sessions

## Active
- **login-fails-after-reset** (25 min, investigating)

## Resolved (last 10)
| Date | Issue | Root Cause | Duration |
|------|-------|------------|----------|
| 2026-01-30 | Login fails | Session not invalidated | 25 min |
| 2026-01-29 | API timeout | Connection pool exhausted | 45 min |
| 2026-01-28 | Missing data | Cache not cleared | 15 min |

**Total resolved:** 12 sessions
**Average duration:** 28 minutes
```

## Integration Points

- Creates: `.planning/debug/active-session.md`
- Archives: `.planning/debug/resolved/`
- Updates: STATE.md (recent sessions)
- Spawns: `eri-debugger` agent
- Workflow: `@~/.eri-rpg/workflows/diagnose-issues.md`
