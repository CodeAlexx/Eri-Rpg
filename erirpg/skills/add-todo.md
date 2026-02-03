# /coder:add-todo - Capture Idea for Later

Quickly capture an idea, improvement, or task without disrupting current workflow.

## CLI Integration

**Call the CLI to manage todos:**
```bash
# Add a todo
erirpg coder-add-todo "Add dark mode support" [--priority high]

# List todos
erirpg coder-todos [--all]
```

This returns JSON with:
- For add: `added`, `todo` object with id, description, priority, created, status
- For list: `todos` array, `count`

Use the CLI for quick capture; follow the workflow below for full management.

---

## Usage

```
/coder:add-todo "Add dark mode support"
/coder:add-todo "Refactor auth module" --priority high
/coder:add-todo "Consider Redis for caching" --category enhancement
/coder:add-todo --list                    # View all todos
/coder:add-todo --resolve 3               # Mark todo complete
```

## Purpose

During development, ideas emerge that shouldn't interrupt current work:
- Feature ideas for future versions
- Technical debt to address later
- Improvements noticed while working
- Questions to investigate

Capture them instantly, continue working.

## Execution Steps

### Step 1: Initialize Todos Directory

Create if not exists:
```
.planning/todos/
├── pending/
│   ├── 001-add-dark-mode.md
│   └── 002-refactor-auth.md
└── completed/
    └── 000-example-done.md
```

### Step 2: Create Todo Entry

Generate todo file:
```markdown
---
id: {NNN}
created: YYYY-MM-DDTHH:MM:SSZ
priority: low | medium | high
category: bug | enhancement | tech-debt | question | idea
status: pending
context_phase: {current phase if in workflow}
---

# TODO: {description}

## Captured During
Phase: {N} - {name} (or "No active phase")
Working on: {current task context}

## Details
{User's description}

## Notes
{Any additional context added}

## Related
- Files: {relevant files if detected}
- Requirements: {related REQ-IDs if applicable}
```

### Step 3: Quick Confirmation

```markdown
## Todo Captured

**#003:** Add dark mode support
**Priority:** medium
**Category:** enhancement

Saved to `.planning/todos/pending/003-add-dark-mode.md`

Continue with current work. View all: `/coder:add-todo --list`
```

### Step 4: Update STATE.md

Add to Pending Todos section:
```markdown
### Pending Todos
- #003: Add dark mode support (medium, enhancement)
- #002: Refactor auth module (high, tech-debt)
- #001: Consider Redis caching (low, idea)
```

## List Todos

`/coder:add-todo --list`:
```markdown
# Pending Todos

## High Priority
| ID | Description | Category | Created |
|----|-------------|----------|---------|
| 002 | Refactor auth module | tech-debt | 2026-01-29 |

## Medium Priority
| ID | Description | Category | Created |
|----|-------------|----------|---------|
| 003 | Add dark mode support | enhancement | 2026-01-30 |

## Low Priority
| ID | Description | Category | Created |
|----|-------------|----------|---------|
| 001 | Consider Redis caching | idea | 2026-01-28 |

---

**Total:** 3 pending todos
**Add:** `/coder:add-todo "description"`
**Resolve:** `/coder:add-todo --resolve {id}`
**Convert to phase:** `/coder:add-phase` with todo content
```

## Resolve Todo

`/coder:add-todo --resolve 3`:
```markdown
## Resolving Todo #003

**Description:** Add dark mode support

How was this resolved?
1. **Implemented** - Done as part of work
2. **Converted** - Became a phase/feature
3. **Won't do** - Decided against it
4. **Duplicate** - Already covered elsewhere

Select (1/2/3/4):
```

After selection:
```markdown
## Todo Resolved

**#003:** Add dark mode support → **Implemented**

Moved to `.planning/todos/completed/003-add-dark-mode.md`

Updated:
- STATUS.md pending todos section
- Todo marked complete with resolution
```

## Priority Levels

| Priority | When to Use | Review Cadence |
|----------|-------------|----------------|
| `high` | Blocking future work, security issues | Before next phase |
| `medium` | Should do soon, quality improvements | Before next milestone |
| `low` | Nice to have, ideas to consider | When time permits |

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `bug` | Known issue to fix | "Login fails on Safari" |
| `enhancement` | Feature improvement | "Add dark mode" |
| `tech-debt` | Code quality issue | "Refactor auth module" |
| `question` | Need to investigate | "Is Redis needed?" |
| `idea` | Future consideration | "Mobile app version" |

## Integration with Workflow

### During Phase Work
Todo captures current context:
```markdown
## Captured During
Phase: 3 - Core Features
Working on: Plan 3-02, Task 2 (API endpoints)
```

### Convert to Phase
For larger todos, convert to proper phase:
```bash
# Read todo for context
cat .planning/todos/pending/003-add-dark-mode.md

# Create phase with todo content
/coder:add-phase "Dark Mode" "Add dark mode theme support"

# Resolve original todo
/coder:add-todo --resolve 3
# Select: 2 (Converted)
```

### Milestone Review
Before `/coder:complete-milestone`, review todos:
```markdown
## Pre-Milestone Todo Review

**High priority todos:** 1
- #002: Refactor auth module

**Recommendation:** Address high-priority todos before completing milestone.

Options:
1. Address now (create quick task or phase)
2. Defer to next milestone
3. Mark as won't do

Select for each high-priority todo:
```

## Quick Add Syntax

Shortcuts for faster capture:
```bash
# With priority
/coder:add-todo "Fix bug" --priority high
/coder:add-todo "Fix bug" -p high

# With category
/coder:add-todo "Add feature" --category enhancement
/coder:add-todo "Add feature" -c enhancement

# Combined
/coder:add-todo "Security fix" -p high -c bug
```

## Batch Operations

`/coder:add-todo --cleanup`:
```markdown
## Todo Cleanup

Review old todos (>30 days):

| ID | Description | Age | Action? |
|----|-------------|-----|---------|
| 001 | Consider Redis | 45 days | keep/resolve/delete |

For each, select action or [Enter] to keep.
```
