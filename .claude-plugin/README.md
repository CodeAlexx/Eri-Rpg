# EriRPG Plugin for Claude Code

Spec-driven development framework with verification.

## What This Provides

- **Workflow Commands**: `/coder:init`, `/coder:plan-phase`, `/coder:execute-phase`, `/coder:verify-work`
- **Session Hooks**: PreToolUse enforcement, SessionStart context recovery
- **Agent Specs**: Planner, Executor, Verifier, and more
- **Persistent Memory**: Knowledge survives `/clear` and session restarts

## Installation

See `INSTALL.md` for detailed instructions.

**Quick start:**

```bash
# 1. Install Python package
pip install -e /path/to/eri-rpg

# 2. Load plugin
claude --plugin-dir /path/to/eri-rpg/.claude-plugin
```

## Available Commands

| Command | Purpose |
|---------|---------|
| `/coder:init` | Recover session context |
| `/coder:plan-phase N` | Create plans for phase N |
| `/coder:execute-phase N` | Execute plans for phase N |
| `/coder:verify-work N` | Validate completed work |
| `/coder:discuss-phase N` | Capture decisions before planning |
| `/coder:add-feature` | Add feature to existing codebase |
| `/coder:doctor` | Diagnose workflow issues |
| `/coder:status` | Quick progress check |

## Hook Behavior

- **PreToolUse**: Enforces workflow - blocks edits outside active runs
- **SessionStart**: Loads project context automatically
- **PreCompact**: Preserves critical state during context compaction

## Requirements

- Python 3.10+
- Claude Code CLI
- `erirpg` package installed (`pip install -e .`)

## Architecture

```
.claude-plugin/
├── plugin.json      # Manifest
├── hooks/           # Bash wrappers → Python modules
├── skills/          # SKILL.md directory format
└── agents/          # Agent specifications
```

The plugin wraps the existing Python package. Hooks delegate to `python3 -m erirpg.hooks.*` modules.
