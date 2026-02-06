# Quick Reference: Where to Find Things

## Lost? Start Here

| I need to... | Go to |
|--------------|-------|
| Understand coder workflow | `docs/QUICK_REFERENCE.md` |
| Find the completion pattern spec | `~/.claude/eri-rpg/references/command-patterns.md` |
| Check skill compliance | `python3 -m erirpg.scripts.lint_skills` |
| Find a skill file | `erirpg/skills/*.md` |
| Find an agent spec | `erirpg/agents/*.md` |
| Understand CLI commands | `erirpg/cli_commands/` |

## File Locations

### Skills (User-Facing Commands)

**Source:** `erirpg/skills/*.md`
**Installed to:** `~/.claude/commands/coder/`

41 skills total. Key ones:
- `new-project.md` - Start new project
- `plan-phase.md` - Create execution plans
- `execute-phase.md` - Run the plans
- `verify-work.md` - User acceptance testing
- `init.md` - Session recovery

### Agents (Thick Execution Logic)

**Source:** `erirpg/agents/*.md`
**Installed to:** `~/.eri-rpg/agents/`

Key agents:
- `eri-planner.md` - Creates PLAN.md files
- `eri-executor.md` - Executes plans with commits
- `eri-verifier.md` - Goal-backward verification
- `eri-phase-researcher.md` - Research before planning

### Reference Documentation

**Location:** `~/.claude/eri-rpg/references/`

- `command-patterns.md` - **THE authority on completion patterns**
- `checkpoints.md` - Checkpoint handling
- `tdd.md` - Test-driven development patterns
- `verification-patterns.md` - How to verify

### CLI Commands

**Location:** `erirpg/cli_commands/`

26 modules with 91+ commands:
- `coder_commands.py` - All `/coder:*` CLI backends
- `setup.py` - add, remove, list, index
- `modes.py` - take, work, done
- `knowledge.py` - learn, recall, decide

## State Files

### Global State

```
~/.eri-rpg/
├── state.json           # Active project tracking
├── registry.json        # Project name → path mapping
└── agents/              # Installed agent specs
```

### Project State

```
.planning/
├── STATE.md             # Current position (ALWAYS check this)
├── ROADMAP.md           # Phase definitions
├── REQUIREMENTS.md      # REQ-IDs
├── PROJECT.md           # Vision and constraints
├── config.json          # Workflow settings
├── EXECUTION_STATE.json # Mid-execution (enables edits)
├── .continue-here.md    # Pause/resume context
└── phases/
    └── 01-name/
        ├── PLAN.md      # Execution plan
        ├── SUMMARY.md   # Completion summary
        └── VERIFICATION.md
```

## Key Commands

### Linting

```bash
# Check all skills have completion sections
python3 -m erirpg.scripts.lint_skills

# Verbose (show passing too)
python3 -m erirpg.scripts.lint_skills --verbose
```

### State Management

```bash
# Update global state (in completion sections)
python3 -m erirpg.cli switch "$(pwd)"

# Check project state
cat .planning/STATE.md
```

### CLI Testing

```bash
# Test CLI commands directly
python3 -m erirpg.cli coder-plan-phase 1
python3 -m erirpg.cli coder-execute-phase 1
python3 -m erirpg.cli coder-quick "task description"
```

## When Things Go Wrong

### Symptom: "Ready when you are" instead of next steps

```
Cause: Missing <completion> section
Fix: Add completion per command-patterns.md
Check: python3 -m erirpg.scripts.lint_skills
```

### Symptom: Edits blocked by hook

```
Cause: No EXECUTION_STATE.json
Fix: Run /coder:execute-phase or /coder:quick
```

### Symptom: Agent spawn fails

```
Cause: API error
Fix: Retry once, then STOP and report to user
NEVER: Do the agent's job manually
```

### Symptom: STATE.md out of sync

```
Fix: /coder:init will detect and offer to reconstruct
```

## Architecture at a Glance

```
User types: /coder:plan-phase 3
                │
                ▼
Skill (thin): erirpg/skills/plan-phase.md
                │
                │ Calls CLI
                ▼
CLI (logic): python3 -m erirpg.cli coder-plan-phase 3
                │
                │ Returns JSON
                ▼
Skill continues: Spawns agent
                │
                ▼
Agent (thick): eri-planner.md (fresh 200k context)
                │
                │ Creates plans
                ▼
Skill <completion>: STATE.md → switch → /clear box
                │
                ▼
User sees: "Type /clear, then /coder:init, then /coder:execute-phase 3"
```

## Architecture Comparison

Coder uses thin skills + CLI + thick agents. Skills are orchestrators that call the CLI for state, then spawn agents with fresh context for heavy work.
