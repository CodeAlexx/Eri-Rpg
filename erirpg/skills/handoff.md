# /coder:handoff - Generate Handoff Documentation

Create comprehensive context documentation for human developers or another AI.

## CLI Integration

**First, call the CLI to gather handoff context:**
```bash
# Generate for human (default)
erirpg coder-handoff

# Generate for AI continuation
erirpg coder-handoff --for ai

# Focus on specific phase
erirpg coder-handoff --phase 3

# Brief summary only
erirpg coder-handoff --brief
```

This returns JSON with:
- `target`: "human" or "ai"
- `output_path`: Where to write handoff doc
- `context`: Gathered project context (project, state, roadmap, progress, git)
- `generated`: Timestamp

Use this context to generate the handoff document below.

---

## Usage

```
/coder:handoff                     # Full project handoff
/coder:handoff --phase 3           # Handoff specific phase
/coder:handoff --for human         # Optimized for human reader
/coder:handoff --for ai            # Optimized for AI continuation
/coder:handoff --brief             # Summary only
```

## When to Use

- Transitioning project to another developer
- Handing off to a different AI session
- Creating documentation for team
- Pausing project for extended period
- Onboarding new team members

## Handoff Contents

### For Humans
```
.planning/HANDOFF.md
├── Executive Summary
├── Project Overview
├── Current State
├── Architecture Guide
├── Key Decisions
├── Known Issues
├── Getting Started
├── Development Guide
└── Appendix
```

### For AI
```
.planning/HANDOFF-AI.md
├── Project Context
├── Codebase Structure
├── Patterns & Conventions
├── Current Position
├── Pending Work
├── Constraints
├── Decision History
└── Resume Instructions
```

## Execution Steps

### Step 1: Gather Context

```python
def gather_handoff_context(project):
    return {
        "project": load_project_md(),
        "roadmap": load_roadmap(),
        "state": load_state(),
        "decisions": aggregate_decisions(),
        "patterns": extract_patterns(),
        "architecture": analyze_architecture(),
        "issues": collect_issues(),
        "todos": collect_todos(),
        "metrics": load_metrics()
    }
```

### Step 2: Generate Human Handoff

```markdown
# Project Handoff: my-app

**Generated:** 2026-01-30
**Author:** Claude (eri-coder)
**Audience:** Human developers

---

## Executive Summary

**my-app** is a task management application built with Next.js and PostgreSQL. The project is 80% complete with 4 of 5 phases done.

**Key Points:**
- Production-ready authentication system
- Core task CRUD implemented
- Pending: Calendar integration (Phase 5)
- Estimated remaining: 1 day

---

## Project Overview

### Vision
A simple task management app for personal productivity with calendar sync.

### Users
- Individual users managing personal tasks
- No multi-tenant/team features (v1)

### Tech Stack
| Layer | Technology | Why Chosen |
|-------|------------|------------|
| Frontend | Next.js 14 | App router, SSR |
| Database | PostgreSQL | Relational, reliable |
| ORM | Prisma | Type-safe, migrations |
| Auth | JWT | Stateless, simple |
| Styling | Tailwind | Utility-first |

---

## Current State

### Progress
```
[████████████████░░░░] 80%
Phase 4 of 5 complete
```

### What's Done
- ✅ Project setup and scaffold
- ✅ User authentication (register, login, logout)
- ✅ Task CRUD (create, read, update, delete)
- ✅ Task filtering and search

### What's Pending
- ⏳ Calendar integration (Google Calendar)
- ⏳ Reminders/notifications
- ⏳ Performance optimization

### Known Issues
1. **Calendar API rate limiting** - Need to implement caching
2. **Mobile responsiveness** - Task list needs work on small screens

---

## Architecture Guide

### Directory Structure
```
src/
├── app/              # Next.js app router pages
│   ├── (auth)/       # Auth pages (login, register)
│   ├── dashboard/    # Main app pages
│   └── api/          # API routes
├── components/       # React components
│   ├── ui/           # Base UI components
│   └── features/     # Feature-specific
├── lib/              # Utilities
│   ├── auth/         # Auth helpers
│   ├── db/           # Prisma client
│   └── utils/        # General utilities
└── types/            # TypeScript types
```

### Data Flow
```
User Action
    ↓
React Component
    ↓
