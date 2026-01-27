# Phase 06: Features

## PreToolUse Hook

Runs before every Edit/Write/MultiEdit tool call.

### Behavior
```
Edit tool called
       │
       ▼
┌─────────────────────┐
│ Is quick fix active │──Yes──► Is this the quick fix file?
│ for this project?   │              │
└─────────────────────┘         Yes ─┼─► ALLOW
       │ No                     No ──┼─► BLOCK
       ▼                             │
┌─────────────────────┐              │
│ Is preflight done   │──────────────┘
│ for this file?      │
└─────────────────────┘
       │
  Yes ─┼─► ALLOW
  No ──┼─► BLOCK with instructions
```

### Output Format
```json
{
  "decision": "block",
  "reason": "ERI-RPG ENFORCEMENT: Preflight required",
  "instructions": "Run: agent.preflight(['file.py'], 'modify')"
}
```

## PreCompact Hook

Runs before Claude Code compacts context.

### Behavior
- Saves current run state to disk
- Logs context size metrics
- Ensures no data lost on compaction

### Output
```json
{
  "message": "EriRPG state saved before compaction",
  "run_id": "abc123",
  "step": "implement"
}
```

## SessionStart Hook

Runs when Claude Code session starts.

### Behavior
- Checks for incomplete runs
- Reminds user if active run exists
- Shows resume instructions

### Output
```
╔══════════════════════════════════════════════════════╗
║  ERI-RPG: Incomplete run detected                    ║
╠══════════════════════════════════════════════════════╣
║  Run: abc123                                         ║
║  Goal: Add user authentication                       ║
║  Progress: 2/4 steps                                 ║
║                                                      ║
║  Resume with: agent = Agent.resume(project_path)    ║
╚══════════════════════════════════════════════════════╝
```

## Installer

### Install
```bash
eri-rpg install
```

Does:
1. Creates `.claude/commands/eri/` directory
2. Copies slash command files
3. Updates `~/.claude/settings.json` with hook configs
4. Sets `ERIRPG_ROOT` in shell profile

### Uninstall
```bash
eri-rpg uninstall
```

Removes commands and hook configs.

### Status Check
```bash
eri-rpg install-status
```

Shows:
```
EriRPG Installation Status:
  Commands: /eri:execute, /eri:start, /eri:guard, /eri:status
  Hooks: PreToolUse ✓, PreCompact ✓, SessionStart ✓
  Environment: ERIRPG_ROOT=/path/to/eri-rpg
```

## Slash Commands

### /eri:execute
Full agent execution loop with enforcement.

### /eri:start
Initialize enforcement at session start.

### /eri:guard
Intercept all file edits (hard mode).

### /eri:status
Show current run status and progress.
