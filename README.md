# EriRPG

**Make Claude better at complex code changes.**

EriRPG gives Claude a structured workflow and persistent memory. You talk to Claude, Claude uses EriRPG internally to track specs, remember code, verify changes, and avoid mistakes.

## Why?

Without EriRPG, Claude:
- Re-reads the same files repeatedly (wastes tokens)
- Forgets decisions from earlier in the session
- Makes changes without verifying they work
- Gets confused on multi-step tasks

With EriRPG, Claude:
- Stores knowledge about modules and recalls it instantly
- Tracks decisions and context across sessions
- Verifies changes before marking complete
- Follows a structured workflow: discuss → plan → implement → verify

## Setup (5 minutes)

```bash
# Install
pip install -e /path/to/eri-rpg

# Register your project
eri-rpg add myproject /path/to/project

# Install Claude Code integration
eri-rpg install
```

That's it. Now use Claude Code normally.

## Usage

Talk to Claude using slash commands:

| Command | What it does |
|---------|--------------|
| `/eri:start` | Begin a coding session |
| `/eri:execute "add auth"` | Execute a goal with full workflow |
| `/eri:quick file.py "fix bug"` | Quick single-file edit |
| `/eri:status` | Check current state |
| `/eri:recall auth` | Get Claude's stored knowledge |
| `/eri:resume` | Continue from last session |

### Example

```
You: /eri:start
You: Add retry logic to the API client

Claude: [Internally runs eri-rpg commands to:]
  - Check what it knows about the API client
  - Create a plan
  - Make edits with verification
  - Track the decision for future sessions
```

You describe what you want. Claude handles the workflow.

## Tiers

| Tier | What Claude can do |
|------|-------------------|
| **lite** | Quick fixes, search, cross-project queries |
| **standard** | + Discussion mode, goal clarification |
| **full** | + Full agent runs, specs, verification |

Default is `lite`. Upgrade with: `eri-rpg mode myproject --standard`

## Project Management

These are the only CLI commands you need to run directly:

```bash
eri-rpg add <name> <path>    # Register a project
eri-rpg remove <name>        # Unregister
eri-rpg list                 # Show registered projects
eri-rpg install              # Set up Claude Code hooks
eri-rpg install-status       # Check installation
```

Everything else? Claude handles it.

## How It Works

```
┌─────────┐     slash commands      ┌─────────┐
│   You   │ ───────────────────────▶│  Claude │
└─────────┘                         └────┬────┘
                                         │
                                         │ CLI calls
                                         ▼
                                    ┌─────────┐
                                    │ EriRPG  │
                                    │   CLI   │
                                    └────┬────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              ┌──────────┐        ┌──────────┐        ┌──────────┐
              │ Knowledge│        │  Specs   │        │  Verify  │
              │  Graph   │        │ & Plans  │        │  Tests   │
              └──────────┘        └──────────┘        └──────────┘
```

EriRPG stores:
- **Knowledge graph** - What Claude learned about your code
- **Specs & plans** - Goals broken into steps
- **Decisions** - Why Claude made certain choices
- **Run state** - Progress on multi-step tasks

This persists across sessions. Claude resumes where it left off.

## Language Support

| Language | Support |
|----------|---------|
| Python | Full (AST-based) |
| Rust | Basic (regex) |
| C/C++ | Basic (regex) |
| Dart | Full (regex) |

## Requirements

- Python 3.10+
- Claude Code (CLI)

## Documentation

- [docs/MANUAL.md](docs/MANUAL.md) - Complete reference
- [DESIGN.md](DESIGN.md) - Technical architecture

## Status

Production-ready for personal use. v2.0.

### Working
- ✅ Knowledge storage and recall
- ✅ Cross-project search (<1ms queries)
- ✅ Quick fix mode
- ✅ Discussion mode
- ✅ Run tracking with decisions
- ✅ Claude Code hooks

### In Progress
- ⚠️ Multi-agent parallel execution
- ⚠️ Transplant mode (copy features between projects)

## License

MIT
