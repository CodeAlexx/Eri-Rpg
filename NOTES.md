# EriRPG Development Notes

Notes for future Claude sessions about fixes, architecture, and critical knowledge.

---

## Quick Reference

| What | Where |
|------|-------|
| Original GSD reference | https://github.com/glittercowboy/get-shit-done |
| Our implementation | This repo: `/home/alex/eri-rpg` |
| Command files | `~/.claude/commands/coder/` and `~/.claude/commands/eri/` |
| Workflow files | `~/.claude/eri-rpg/workflows/` |
| Templates | `~/.claude/eri-rpg/templates/` |
| Global state | `~/.eri-rpg/state.json` |
| Hooks | `erirpg/hooks/` (sessionstart.py, posttooluse.py, etc.) |

---

## Architecture Overview

### Two Command Families

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER RUNS COMMAND                           │
├──────────────────────────┬──────────────────────────────────────┤
│  /eri:* commands         │  /coder:* commands                   │
│  - Lightweight CLI       │  - Full workflow system              │
│  - State: .eri-rpg/      │  - State: .planning/                 │
│  - Init: /eri:start      │  - Init: /coder:init                 │
├──────────────────────────┴──────────────────────────────────────┤
│                     GLOBAL STATE                                │
│                 ~/.eri-rpg/state.json                           │
│           (shared by both families)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Key State Fields

**In `~/.eri-rpg/state.json`:**

| Field | Purpose | Updated By |
|-------|---------|------------|
| `target_project_path` | **PRIMARY** - Most recent project worked on | posttooluse hook, switch command |
| `target_project` | Project name for display | posttooluse hook |
| `active_project_path` | Legacy field, same as target | posttooluse hook (backwards compat) |
| `active_project` | Legacy project name | posttooluse hook (backwards compat) |
| `cwd` | User's current working directory | statusline |

**Priority for session recovery:**
1. `target_project_path` (check first)
2. `active_project_path` (fallback)
3. `active_project` + registry lookup (last resort)

---

## GSD Reference (Original Framework)

The original "get-shit-done" framework: https://github.com/glittercowboy/get-shit-done

**What we took from GSD:**
- Multi-phase project workflow concept
- STATE.md / ROADMAP.md / PLAN.md structure
- Verify-before-continue methodology
- Phase-based execution model

**What we changed:**
- Renamed `/gsd:*` → `/coder:*`
- Renamed paths `~/.claude/get-shit-done/` → `~/.claude/eri-rpg/`
- Added EriRPG CLI integration for state management
- Added hooks (sessionstart, posttooluse) for automatic state tracking
- Added `/eri:*` commands for lightweight CLI-based workflows
- Shared global state between both command families

**If you need GSD patterns:** Check the original repo for methodology reference, but use our `~/.claude/eri-rpg/` paths and `/coder:*` commands.

---

## 2026-02-03: Session Recovery Fix

### The Problem

After `/clear` or session compaction, system defaulted to wrong project.

**Example:** User edits `serenity/ui` files, runs `/clear`, then `/coder:init` shows `eri-rpg` instead of `serenity/ui`.

### Root Causes

1. **Variable shadowing in sessionstart.py:**
   ```python
   # BUG: project_path from function overwrites in loop
   project_path = get_active_project_info()  # Returns path
   for project_path in project_roots:        # Shadows it!
   ```

2. **Wrong state field priority:**
   ```python
   # BUG: Checked old field first
   state.get("active_project")  # Old field
   # SHOULD: Check new field first
   state.get("target_project_path")  # New field from hooks
   ```

3. **State not updating on project switch:**
   ```python
   # BUG: Only set on first edit
   if "target_project" not in state:
       state["target_project"] = ...

   # FIX: Always update
   state["target_project"] = project_name
   state["target_project_path"] = project_path
   ```

### The Fix

**`erirpg/hooks/sessionstart.py`:**
```python
def get_active_project_info() -> tuple:
    """Get active project name and path from global state.
    Checks multiple fields in order of priority:
    1. target_project_path - Set by coder:switch, most recent target
    2. active_project_path - Legacy field from coder system
    3. active_project - Project name lookup via registry
    """
    # Priority 1: target_project_path (set by switch command)
    target_path = state.get("target_project_path")
    if target_path and os.path.isdir(target_path):
        project_name = Path(target_path).name
        return project_name, target_path
    # ... fallbacks
```

**`erirpg/hooks/posttooluse.py`:**
```python
# Always update target_project to the project being edited
# This ensures /clear recovery finds the right project
state["target_project"] = project_name
state["target_project_path"] = project_path
# Legacy fields for backwards compat (same as target now)
state["active_project"] = project_name
state["active_project_path"] = project_path
```

