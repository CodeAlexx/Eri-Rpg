---
name: coder:insert-phase
description: Insert an urgent phase between existing phases
argument-hint: "<after-phase-number> <phase-name> <goal>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to get insertion info:**
```bash
erirpg coder-insert-phase <after-phase> "Phase Name" "Goal"
```

This returns JSON with:
- `insert_after`: Phase number to insert after
- `new_phase_number`: Number the new phase will get
- `phase_name`: Name provided
- `goal`: Goal description
- `phases_to_renumber`: Array of phases that need +1
- `total_renumber`: Count of phases to renumber

Use this data to confirm the insertion and renumbering.

---

<objective>
Insert a new phase after a specific phase number.
Renumbers subsequent phases. Use for urgent work that can't wait.
</objective>

<context>
Insert after: $ARGUMENTS (first number)
Phase name: $ARGUMENTS (second word)
Goal: $ARGUMENTS (rest of line)
</context>

<process>
## Step 1: Load and Validate
```bash
cat .planning/ROADMAP.md
cat .planning/STATE.md
```

Check:
- Phase number exists
- Subsequent phases not yet started
- Current phase position

## Step 2: Gather Details
Use AskUserQuestion:
1. "Why is this urgent? (rationale for insertion)"
2. "What requirements does this address?"
3. "Success criteria?"

## Step 3: Renumber Phases
All phases after insertion point get +1 to their number.

Update ROADMAP.md:
- Insert new phase at position
- Renumber subsequent phases
- Update dependency references

## Step 4: Update References
Update any files that reference phase numbers:
- STATE.md
- PLAN.md files (if any reference shifted phases)

## Step 5: Commit
```bash
git add .planning/
git commit -m "plan: insert urgent phase {N} - {name}

Rationale: {why urgent}
Subsequent phases renumbered."
```
</process>

<completion>
## On Completion

### 1. Verify Committed

```bash
git status --short .planning/
```

### 2. Update STATE.md

```markdown
## Current Phase
Phase count updated: {new_total} phases

## Last Action
Completed insert-phase {N}
- Inserted: Phase {N} - {phase-name}
- Renumbered: Phases {N+1}+ shifted

## Next Step
Run `/coder:discuss-phase {N}` or `/coder:plan-phase {N}`
```

### 3. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 4. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE INSERTED: {N} - {phase-name}                          ║
╠════════════════════════════════════════════════════════════════╣
║  Position: After phase {N-1}                                   ║
║  Renumbered: {count} subsequent phases                         ║
║  Rationale: {urgency reason}                                   ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Discuss or plan the new phase

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:discuss-phase {N}  (to clarify approach)
   OR:    /coder:plan-phase {N}     (if approach is clear)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
</completion>
