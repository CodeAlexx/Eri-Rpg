---
name: coder:add-phase
description: Append a new phase to the current milestone roadmap
argument-hint: "<phase-name> <goal>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to get phase info:**
```bash
erirpg coder-add-phase "Phase Name" "Goal description"
```

This returns JSON with:
- `phase_number`: Next available phase number
- `phase_name`: Name provided
- `goal`: Goal description
- `existing_phases`: Array of current phases [{number, name}]
- `unassigned_requirements`: REQ-IDs not yet assigned to phases

Use this data to confirm phase number and show available requirements.

---

<objective>
Add a new phase to the end of the current milestone roadmap.
Maps requirements to the phase and defines success criteria.
</objective>

<context>
Phase name: $ARGUMENTS (first word)
Goal: $ARGUMENTS (rest of line)
Read: ROADMAP.md, REQUIREMENTS.md
Output: Updated ROADMAP.md with new phase
</context>

<process>
## Step 1: Load Current State
```bash
cat .planning/ROADMAP.md
cat .planning/REQUIREMENTS.md
```

Determine:
- Current milestone
- Existing phase count
- Unassigned requirements

## Step 2: Gather Phase Details
Use AskUserQuestion:
1. "What requirements does this phase address?" (show unassigned REQ-IDs)
2. "What are the success criteria? (observable truths)"
3. "Any dependencies on other phases?"

## Step 3: Append to ROADMAP.md
Add new phase section:

```markdown
### Phase {N}: {phase-name}
**Goal:** {goal}
**Requirements:** {REQ-IDs}
**Dependencies:** {prior phases or "None"}
**Success Criteria:**
- {observable truth 1}
- {observable truth 2}
- {observable truth 3}
```

## Step 4: Update STATE.md
If this is the first phase after milestone init, update:
```
Phase: 1 of {N} ({phase-name})
Status: Ready to discuss/plan
```

## Step 5: Commit
```bash
git add .planning/ROADMAP.md .planning/STATE.md
git commit -m "plan: add phase {N} - {phase-name}"
```
</process>

<completion>
## On Completion

### 1. Verify Committed

```bash
git status --short .planning/
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE {N} ADDED: {phase-name}                               ║
╠════════════════════════════════════════════════════════════════╣
║  Goal: {goal}                                                  ║
║  Requirements: {REQ-IDs}                                       ║
║  Dependencies: {deps or None}                                  ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Plan or discuss the phase

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Optional: Run `/coder:discuss-phase {N}` first to clarify approach.
```
</completion>
