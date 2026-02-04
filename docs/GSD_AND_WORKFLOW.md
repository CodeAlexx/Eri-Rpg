# GSD Origins and Coder Workflow Architecture

## What is GSD?

**GSD (Get Shit Done)** is the original framework that eri-coder was forked from.

- **Repository:** https://github.com/glittercowboy/get-shit-done
- **Local copy:** `~/gsd/get-shit-done/`
- **Philosophy:** AI-driven structured development with verification

GSD pioneered the concept of:
- Phase-based development with clear goals
- Must-haves and verification criteria
- Wave-based parallel execution
- Goal-backward verification (check outcomes, not just tasks)

## Architecture Comparison

### GSD Architecture (Monolithic)

```
Commands → Workflows → Execution
   │           │
   └───────────┴── Everything in thick workflow files (400-700 lines each)
```

GSD workflows contain ALL logic:
- Step definitions
- Agent spawning
- State updates
- Completion logic
- Error handling

**Files:** `~/.claude/get-shit-done/workflows/*.md`

### Coder Architecture (Distributed)

```
Skills (thin) → CLI (logic) → Agents (thick)
     │              │              │
     │              │              └── Full execution context (200k fresh)
     │              └── JSON output, state management
     └── ~100 lines, just call CLI and follow output
```

**Why distributed?**
- Token efficiency: Skills are cheap to load
- Parallel execution: Agents get fresh 200k context each
- Testability: CLI commands can be unit tested
- Modularity: Change agent without touching skill

**Files:**
- Skills: `erirpg/skills/*.md` → installed to `~/.claude/commands/coder/`
- CLI: `erirpg/cli.py` + `erirpg/cli_commands/`
- Agents: `erirpg/agents/*.md` → installed to `~/.eri-rpg/agents/`

## The Completion Pattern System

### The Problem We Solved

After Phase 2 execution, Claude said "ready when you are" instead of:
1. Updating STATE.md
2. Updating global state
3. Showing clear next command

**Root cause:** Skills were missing `<completion>` sections.

### The Authoritative Documentation

**Location:** `~/.claude/eri-rpg/references/command-patterns.md`

This file defines the mandatory completion pattern for ALL state-changing commands:

```markdown
<completion>
## Step N: Update STATE.md
Update STATE.md with full context for resume...

## Step N+1: Update Global State
```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

## Step N+2: Present Next Steps
```
╔════════════════════════════════════════════════════════════════╗
║  ✓ COMMAND COMPLETE: {summary}                                 ║
╠════════════════════════════════════════════════════════════════╣
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:next-command {args}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</completion>
```

### The Linter

We created a linter to enforce this pattern:

```bash
python3 -m erirpg.scripts.lint_skills
```

Checks all state-changing skills for:
- `<completion>` section exists
- STATE.md update present
- `switch` command for global state
- `/clear` box with next command

**State-changing skills (16):**
- add-feature, add-phase, clone-behavior, complete-milestone
- discuss-phase, execute-phase, insert-phase, map-codebase
- new-milestone, new-project, pause, plan-milestone-gaps
- plan-phase, quick, remove-phase, verify-work

## Key Reference Files

### For Coder Workflow

| File | Purpose | Location |
|------|---------|----------|
| `command-patterns.md` | Completion pattern spec | `~/.claude/eri-rpg/references/` |
| Skills | User-facing commands | `erirpg/skills/*.md` |
| Agents | Thick execution logic | `erirpg/agents/*.md` |
| CLI | State management | `erirpg/cli_commands/` |

### For GSD Reference

| File | Purpose | Location |
|------|---------|----------|
| `execute-phase.md` | Wave orchestration | `~/gsd/get-shit-done/workflows/` |
| `verify-phase.md` | Goal-backward verification | `~/gsd/get-shit-done/workflows/` |
| `execute-plan.md` | Plan execution | `~/gsd/get-shit-done/workflows/` |

## State Flow

### On Command Completion

