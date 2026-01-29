# EriRPG Internals

How things work together. Read this to understand the system.

## Architecture Overview

```
User → Slash Command → Claude → CLI → State Files
                         ↓
                    Hooks (PreToolUse)
                         ↓
                    Status Line
```

## The Core Loop

1. User types `/eri:something` (slash command)
2. Slash command file tells Claude what CLI to run
3. Claude runs `python3 -m erirpg.cli <command>`
4. CLI updates state files
5. Hooks run on every tool use (persona detection, enforcement)
6. Status line reads state and displays

## Key Principle

**Users talk to Claude. Claude talks to CLI.**

Users never need to know CLI commands. They use slash commands. Claude executes the CLI internally.

## State Flow

### Global State (~/.eri-rpg/state.json)
```json
{
  "active_project": "project-name",
  "phase": "idle|planning|implementing|verifying",
  "persona": "analyzer|backend|frontend|...",
  "persona_auto": true,
  "debug_session": { ... }
}
```

### Project Config (.eri-rpg/config.json)
```json
{
  "tier": "lite|standard|full",
  "mode": "bootstrap|maintain",
  "known_externals": ["diffusers", ...]
}
```

## Hook System

Hooks run automatically via Claude Code's hook system.

### Installation Location
`~/.claude/settings.json` → hooks section

### Hook Flow
```
Tool Call → PreToolUse Hook → (allow/block) → Tool Executes
```

### Persona Detection Hook
- Runs on EVERY tool use (matcher: ".*")
- Detects persona from tool name + file patterns
- Updates state.json
- Never blocks

### Enforcement Hook
- Runs on Edit|Write|Bash
- Checks if operation is allowed
- Can block with error message

## Status Line

`~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /home/alex/eri-rpg/erirpg/statusline.py"
  }
}
```

Reads from:
- `~/.eri-rpg/state.json` (persona, phase)
- `~/.eri-rpg/registry.json` (active project)
- `.eri-rpg/config.json` (tier)
- Git (branch)

## Slash Commands

Located: `~/.claude/commands/eri/*.md`

Format:
```markdown
# /eri:command - Description

## Usage
...

## Action
```bash
python3 -m erirpg.cli <actual-command>
```
```

## CLI Structure

```
erirpg/
├── cli.py              # Main CLI entry
├── cli_commands/       # All command modules
│   ├── __init__.py     # Registers all commands
│   ├── debug_cmd.py    # /eri:debug
│   ├── persona_cmd.py  # /eri:persona
│   ├── quick.py        # /eri:quick
│   └── ...
├── hooks/              # Claude Code hooks
│   ├── persona_detect.py
│   ├── pretooluse.py
│   └── ...
├── statusline.py       # Status line output
├── storage.py          # SQLite backend
└── registry.py         # Project registry
```

## Adding a New Feature

1. Create CLI command in `erirpg/cli_commands/`
2. Register in `erirpg/cli_commands/__init__.py`
3. Create slash command in `~/.claude/commands/eri/`
4. Update STATUS.md
5. Update docs/MANUAL.md if user-facing
6. Update docs/CHANGELOG.md

## Testing

```bash
# Test CLI directly
python3 -m erirpg.cli <command>

# Test status line
python3 /home/alex/eri-rpg/erirpg/statusline.py

# Check state
cat ~/.eri-rpg/state.json
```

## Common Debugging

### Persona not updating
1. Check hook is installed: `cat ~/.claude/settings.json | grep persona_detect`
2. Check state: `cat ~/.eri-rpg/state.json`
3. Enable debug: `ERIRPG_PERSONA_DEBUG=1` then check `/tmp/erirpg-persona.log`

### Status line wrong
1. Run directly: `python3 /path/to/statusline.py`
2. Check it reads correct files
3. Check state.json has expected values

### Slash command not working
1. Check file exists: `ls ~/.claude/commands/eri/`
2. Check format has `## Action` with CLI command
3. Test CLI directly: `python3 -m erirpg.cli <command>`
