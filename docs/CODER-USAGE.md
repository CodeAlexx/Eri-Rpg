# ERI-CODER Usage Guide

**Vibe code new projects from zero to production.**

## Quick Start

```bash
# Start a new project
/coder:new-project my-app "A task management app"

# Follow the 8-phase initialization...
# Then build phase by phase:
/coder:plan-phase 1
/coder:execute-phase 1
/coder:verify-work 1

# Repeat for each phase until done
/coder:complete-milestone v1.0
```

---

## Two Systems, One Workflow

| System | Purpose | When to Use |
|--------|---------|-------------|
| `/coder:*` | Vibe coding new projects | Building from scratch |
| `/eri:*` | Tracking existing projects | Maintaining mature codebases |

**Lifecycle:** Build with `/coder:*` → Mature → Onboard with `/eri:index` → Maintain with `/eri:*`

---

## The Coder Workflow

### Phase 1: Start a New Project

```bash
/coder:new-project my-app "Description of what you're building"
```

This runs 8 initialization phases:
1. **Setup** - Creates `.planning/` directory, checks for existing code
2. **Brownfield** - If code exists, offers `/coder:map-codebase`
3. **Questioning** - Deep Q&A to surface requirements
4. **PROJECT.md** - Synthesizes vision, constraints, decisions
5. **Preferences** - Mode (yolo/interactive), depth, parallelization
6. **Research** - Parallel agents research stack, features, pitfalls
7. **Requirements** - User selects v1 scope, generates REQ-IDs
8. **Roadmap** - Derives phases from requirements

**Output:** `.planning/` directory with PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md

---

### Phase 2: Optional - Discuss Implementation

```bash
/coder:discuss-phase 1
```

Before planning, capture your preferences:
- UI density and layout choices
- API response formats
- Database decisions
- Error handling approaches

**Output:** `.planning/phases/01-foundation/01-CONTEXT.md`

---

### Phase 3: Plan the Phase

```bash
/coder:plan-phase 1
```

Creates executable PLAN.md files with:
- **Goal-backward methodology**: Observable truths, artifacts, key links
- **2-3 tasks per plan** (keeps context manageable)
- **Wave assignments** for parallel execution
- **Verification commands**

**Output:** `.planning/phases/01-foundation/01-01-PLAN.md`, etc.

---

### Phase 4: Execute the Phase

```bash
/coder:execute-phase 1
```

Executes plans using wave-based parallelization:
- **Wave 1** plans run in parallel
- Wait for completion
- **Wave 2** plans run in parallel
- And so on...

**Deviation Rules:**
| Rule | Action | Example |
|------|--------|---------|
| 1. Bug found | Auto-fix | Logic error, type error |
| 2. Missing critical | Auto-add | Error handling, validation |
| 3. Blocking issue | Auto-fix | Missing import, config |
| 4. Architecture change | **STOP** | New DB table, switching libs |

**Output:** `.planning/phases/01-foundation/01-01-SUMMARY.md`, etc.

---

### Phase 5: Verify the Work

```bash
/coder:verify-work 1
```

Three-level verification:
1. **Exists** - Does the file exist?
2. **Substantive** - Real code (not stubs)?
3. **Wired** - Connected to the system?

Then manual UAT:
- Claude guides you through testing each deliverable
- You report pass/fail
- Failures trigger debugger for root cause

**Output:** `.planning/phases/01-foundation/01-VERIFICATION.md`, `01-UAT.md`

---

### Phase 6: Repeat or Complete

**If more phases:**
```bash
/coder:plan-phase 2
/coder:execute-phase 2
/coder:verify-work 2
```

**If all phases done:**
```bash
/coder:complete-milestone v1.0
```

This:
- Archives milestone to `.planning/archive/`
- Creates git tag
- Prepares STATE.md for next version

---

## Roadmap Management

### Add a Phase
```bash
/coder:add-phase "API-Integration" "Connect to external payment API"
```

### Insert Urgent Phase
```bash
/coder:insert-phase 2 "Hotfix" "Fix critical security issue"
# Renumbers subsequent phases
```