API Route (/api/*)
    ↓
Service Layer (lib/services/)
    ↓
Prisma ORM
    ↓
PostgreSQL
```

### Key Files
| File | Purpose |
|------|---------|
| `src/lib/auth/jwt.ts` | JWT token handling |
| `src/lib/db/prisma.ts` | Database client |
| `src/components/features/TaskList.tsx` | Main task view |
| `prisma/schema.prisma` | Database schema |

---

## Key Decisions

### D1: JWT vs Sessions
**Chose:** JWT tokens in httpOnly cookies
**Why:** Simpler infrastructure, stateless scaling
**Trade-off:** Harder to revoke (mitigated with short expiry)

### D2: Prisma vs Raw SQL
**Chose:** Prisma ORM
**Why:** Type safety, migrations, developer experience
**Trade-off:** Slight performance overhead (acceptable)

### D3: App Router vs Pages Router
**Chose:** Next.js App Router
**Why:** Modern patterns, server components
**Trade-off:** Newer, some edge cases

---

## Getting Started

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- pnpm (recommended)

### Setup
```bash
# Clone and install
git clone <repo>
cd my-app
pnpm install

# Database
cp .env.example .env  # Edit with your DB URL
pnpm prisma migrate dev

# Run
pnpm dev
```

### Key Commands
```bash
pnpm dev          # Development server
pnpm build        # Production build
pnpm test         # Run tests
pnpm lint         # Lint check
pnpm prisma studio # Database GUI
```

---

## Development Guide

### Adding a New Feature
1. Create API route in `src/app/api/`
2. Add service in `src/lib/services/`
3. Create components in `src/components/features/`
4. Add tests in `tests/`

### Testing
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/`

Run with: `pnpm test`

### Code Style
- ESLint + Prettier configured
- Commit messages: Conventional Commits
- PR reviews required

---

## Appendix

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection |
| JWT_SECRET | Yes | Token signing key |
| GOOGLE_CLIENT_ID | No | For calendar sync |

### API Reference
See: `docs/API.md`

### Troubleshooting
See: `docs/TROUBLESHOOTING.md`
```

### Step 3: Generate AI Handoff

```markdown
# AI Handoff: my-app

**Context Type:** eri-coder project handoff
**Generated:** 2026-01-30T15:00:00Z
**Source Session:** Continue with /coder:resume

---

## Project Context

### Identity
```yaml
name: my-app
type: web-application
stack: [nextjs, typescript, prisma, postgresql]
status: phase-4-complete
```

### Planning Location
```
.planning/
├── PROJECT.md      # Vision, constraints
├── ROADMAP.md      # Phase structure
├── STATE.md        # Current position
├── REQUIREMENTS.md # Feature list
└── phases/         # Execution artifacts
```

---

## Current Position

```yaml
phase: 5
phase_name: Calendar Integration
phase_status: not_started
total_phases: 5
completion: 80%
```

### Resume Command
```
/coder:plan-phase 5
```

---

## Codebase Structure

### Entry Points
- `src/app/page.tsx` - Home page
- `src/app/api/*` - API routes
- `prisma/schema.prisma` - Database schema

### Key Modules
| Module | Path | Purpose |
|--------|------|---------|
| Auth | `src/lib/auth/` | JWT handling |
| Tasks | `src/lib/services/task.ts` | Task CRUD |
| DB | `src/lib/db/` | Prisma client |

### Pattern: API Route
```typescript
// Standard API route structure
export async function POST(req: Request) {
  try {
    const user = await authenticate(req);
    const data = await validate(req, schema);
    const result = await service.action(data);
    return Response.json(result);
  } catch (error) {
    return handleError(error);
  }
}
```

---

## Constraints

### Must Follow
1. Use existing patterns from codebase
2. JWT auth for all protected routes
3. Prisma for database access
4. Zod for validation
5. Tailwind for styling

### Must Avoid
1. Raw SQL queries
2. Client-side auth tokens (localStorage)
3. Inline styles
4. Any dependencies

---

## Pending Work

### Phase 5: Calendar Integration
**Goal:** Users can sync tasks with Google Calendar

**Requirements:**
- REQ-018: Connect Google account
- REQ-019: Sync tasks to calendar
- REQ-020: Show calendar events in app

**Approach:**
- Use Google Calendar API
- OAuth2 for auth
- Background sync job

---

## Decision History

### Recent Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Calendar API | Google | User requested |
| Sync strategy | Pull-based | Simpler, rate limit friendly |
| Background jobs | None (cron) | No extra infra |

### Decisions to Make
1. How to handle calendar sync conflicts
2. Rate limiting strategy for API calls

---

## Resume Instructions

1. Read `.planning/STATE.md` for current position
2. Read `.planning/ROADMAP.md` for phase 5 goals
3. Run `/coder:plan-phase 5` to create execution plans
4. Execute with `/coder:execute-phase 5`
5. Verify with `/coder:verify-work 5`

### Context to Load
```
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@src/lib/auth/jwt.ts
@prisma/schema.prisma
```
```

### Step 4: Save and Report

```markdown
## Handoff Generated

**Files created:**
- `.planning/HANDOFF.md` (human-readable)
- `.planning/HANDOFF-AI.md` (AI-optimized)

### For Humans
Share HANDOFF.md with team members. Contains:
- Project overview and vision
- Architecture guide
- Development instructions
- Key decisions explained

### For AI
To continue in new session:
1. Read HANDOFF-AI.md
2. Run `/coder:resume`
3. Or start from current state

### Next Steps
| Recipient | Action |
|-----------|--------|
| New developer | Read HANDOFF.md, run getting started |
| New AI session | Load HANDOFF-AI.md, run /coder:resume |
| Team | Share HANDOFF.md in docs |
```

## Handoff Modes

### --for human
- Expanded explanations
- Getting started guide
- Troubleshooting section
- Less technical detail

### --for ai
- Structured context
- File references with @
- Constraint list
- Resume commands

### --brief
- One-page summary
- Current state only
- Next actions

## Integration Points

- Reads: All planning artifacts, code structure, decisions
- Creates: HANDOFF.md, HANDOFF-AI.md
- Uses: Project patterns, conventions
- Supports: Both human and AI recipients
