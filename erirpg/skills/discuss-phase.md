---
name: coder:discuss-phase
description: Capture implementation decisions for a specific phase before planning
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to load phase context:**
```bash
erirpg coder-discuss-phase <phase-number>
```

This returns JSON with:
- `phase`: Phase number
- `phase_content`: Full phase section from ROADMAP.md
- `goal`: Extracted goal
- `requirements`: Mapped requirements
- `context_exists`: Whether CONTEXT.md already exists
- `phase_dir`: Path to phase directory

Use this data to drive the discussion questions.

---

<objective>
Capture user's implementation preferences BEFORE planning a phase.
Creates {phase}-CONTEXT.md that planner and researcher will read.
</objective>

<context>
Phase number: $ARGUMENTS
Read from: .planning/ROADMAP.md to get phase details
Output: .planning/phases/{XX-name}/{phase}-CONTEXT.md
</context>

<process>
## Step 1: Load Phase
```bash
# Read roadmap to get phase info
cat .planning/ROADMAP.md
```

Extract:
- Phase name and number
- Phase goal
- Requirements mapped to this phase
- Success criteria

## Step 2: Analyze Phase Type
Determine what kind of phase this is:
- **UI/Visual**: Layout, density, interactions, empty states
- **API/CLI**: Response format, flags, error handling, auth
- **Data/Storage**: Schema, migrations, caching, backup
- **Integration**: Protocols, retry logic, fallbacks
- **Content**: Structure, tone, depth

## Step 3: Identify Gray Areas
Based on phase type, identify decisions that need user input:

For UI phases:
- "How should empty states look?"
- "Mobile-first or desktop-first?"
- "Dark mode support?"

For API phases:
- "REST or GraphQL?"
- "How should errors be formatted?"
- "Rate limiting needed?"

For Data phases:
- "What database?"
- "Soft delete or hard delete?"
- "Audit logging?"

## Step 4: Interactive Q&A
Use AskUserQuestion for each gray area the user wants to discuss.
Ask ONE question at a time. Wait for answer. Record.

## Step 5: Write CONTEXT.md
Create .planning/phases/{XX-name}/{phase}-CONTEXT.md:

```markdown
---
phase: {XX-name}
discussed: {timestamp}
---

# Phase {N}: {Name} - Implementation Context

## Locked Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| {what} | {choice} | {why} |

## Design Direction
{narrative summary of implementation approach}

## Gray Areas Resolved
### {Topic 1}
**Question:** {what was asked}
**Answer:** {user's decision}
**Impact:** {how this affects implementation}

## Open Questions
{anything still unresolved - planner should handle or ask}
```

## Step 6: Commit
```bash
git add .planning/phases/
git commit -m "docs(phase-{N}): capture implementation context"
```
</process>

<completion>
When done:
1. Show summary of decisions captured
2. Note what CONTEXT.md contains
3. Suggest next: `/coder:plan-phase {N}`
</completion>