### Remove Future Phase
```bash
/coder:remove-phase 5
# Can't remove completed/in-progress phases
```

---

## Session Management

### Pause Work
```bash
/coder:pause "EOD - continuing tomorrow"
```

Creates `.planning/.continue-here.md` with:
- Current position
- Uncommitted changes
- What was happening
- Next steps

### Resume Work
```bash
/coder:resume
```

---

## Starting a New Version

```bash
/coder:new-milestone v2.0
```

This:
- Loads deferred v2 requirements
- Lets you add/remove requirements
- Creates new roadmap phases
- Resets STATE.md for new milestone

---

## Brownfield Projects

For existing codebases:

```bash
/coder:map-codebase all
```

Focus options: `tech`, `arch`, `quality`, `concerns`, `all`

Creates `.planning/codebase/` with:
- STACK.md - Languages, frameworks, dependencies
- ARCHITECTURE.md - Structure, patterns, data flow
- CONVENTIONS.md - Coding style, naming patterns
- CONCERNS.md - Tech debt, security issues, risks

Then continue with `/coder:new-project` to add features.

---

## Directory Structure

```
.planning/
├── PROJECT.md          # Vision, constraints, decisions
├── REQUIREMENTS.md     # REQ-IDs with priorities
├── ROADMAP.md          # Phases with success criteria
├── STATE.md            # Current position
├── config.json         # Workflow preferences
├── .continue-here.md   # Resume state (if paused)
├── research/           # Research artifacts
│   ├── STACK.md
│   ├── FEATURES.md
│   ├── ARCHITECTURE.md
│   ├── PITFALLS.md
│   └── SUMMARY.md
├── codebase/           # Brownfield analysis
│   ├── STACK.md
│   ├── ARCHITECTURE.md
│   └── CONCERNS.md
├── phases/
│   ├── 01-foundation/
│   │   ├── 01-CONTEXT.md
│   │   ├── 01-01-PLAN.md
│   │   ├── 01-01-SUMMARY.md
│   │   ├── 01-VERIFICATION.md
│   │   └── 01-UAT.md
│   └── 02-core-features/
│       └── ...
└── archive/
    └── v1.0/
        ├── STATE.md
        └── ROADMAP.md
```

---

## Transitioning to Maintenance Mode

When your project matures and you want to switch from vibe-coding to tracking:

```bash
# Index the codebase into eri-rpg
/eri:index .

# Now use eri commands for maintenance
/eri:start
/eri:recall auth      # Recall what you learned
/eri:plan fix-bug     # Plan changes
/eri:execute          # Execute with verification
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `/coder:new-project <name> [desc]` | Start new project (8 phases) |
| `/coder:map-codebase [focus]` | Analyze existing codebase |
| `/coder:discuss-phase <N>` | Capture implementation decisions |
| `/coder:plan-phase <N> [--gaps]` | Create executable plans |
| `/coder:execute-phase <N>` | Execute with wave parallelization |
| `/coder:verify-work <N>` | Manual UAT with debugging |
| `/coder:add-phase <name> <goal>` | Append phase to roadmap |
| `/coder:insert-phase <after> <name> <goal>` | Insert urgent phase |
| `/coder:remove-phase <N>` | Remove future phase |
| `/coder:pause [reason]` | Create handoff state |
| `/coder:resume` | Resume from handoff |
| `/coder:new-milestone <name>` | Start new version |
| `/coder:complete-milestone [name]` | Archive and tag release |

---

## Tips

1. **Let questioning go deep** - The more you clarify upfront, the better the plans
2. **Use discuss-phase for gray areas** - Lock decisions before planning
3. **Trust the deviation rules** - Rules 1-3 auto-fix, only rule 4 stops
4. **Verify after each phase** - Don't accumulate unverified code
5. **Pause before stopping** - Your future self will thank you

---

## Status Line Indicators

When active:
- `🎸 coder` = Vibe coding mode (building new)
- `🔧 eri` = Tracking mode (maintaining existing)
