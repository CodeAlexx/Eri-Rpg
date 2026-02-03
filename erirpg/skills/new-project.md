---
name: coder:new-project
description: Vibe code a new project with full eri-coder workflow (8 phases)
argument-hint: "<name> [description]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
  - AskUserQuestion
---

# New Project

**Run the CLI command first to check environment:**

```bash
python3 -m erirpg.cli coder-new-project "$ARGUMENTS"
```

The CLI returns:
- `planning_exists`: Whether .planning already exists
- `has_project`: Whether PROJECT.md exists
- `brownfield`: Whether existing code detected
- `code_dir`: Directory with existing code (if brownfield)
- `project_type`: Detected type (node, python, rust, go)

## Workflow Based on CLI Output

### If planning_exists and has_project
Ask user where to create new project, or if they want `/coder:add-feature` instead.

### If brownfield detected
Present options:
1. Map codebase first (`/coder:map-codebase`), then plan
2. Use `/coder:add-feature` for adding to existing code
3. Skip mapping, start fresh

### Otherwise: 8-Phase Flow

**Phase 1: SETUP**
- Initialize git if needed
- Create .planning/ directory

**Phase 2: QUESTIONING**
Use AskUserQuestion for:
- What problem does this solve?
- Who are the users?
- What does success look like?
- What's out of scope for v1?
- Technical constraints?

**Phase 3: PROJECT.md**
Create .planning/PROJECT.md with synthesized answers.

**Phase 4: PREFERENCES**
Ask and save to .planning/config.json:
- mode: yolo | interactive
- depth: quick | standard | comprehensive
- workflow.research: true | false
- workflow.plan_check: true | false
- workflow.verifier: true | false

**Phase 5: RESEARCH** (if enabled)
Spawn 4 parallel researchers → .planning/research/
Then synthesizer → SUMMARY.md

**Phase 6: REQUIREMENTS**
Present features, user selects v1 scope.
Create .planning/REQUIREMENTS.md with REQ-IDs.

**Phase 7: ROADMAP**
Spawn eri-roadmapper → .planning/ROADMAP.md
Create .planning/STATE.md

**Phase 8: COMMIT**
```bash
git add .planning/
git commit -m "docs: initialize project planning"
```

<completion>
## On Completion

### 1. Verify Everything Committed

```bash
git status --short .planning/
```

If uncommitted files, commit:
```bash
git add .planning/
git commit -m "docs: initialize {project-name} planning

- PROJECT.md: vision and constraints
- REQUIREMENTS.md: feature list with REQ-IDs
- ROADMAP.md: phased implementation plan
- STATE.md: progress tracker"
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PROJECT INITIALIZED: {project-name}                         ║
╠════════════════════════════════════════════════════════════════╣
║  Created:                                                      ║
║  - .planning/PROJECT.md                                        ║
║  - .planning/REQUIREMENTS.md                                   ║
║  - .planning/ROADMAP.md ({N} phases)                           ║
║  - .planning/STATE.md                                          ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Start Phase 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Optional: Run `/coder:discuss-phase 1` first to clarify approach.
```
</completion>
