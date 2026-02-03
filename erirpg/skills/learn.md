# /coder:learn - Capture Patterns for Reuse

Extract patterns, decisions, and learnings from successful runs for future projects.

## CLI Integration

**Call the CLI to store patterns:**
```bash
# Store a pattern
erirpg coder-learn pattern "API Layer" -d "Structured API with separation of concerns" -t api -t backend

# Store a decision
erirpg coder-learn decision "ORM Choice" -d "Chose Prisma for type safety"

# Store a gotcha
erirpg coder-learn gotcha "JWT Expiry" -d "Tokens not invalidated on password change"

# Store a convention
erirpg coder-learn convention "File Naming" -d "Use kebab-case for files"
```

Returns JSON with the created entry including ID and timestamp.

---

## Usage

```
/coder:learn                       # Learn from current project
/coder:learn --phase 2             # Learn from specific phase
/coder:learn --pattern "auth"      # Extract auth pattern
/coder:learn --export              # Export to reusable template
```

## What Gets Learned

### 1. Architectural Patterns
- Component structures that worked
- Data flow patterns
- Integration approaches
- Error handling strategies

### 2. Decision Patterns
- Decisions made and why
- Trade-offs evaluated
- What worked, what didn't

### 3. Code Patterns
- Successful implementations
- Reusable utilities
- Testing strategies

### 4. Process Patterns
- Effective phase structures
- Useful task breakdowns
- Verification approaches

## Execution Steps

### Step 1: Analyze Project

```python
def analyze_for_learning(project):
    return {
        "stack": extract_stack(project),
        "architecture": extract_architecture(project),
        "patterns": extract_patterns(project),
        "decisions": extract_decisions(project),
        "metrics": extract_metrics(project),
        "lessons": extract_lessons(project)
    }
```

### Step 2: Identify Patterns

```markdown
## Patterns Identified

### Architectural Patterns

#### 1. API Layer Pattern
**Found in:** Phase 2 - Authentication
**Pattern:**
```
src/api/
├── routes/       # Express/Fastify route handlers
├── middleware/   # Auth, validation, error handling
├── services/     # Business logic
└── validators/   # Zod/Joi schemas
```
**Benefit:** Clear separation, testable services
**Reuse:** Any API-based project

#### 2. Auth Pattern
**Found in:** Phase 2 - Authentication
**Pattern:**
- JWT in httpOnly cookie
- Refresh token rotation
- Middleware-based protection
**Files:** middleware/auth.ts, services/auth.ts
**Benefit:** Stateless, secure, scalable

### Code Patterns

#### 3. Error Handling Pattern
**Found in:** Multiple phases
```typescript
// Consistent error response
class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string
  ) {
    super(message);
  }
}

// Error middleware
app.use((err, req, res, next) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: err.code,
      message: err.message
    });
  }
  // ... handle unknown errors
});
```

#### 4. Validation Pattern
**Found in:** Phase 2
```typescript
// Zod schema + middleware combo
const userSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

const validate = (schema) => (req, res, next) => {
  const result = schema.safeParse(req.body);
  if (!result.success) {
    throw new AppError(400, 'VALIDATION_ERROR', result.error);
  }
  req.validated = result.data;
  next();
};
```

### Decision Patterns

#### 5. Technology Selection
| Decision | Choice | Rationale |
|----------|--------|-----------|
| ORM | Prisma | Type-safe, migrations |
| Validation | Zod | TypeScript-first |
| Auth | JWT | Stateless, simple |
| State | Zustand | Simple, no boilerplate |

### Process Patterns

#### 6. Phase Structure
**Effective for:** Web applications
```
Phase 1: Foundation (DB, scaffold)
Phase 2: Auth (users, sessions)
Phase 3: Core Features (main functionality)
Phase 4: Integrations (external services)
Phase 5: Polish (UX, performance)
```
```

### Step 3: Store Patterns

