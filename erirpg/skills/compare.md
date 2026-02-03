# /coder:compare - Compare Approaches Before Committing

Evaluate two or more approaches side-by-side before choosing one.

## CLI Integration

**For git branch comparison, call the CLI:**
```bash
# Compare branch with current HEAD
erirpg coder-compare feature-branch

# Compare two branches
erirpg coder-compare feature-a feature-b
```

This returns JSON with:
- `branch1`, `branch2`: Branches being compared
- `commits_ahead`: Commits branch2 has over branch1
- `commits_behind`: Commits branch1 has over branch2
- `files_changed`: Array of changed file names
- `stat`: Full git stat output

For conceptual comparisons (not branches), follow the workflow below.

---

## Usage

```
/coder:compare "JWT auth" "Session auth"           # Compare two approaches
/coder:compare --file approach-a.md approach-b.md  # Compare from files
/coder:compare --branch feature-a feature-b        # Compare git branches
/coder:compare --worktree                          # Use git worktrees
```

## When to Use

- Major architectural decision
- Multiple valid implementation paths
- Evaluating libraries or frameworks
- Before committing to a direction

## Execution Steps

### Step 1: Define Approaches

```markdown
## Comparison: Auth Strategy

**Context:** Phase 2 requires user authentication
**Decision Point:** Which auth mechanism to use?

### Approach A: JWT Tokens
- Stateless authentication
- Token stored in httpOnly cookie
- 7-day expiry with refresh

### Approach B: Server-Side Sessions
- Session stored in Redis
- Session ID in cookie
- Instant invalidation

Analyzing both approaches...
```

### Step 2: Research Each Approach

Spawn parallel research agents:

```python
approaches = []

for approach in [approach_a, approach_b]:
    research = Task(
        prompt=f"""
Research this implementation approach:
{approach.description}

Evaluate:
1. Implementation complexity
2. Security implications
3. Performance characteristics
4. Scalability
5. Maintenance burden
6. Common pitfalls

Project context:
{project_summary}
        """,
        subagent_type="eri-project-researcher"
    )
    approaches.append(research)

results = await gather(approaches)
```

### Step 3: Generate Comparison Matrix

```markdown
## Comparison Matrix

| Criterion | JWT Tokens | Session Auth | Winner |
|-----------|------------|--------------|--------|
| **Complexity** | Medium | Medium-High | JWT |
| **Security** | Good (with refresh) | Excellent | Session |
| **Performance** | Excellent (no DB) | Good | JWT |
| **Scalability** | Excellent | Good (Redis) | JWT |
| **Invalidation** | Hard | Instant | Session |
| **Maintenance** | Low | Medium | JWT |

### Weighted Score
| Criterion | Weight | JWT | Session |
|-----------|--------|-----|---------|
| Security | 30% | 7 | 9 |
| Simplicity | 25% | 8 | 6 |
| Performance | 20% | 9 | 7 |
| Scalability | 15% | 9 | 7 |
| Flexibility | 10% | 6 | 8 |
| **Total** | 100% | **7.7** | **7.4** |
```

### Step 4: Prototype Each (Optional)

If `--prototype` specified:

```python
for approach in approaches:
    # Create worktree for approach
    worktree = create_worktree(f"compare-{approach.name}")

    # Generate minimal implementation
    prototype = generate_prototype(approach)

    # Test prototype
    test_results = test_prototype(prototype)

    approach.prototype = {
        "worktree": worktree,
        "files": prototype.files,
        "test_results": test_results,
        "lines_of_code": count_lines(prototype)
    }
```

### Step 5: Present Detailed Analysis

```markdown
## Detailed Analysis

### Approach A: JWT Tokens

**Pros:**
- No server-side storage needed
- Scales horizontally with no shared state
- Works well with microservices
- Lower infrastructure cost

**Cons:**
- Token revocation is complex
- Token size can grow (claims)
- Refresh token rotation needed
- XSS risk if stored in localStorage

**Implementation Estimate:**
- Files: 4
- Lines: ~200
- Complexity: Medium
- Dependencies: jsonwebtoken

**Code Sketch:**
```typescript
// middleware/auth.ts
export function authMiddleware(req, res, next) {
  const token = req.cookies.token;
  try {
    const payload = jwt.verify(token, SECRET);
    req.user = payload;
    next();
  } catch (e) {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

---

### Approach B: Server-Side Sessions

**Pros:**
- Instant session invalidation
- Smaller cookie size
- Server controls all state
- Easier to implement audit logging

**Cons:**
- Requires Redis/database
- Session lookup on every request
- Horizontal scaling needs shared store
- More infrastructure

**Implementation Estimate:**
- Files: 5
- Lines: ~250
- Complexity: Medium-High
- Dependencies: express-session, redis

**Code Sketch:**
```typescript
// middleware/session.ts
app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { secure: true, httpOnly: true }
}));
```
```

### Step 6: Recommendation

```markdown
## Recommendation

**Recommended:** Approach A (JWT Tokens)

### Rationale
1. **Project fit:** This is a simple app without complex session requirements
2. **Simplicity:** JWT requires less infrastructure
3. **Performance:** No database lookup per request
4. **Scale:** Stateless auth scales better

### Mitigations for JWT Cons
- Use short expiry (15 min) + refresh tokens
- Store in httpOnly cookie (not localStorage)
- Implement token blacklist for logout

### Decision Required
- Accept recommendation: `approve jwt`
- Choose alternative: `approve session`
- Need more info: `more [topic]`
- Prototype both: `prototype`
```

### Step 7: Apply Decision

On user approval:

```python
if user_response == "approve jwt":
    # Record decision
    record_decision(
        decision="Auth strategy",
        choice="JWT Tokens",
        rationale=recommendation.rationale,
        alternatives_considered=["Server-side sessions"]
    )

    # Update phase context
    add_to_context(
        phase=current_phase,
        constraint="Use JWT tokens for authentication"
    )

    # If prototyped, merge winning branch
    if prototyped:
        merge_worktree("compare-jwt")
        cleanup_worktree("compare-session")
```

## Branch Comparison

Compare existing git branches:
```
/coder:compare --branch feature/jwt feature/sessions
```

```markdown
## Branch Comparison

### feature/jwt (3 commits ahead)
- Added JWT middleware
- Added refresh token logic
- Added token tests

### feature/sessions (4 commits ahead)
- Added Redis connection
- Added session middleware
- Added session store
- Added session tests

### Diff Summary
| Metric | JWT | Sessions |
|--------|-----|----------|
| Files | 5 | 7 |
| Lines | 180 | 240 |
| Dependencies | 1 | 3 |
| Test coverage | 85% | 82% |
```

## Worktree Mode

For isolated prototyping:
```
/coder:compare --worktree "JWT auth" "Session auth"
```

Creates separate worktrees:
```
project/
├── .git/
├── src/                    # Main branch
└── .worktrees/
    ├── compare-jwt/        # JWT prototype
    └── compare-session/    # Session prototype
```

## Integration Points

- Spawns: Research agents for each approach
- Creates: Worktrees if prototyping
- Records: Decision in STATE.md and/or DECISIONS.md
- Updates: Phase context with chosen approach
- Cleans: Non-selected worktrees/branches
