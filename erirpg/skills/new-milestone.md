---
name: coder:new-milestone
description: Start a new version/milestone on an existing project
argument-hint: "<milestone-name>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Task
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to get milestone context:**
```bash
erirpg coder-new-milestone "v2.0"
```

This returns JSON with:
- `milestone_name`: Name for the new milestone
- `has_project`: Whether PROJECT.md exists
- `v2_requirements`: REQ-IDs deferred to v2
- `v2_count`: Number of v2 requirements
- `previous_milestones`: Names of completed milestones

Use this data to prepare the new milestone.

---

<objective>
Start a new milestone (version) on an existing project.
Loads v2 requirements, creates new roadmap phases, prepares for development.
</objective>

<context>
Milestone name: $ARGUMENTS (e.g., "v2.0", "2.0", "Phase 2")
Read: REQUIREMENTS.md (v2 scope), previous milestone learnings
Output: Updated ROADMAP.md with new phases, fresh STATE.md
</context>

<process>
## Step 1: Load Previous Context
```bash
cat .planning/REQUIREMENTS.md
cat .planning/archive/*/STATE.md 2>/dev/null | head -50
cat .planning/PROJECT.md
```

Extract:
- v2 requirements (deferred from v1)
- Learnings from previous milestone
- Original project vision

## Step 2: Review/Update Requirements
Show v2 requirements to user:
"These requirements were deferred to v2. Review and adjust:"

| REQ-ID | Requirement | Still Needed? |
|--------|-------------|---------------|

Use AskUserQuestion:
- "Any requirements to remove?"
- "Any new requirements to add?"
- "Priority changes?"

Update REQUIREMENTS.md with changes.

## Step 3: Research (if needed)
If new technologies or patterns needed for v2:
- Spawn researchers for new domains
- Update .planning/research/ with new findings

## Step 4: Create New Roadmap
Spawn eri-roadmapper agent with:
- Updated REQUIREMENTS.md
- Previous milestone learnings
- Project constraints

Roadmapper appends new phases to ROADMAP.md:
```markdown
## Milestone: {new-milestone-name}

### Phase {N+1}: {Name}
**Goal:** {outcome}
**Requirements:** REQ-xxx, REQ-yyy
**Success Criteria:**
- {observable truth}
...
```

## Step 5: Update STATE.md
```markdown
# Project State

## Current Position
Milestone: {new-milestone-name}
Phase: 1 of M ({first-phase-name})
Plan: 0 of 0 (not yet planned)
Status: Ready to plan

## Previous Milestones
- v1.0: completed {date}

## Accumulated Context
{learnings from previous milestone}

## Last Activity
{timestamp} - Started milestone {name}
```

## Step 6: Commit
```bash
git add .planning/
git commit -m "milestone({name}): initialize new milestone"
```
</process>

<completion>
When new milestone initialized:
1. Show new phases created
2. Show requirements mapped
3. Suggest next: `/coder:discuss-phase {N}` or `/coder:plan-phase {N}`
</completion>
