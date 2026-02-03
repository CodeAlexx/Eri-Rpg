# /coder:list-phase-assumptions - See Claude's Approach

Preview how Claude will approach a phase before planning. Reveals assumptions, anticipated challenges, and proposed patterns.

## CLI Integration

**First, call the CLI to get phase info:**
```bash
erirpg coder-phase-assumptions 3
```

This returns JSON with:
- `phase`: Phase number
- `content`: Full phase section from ROADMAP.md
- `goal`: Extracted goal
- `success_criteria`: Extracted success criteria

Use this data to present assumptions and planning approach.

---

## Usage

```
/coder:list-phase-assumptions 3
/coder:list-phase-assumptions 3 --detailed
```

## Purpose

Before `/coder:plan-phase`, understand:
- What Claude assumes about the phase
- What patterns Claude will use
- What challenges Claude anticipates
- What decisions Claude will make

This allows course correction BEFORE plans are created.

## Execution Steps

### Step 1: Load Phase Context

Read phase definition from ROADMAP.md:
```markdown
## Phase 3: User Authentication

**Goal:** Users can create accounts and log in securely

**Success Criteria:**
- Users can register with email/password
- Users can log in and receive session token
- Protected routes reject unauthenticated requests
- Passwords are securely hashed

**Requirements Mapped:**
- REQ-005: User registration
- REQ-006: User login
- REQ-007: Session management
```

### Step 2: Analyze Phase

Consider:
- Phase type (UI, API, data, content, integration)
- Technical domain (auth, payments, search, etc.)
- Dependencies on prior phases
- Files likely to be created/modified
- Patterns typically used
- Common pitfalls in this domain

### Step 3: Present Assumptions

```markdown
# Phase 3: User Authentication - Assumptions Preview

## Phase Classification

**Type:** Backend API + Database
**Domain:** Authentication/Security
**Complexity:** Medium-High
**Estimated Plans:** 3-4

## Technical Assumptions

### Stack Decisions
| Component | Assumed | Reasoning |
|-----------|---------|-----------|
| Password hashing | bcrypt | Industry standard, secure |
| Session storage | JWT in httpOnly cookie | Stateless, secure |
| Database | [from PROJECT.md] | Project requirement |
| Validation | zod | Type-safe validation |

### Architecture Assumptions
1. **User model** will be created in `src/models/user.ts`
2. **Auth routes** at `/api/auth/*` (register, login, logout)
3. **Middleware** for protected routes in `src/middleware/auth.ts`
4. **Session tokens** as JWT with 7-day expiry

### Pattern Assumptions
- Repository pattern for database access
- Express/Fastify middleware for auth checks
- Separate service layer for business logic
- Input validation at route level

## Anticipated Challenges

| Challenge | Approach |
|-----------|----------|
| Secure password storage | bcrypt with salt rounds 12 |
| Session invalidation | Token blacklist or short expiry |
| Rate limiting | Not in scope (Phase 5) |
| OAuth integration | Not in scope (future) |

## Gray Areas (May Ask About)

These aspects could go multiple ways:

1. **Session Duration**
   - Option A: 7 days (convenience)
   - Option B: 24 hours (security)
   - Option C: Sliding expiry (balance)

2. **Password Requirements**
   - Option A: Minimum 8 chars (simple)
   - Option B: Complexity rules (strict)
   - Option C: Passphrase-friendly (modern)

3. **Username vs Email**
   - Option A: Email only (simple)
   - Option B: Username + email (flexible)

## Dependency Analysis

### Requires from Prior Phases
- Database connection (Phase 1)
- API framework setup (Phase 1)
- Error handling patterns (Phase 2)

### Provides for Later Phases
- Authenticated user context
- Protected route middleware
- User model for associations

## Proposed Plan Structure

| Plan | Focus | Tasks |
|------|-------|-------|
| 3-01 | Database + User Model | Schema, migrations, model |
| 3-02 | Auth API | Register, login, logout routes |
| 3-03 | Session Middleware | JWT handling, protected routes |
| 3-04 | Integration | Wire auth to existing routes |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Security vulnerabilities | High | Follow OWASP guidelines |
| Session edge cases | Medium | Comprehensive test coverage |
| Breaking existing routes | Medium | Integration phase last |

---

## Your Input Needed

To refine these assumptions before planning:

1. **Confirm or change** any technical assumptions above
2. **Decide gray areas** or defer to Claude's judgment
3. **Add constraints** not captured in PROJECT.md
4. **Flag concerns** about proposed approach

**Ready to plan?** Run `/coder:plan-phase 3`
**Need discussion?** Run `/coder:discuss-phase 3`
```

### Step 4: Detailed Mode (--detailed)

Additional sections for `--detailed`:

```markdown
## File Inventory (Predicted)

### New Files
| File | Purpose | Lines (est) |
|------|---------|-------------|
| `src/models/user.ts` | User entity | ~50 |
| `src/routes/auth.ts` | Auth endpoints | ~120 |
| `src/services/auth.ts` | Auth logic | ~80 |
| `src/middleware/auth.ts` | JWT middleware | ~40 |
| `src/utils/password.ts` | Hashing utils | ~30 |
| `tests/auth.test.ts` | Auth tests | ~150 |

### Modified Files
| File | Changes |
|------|---------|
| `src/routes/index.ts` | Mount auth routes |
| `src/types/index.ts` | Add User types |
| `prisma/schema.prisma` | Add User model |

## Test Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Password hashing, token generation |
| Integration | Auth flow end-to-end |
| Security | SQL injection, XSS, timing attacks |

## External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| bcrypt | ^5.x | Password hashing |
| jsonwebtoken | ^9.x | JWT handling |
| zod | ^3.x | Input validation |

## Context7 Research Planned

Will consult documentation for:
- bcrypt best practices
- JWT security guidelines
- Express middleware patterns
- Prisma user model patterns

## Similar Patterns in Codebase

[If brownfield, reference existing patterns]
- Error handling: follows `src/utils/errors.ts` pattern
- Middleware: matches existing `src/middleware/` structure
```

## When to Use

| Scenario | Recommended Action |
|----------|-------------------|
| First time with this domain | Run assumptions first |
| Standard patterns | Skip, go to plan-phase |
| Complex phase | Run assumptions + discuss-phase |
| Team review needed | Share assumptions output |
| Concerns about approach | Run before any planning |

## Comparison with discuss-phase

| Command | Purpose | Output |
|---------|---------|--------|
| `list-phase-assumptions` | See Claude's planned approach | Read-only preview |
| `discuss-phase` | Provide user preferences | Creates CONTEXT.md |

Typical flow:
```
list-phase-assumptions 3  → See Claude's thinking
discuss-phase 3           → Override with your preferences
plan-phase 3              → Plans incorporate both
```