Save to `~/.eri-rpg/patterns/`:

```yaml
# ~/.eri-rpg/patterns/api-layer.yaml
name: API Layer Pattern
category: architecture
tags: [api, backend, express, fastify]
source_project: my-app
created: 2026-01-30

description: |
  Structured API layer with clear separation of concerns.

structure:
  - path: src/api/routes/
    purpose: HTTP route handlers
  - path: src/api/middleware/
    purpose: Cross-cutting concerns
  - path: src/api/services/
    purpose: Business logic
  - path: src/api/validators/
    purpose: Input validation schemas

example_files:
  - src/api/routes/users.ts
  - src/api/middleware/auth.ts
  - src/api/services/user.ts

when_to_use:
  - REST API backends
  - Express/Fastify projects
  - Projects requiring auth

when_not_to_use:
  - Simple scripts
  - GraphQL (different pattern)
  - Serverless functions
```

### Step 4: Present Summary

```markdown
## Learning Complete

**Project:** my-app
**Patterns extracted:** 8
**Saved to:** ~/.eri-rpg/patterns/

### Patterns Saved
| Pattern | Category | Tags |
|---------|----------|------|
| API Layer | architecture | api, backend |
| JWT Auth | architecture | auth, jwt |
| Error Handling | code | errors |
| Validation | code | validation, zod |
| Tech Selection | decision | stack |
| Phase Structure | process | workflow |
| Testing Strategy | testing | vitest |
| CI/CD Setup | devops | github-actions |

### Usage in Future Projects
```
/coder:new-project my-new-app --use-pattern "api-layer" --use-pattern "jwt-auth"
```

### Pattern Library
View all patterns: `cat ~/.eri-rpg/patterns/index.json`
Total patterns: 15
```

## Learn From Specific Phase

```
/coder:learn --phase 2
```

Focuses on patterns from that phase only.

## Extract Specific Pattern

```
/coder:learn --pattern "auth"
```

```markdown
## Extracting: Auth Pattern

**Source:** Phase 2 - Authentication
**Files:** 5
**Lines:** 320

### Pattern Components
1. JWT token generation
2. Cookie-based storage
3. Refresh token rotation
4. Middleware protection
5. Session invalidation

### Extracted Template
Creating: `~/.eri-rpg/patterns/jwt-auth/`
- template/middleware/auth.ts
- template/services/auth.ts
- template/routes/auth.ts
- README.md
- pattern.yaml

### Usage
```
/coder:new-project --use-pattern jwt-auth
```
```

## Export Full Template

```
/coder:learn --export
```

Creates complete project template:
```
~/.eri-rpg/templates/my-app-template/
├── template/
│   ├── src/
│   ├── tests/
│   └── config files
├── patterns/
│   └── [extracted patterns]
├── decisions.md
├── roadmap-template.md
└── template.yaml
```

## Pattern Categories

| Category | Examples |
|----------|----------|
| `architecture` | API structure, state management, data flow |
| `code` | Error handling, validation, utilities |
| `decision` | Technology choices, trade-off resolutions |
| `process` | Phase structures, task breakdowns |
| `testing` | Test strategies, coverage approaches |
| `devops` | CI/CD, deployment, monitoring |

## Integration with New Projects

When starting new project:
```python
def apply_patterns(project, patterns):
    for pattern in patterns:
        # Copy template files
        copy_pattern_template(pattern, project)

        # Add to project context
        project.context.append({
            "type": "pattern",
            "name": pattern.name,
            "guidance": pattern.when_to_use
        })

        # Suggest in roadmap
        if pattern.suggests_phase:
            add_suggested_phase(project, pattern)
```

## Integration Points

- Reads: Project SUMMARY files, code, decisions
- Writes: ~/.eri-rpg/patterns/
- Creates: Pattern templates and YAML configs
- Indexes: Pattern library for search
- Uses: Pattern in new projects via --use-pattern