```
1. Command executes (plan-phase, execute-phase, etc.)
           │
           ▼
2. <completion> section runs:
   ├── git status check
   ├── STATE.md update (position, last action, next step)
   ├── Global state: python3 -m erirpg.cli switch "$(pwd)"
   └── /clear box with exact next command
           │
           ▼
3. User runs /clear
           │
           ▼
4. User runs /coder:init
           │
           ▼
5. Init reads STATE.md → shows position → offers next command
```

### State Files

| File | Scope | Purpose |
|------|-------|---------|
| `~/.eri-rpg/state.json` | Global | Active project tracking |
| `.planning/STATE.md` | Project | Current position, progress |
| `.planning/ROADMAP.md` | Project | Phase definitions |
| `.planning/EXECUTION_STATE.json` | Phase | Mid-execution checkpoint |
| `.planning/.continue-here.md` | Project | Pause/resume context |

## Common Gotchas

### 1. "Ready when you are" instead of next steps

**Cause:** Skill missing `<completion>` section
**Fix:** Add completion section per command-patterns.md
**Prevention:** Run `python3 -m erirpg.scripts.lint_skills`

### 2. Agent spawn fails

**Cause:** API error, timeout
**Fix:**
1. Retry once
2. If still fails, STOP and report to user
3. NEVER do the agent's job manually

**Why:** Agents have isolated context. Manual execution defeats the purpose.

### 3. Edits blocked by hook

**Cause:** No active EXECUTION_STATE.json
**Fix:**
- `/coder:execute-phase` auto-creates it
- Or use `/coder:quick` for ad-hoc work

### 4. STATE.md missing

**Cause:** Incomplete initialization
**Fix:** `/coder:init` will offer to reconstruct from artifacts

## Skill → CLI → Agent Flow

### Example: `/coder:plan-phase 3`

```
1. SKILL (erirpg/skills/plan-phase.md)
   │
   │  Thin wrapper, calls CLI:
   │  python3 -m erirpg.cli coder-plan-phase 3
   │
   ▼
2. CLI (erirpg/cli_commands/coder_commands.py)
   │
   │  Returns JSON:
   │  {
   │    "phase": 3,
   │    "phase_name": "authentication",
   │    "goal": "...",
   │    "settings": {...}
   │  }
   │
   ▼
3. SKILL continues, spawns agent:
   │
   │  Task(
   │    subagent_type="eri-planner",
   │    prompt="Create plans for phase 3..."
   │  )
   │
   ▼
4. AGENT (erirpg/agents/eri-planner.md)
   │
   │  Fresh 200k context
   │  Creates .planning/phases/03-auth/PLAN.md files
   │
   ▼
5. SKILL runs <completion> section:
   │
   │  - Git commit
   │  - STATE.md update
   │  - Global state switch
   │  - /clear box
   │
   ▼
6. USER sees: "Type /clear, then /coder:init, then /coder:execute-phase 3"
```

## GSD vs Coder Trade-offs

| Aspect | GSD | Coder |
|--------|-----|-------|
| Cognitive load | Lower (one file) | Higher (3 layers) |
| Token efficiency | Lower | Higher |
| Parallelization | None | Wave-based |
| Testability | Hard | Easy (CLI testable) |
| Failure mode | Obvious | Hidden (completion missing) |

**Verdict:** Coder's architecture is better for scale, but needs guardrails (the linter) to prevent completion sections from being forgotten.

## Quick Reference

### When something breaks

1. Check `command-patterns.md` for the spec
2. Check if skill has `<completion>` section
3. Run linter: `python3 -m erirpg.scripts.lint_skills`

### When adding new skills

1. Determine if state-changing (needs completion) or read-only
2. If state-changing, add to `STATE_CHANGING_SKILLS` in `lint_skills.py`
3. Include full `<completion>` section per command-patterns.md
4. Run linter before committing

### When comparing to GSD

1. GSD workflows are at `~/gsd/get-shit-done/workflows/`
2. GSD has similar logic but baked into workflow steps
3. Coder separates it into `<completion>` sections
