# EriRPG Status

**Version**: 0.56.0-alpha
**Last Updated**: 2026-01-29

## Feature Status

### Core Features (Working)
| Feature | Status | Files |
|---------|--------|-------|
| Registry | ✅ | `erirpg/registry.py` |
| Knowledge graph | ✅ | `erirpg/knowledge.py`, `.eri-rpg/knowledge.json` |
| SQLite storage | ✅ | `erirpg/storage.py`, `~/.eri-rpg/erirpg.db` |
| Quick mode | ✅ | `erirpg/cli_commands/quick.py` |
| Execute mode | ✅ | `erirpg/cli_commands/modes.py` |
| Verification | ✅ | `erirpg/cli_commands/verify_group.py` |

### Persona System (Working)
| Feature | Status | Files |
|---------|--------|-------|
| Auto-detection hook | ✅ | `erirpg/hooks/persona_detect.py` |
| Status line display | ✅ | `erirpg/statusline.py` |
| Debug persona/triage | ✅ | `erirpg/cli_commands/debug_cmd.py` |
| Manual set-persona | ✅ | `erirpg/cli_commands/persona_cmd.py` |

### Hooks (Installed in ~/.claude/settings.json)
| Hook | Purpose | File |
|------|---------|------|
| PreToolUse (.*) | Persona auto-detection | `erirpg/hooks/persona_detect.py` |
| PreToolUse (Edit\|Write\|Bash) | Enforcement | `erirpg/hooks/pretooluse.py` |
| PreCompact | Save context before compaction | `erirpg/hooks/precompact.py` |
| SessionStart | Initialize session | `erirpg/hooks/sessionstart.py` |

## State Files

### Global (~/.eri-rpg/)
| File | Purpose |
|------|---------|
| `state.json` | Active project, phase, persona, debug_session |
| `registry.json` | All registered projects |
| `erirpg.db` | SQLite knowledge storage |

### Per-Project (.eri-rpg/)
| File | Purpose |
|------|---------|
| `config.json` | Tier, mode, known_externals |
| `knowledge.json` | Module learnings |
| `graph.json` | Dependency graph |
| `runs/` | Execution run history |

## Status Line Format

```
📁 project | 📍 phase | 🎭 persona | 🔄 context%
🌿 branch | ⚡ tier
```

Source: `erirpg/statusline.py`
Config: `~/.claude/settings.json` → statusLine.command

## Persona Auto-Detection Rules

| Tool | File Pattern | Detected Persona |
|------|--------------|------------------|
| Read, Grep, Glob | any | analyzer |
| Edit, Write | .py, .js, .ts, .go, .rs | backend |
| Edit, Write | .jsx, .tsx, .vue, .css | frontend |
| Edit, Write | .md, /docs/, readme | scribe |
| Edit, Write | auth, security, crypto | security |
| Bash | pytest, jest, test | qa |
| Bash | git | devops |
| Bash | docker, kubectl, deploy | devops |
| Bash | ruff, eslint, black | refactorer |
| Task | any | architect |
| WebSearch, WebFetch | any | analyzer |

Source: `erirpg/hooks/persona_detect.py`

## Debug Session

`/eri:debug "problem"` stores:
```json
{
  "debug_session": {
    "active": true,
    "description": "problem description",
    "externals": ["detected", "tools"],
    "started": "ISO timestamp"
  }
}
```

Does NOT lock persona - auto-detection continues.

Known externals configured per-project in `.eri-rpg/config.json`:
```json
{
  "known_externals": ["diffusers", "pytorch", ...]
}
```

Defaults: onetrainer, simpletuner, ai-toolkit, kohya, diffusers, transformers, accelerate, pytorch, torch

## Slash Commands (User-Facing)

Located in `~/.claude/commands/eri/`

| Command | CLI Backend |
|---------|-------------|
| `/eri:debug` | `python3 -m erirpg.cli debug` |
| `/eri:persona` | `python3 -m erirpg.cli set-persona` |
| `/eri:execute` | `python3 -m erirpg.cli execute` |
| `/eri:quick` | `python3 -m erirpg.cli quick` |
| `/eri:status` | `python3 -m erirpg.cli status` |

## Known Issues

- None currently tracked

## Recent Changes (v0.56)

1. Debug persona with triage-first approach
2. Persona auto-detection from tool usage
3. Two-line status line with all info
4. Debug session stored separately from persona
5. known_externals configurable per project