### State Flow After Fix

```
User edits file in project
    ↓
PostToolUse hook fires
    ↓
Updates state.json:
  - target_project_path = /path/to/project
  - target_project = project_name
    ↓
User runs /clear (context wiped)
    ↓
User runs /coder:init or /eri:start
    ↓
SessionStart hook fires
    ↓
Reads state.json → target_project_path
    ↓
Shows correct project, not cwd
```

### Files Changed

| File | Change |
|------|--------|
| `erirpg/hooks/sessionstart.py` | Fixed `get_active_project_info()`, fixed variable shadowing |
| `erirpg/hooks/posttooluse.py` | Always update target_project fields |
| `erirpg/agents/eri-executor.md` | Removed GSD refs, updated paths |
| `erirpg/agents/eri-verifier.md` | Removed GSD refs |
| `erirpg/cli_commands/coder_cmds.py` | Added `get_current_position` helper |

### Commit

```
f19b9d6 fix(hooks): session recovery now remembers last project after /clear
```

**NOT PUSHED** - Changes are local only per user request.

---

## Critical Knowledge for Future Sessions

### Don't Break These

1. **State field priority** - Always check `target_project_path` before other fields
2. **PostToolUse updates** - Must always update state, not just on first edit
3. **Variable naming** - Don't use `project_path` as loop variable if function returns it
4. **Path validation** - Always check `os.path.isdir()` before using paths from state

### Testing Session Recovery

```bash
# 1. Edit a file in non-eri-rpg project
# (This triggers posttooluse hook)

# 2. Check state was updated
cat ~/.eri-rpg/state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('target_project_path'))"

# 3. Simulate /clear recovery
python3 -c "
import sys
sys.path.insert(0, '/home/alex/eri-rpg')
from erirpg.hooks.sessionstart import get_active_project_info
name, path = get_active_project_info()
print(f'Would recover to: {name} at {path}')
"
```

### Command Pattern Documentation

Full command architecture is documented at:
`~/.claude/eri-rpg/references/command-patterns.md`

Key principles:
- Commands are thin, workflows are thick
- Every state-changing command must update STATE.md
- Every completion must show prominent /clear instructions
- Global state must be updated for cross-session recovery

---

## 2026-02-03: Execute-Phase Completion Fix

### The Problem

After `/coder:execute-phase` completed, Claude said "ready when you are" instead of showing clear next steps. User had to prompt "is status.md updated? is commit?" to get proper completion.

### Root Cause

`erirpg/skills/execute-phase.md` was missing the `<completion>` section required by `command-patterns.md`. All state-changing commands MUST have:
1. Git status check (no uncommitted files)
2. STATE.md update with full context
3. Global state update
4. Prominent /clear box with exact next command

### The Fix

Added `<completion>` section to `execute-phase.md` following the pattern from `~/.claude/eri-rpg/references/command-patterns.md`.

### Key Principle

**Commands are thin, workflows are thick, completion is mandatory.**

Every state-changing command must end with:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:next-command {args}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Never say "ready when you are" - always show the explicit next command.

### Commit

```
ebe0089 fix(execute-phase): add mandatory completion section per command-patterns.md
```

---

## Glossary

| Term | Definition |
|------|------------|
| EriRPG | The CLI and framework we built |
| GSD | Original "get-shit-done" framework we forked ideas from |
| Coder workflow | Multi-phase project workflow (`/coder:*`) |
| Eri workflow | Lightweight CLI-based workflow (`/eri:*`) |
| Global state | `~/.eri-rpg/state.json` - tracks active project across sessions |
| Project state | `.planning/STATE.md` (coder) or `.eri-rpg/` (eri) |
| Hooks | Python scripts that run on session events (posttooluse, sessionstart) |
| PostToolUse | Hook that runs after any tool completes |
| SessionStart | Hook that runs at session start or after /clear |

---

## Locations Quick Reference

```
/home/alex/eri-rpg/               # Main repo
├── erirpg/
│   ├── hooks/
│   │   ├── sessionstart.py       # Session recovery hook
│   │   └── posttooluse.py        # State update hook
│   ├── cli_commands/
│   │   └── coder_cmds.py         # Coder CLI commands
│   └── agents/                   # Agent definitions
├── NOTES.md                      # This file
└── EMPOWERMENT.md                # AI partnership principles

~/.claude/
├── commands/
│   ├── coder/                    # /coder:* command files
│   └── eri/                      # /eri:* command files
└── eri-rpg/
    ├── workflows/                # Execution workflows
    ├── templates/                # Plan/summary templates
    └── references/               # Documentation (incl. command-patterns.md)

~/.eri-rpg/
├── state.json                    # Global state (CRITICAL)
└── registry.json                 # Project registry
```
