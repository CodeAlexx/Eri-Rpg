# EriRPG

**Spec-driven development toolkit for AI-assisted coding.**

EriRPG helps manage complex code changes by enforcing a structured workflow: learn → preflight → edit → verify. Originally designed for cross-project "transplants" (copying features between codebases), it now supports general development workflows.

## Status: Alpha (v0.1.0)

This is working software but has rough edges. See [Known Issues](#known-issues) below.

## What It Does

1. **Project Registry** - Register and index codebases (Python, Rust, C)
2. **Knowledge Storage** - Save learnings about modules to avoid re-reading code
3. **Preflight Checks** - Verify understanding before making changes
4. **Run Tracking** - Track multi-step changes with rollback capability
5. **Quick Fix Mode** - Lightweight single-file edits without full ceremony
6. **Claude Code Integration** - Hooks enforce workflow in AI coding sessions
7. **One-Command Install** - `eri-rpg install` sets up Claude Code integration

## Quick Start

```bash
# Install
pip install -e /path/to/eri-rpg

# Set up Claude Code integration (optional)
eri-rpg install

# Register a project
eri-rpg add myproject /path/to/project

# Index it (builds dependency graph)
eri-rpg index myproject

# Find modules
eri-rpg find myproject "loss calculation"

# Store learning after understanding a module
eri-rpg learn myproject src/utils.py -s "Utility functions" -p "String helpers and validators"

# Recall it later
eri-rpg recall myproject src/utils.py
```

## Core Commands

### Project Management
```bash
eri-rpg add <name> <path>      # Register project
eri-rpg remove <name>          # Unregister project
eri-rpg list                   # List registered projects
eri-rpg index <name>           # Build dependency graph
```

### Knowledge
```bash
eri-rpg learn <project> <file> # Store learning about a module
eri-rpg recall <project> <file> # Retrieve stored learning
eri-rpg knowledge <project>    # Show all learnings
eri-rpg relearn <project> <file> # Force re-read
```

### Search & Analysis
```bash
eri-rpg find <project> <query>  # Search modules
eri-rpg show <project>          # Show project structure
eri-rpg impact <project> <file> # Analyze change impact
```

### Quick Fix Mode (Lightweight)
```bash
eri-rpg quick <project> <file> "description"  # Start quick fix
eri-rpg quick-done <project>                  # Commit and complete
eri-rpg quick-cancel <project>                # Restore and abort
eri-rpg quick-status <project>                # Check status
```

### Run Management
```bash
eri-rpg runs <project>           # List runs
eri-rpg cleanup <project>        # Show stale runs
eri-rpg cleanup <project> --prune # Delete stale runs
eri-rpg rollback <project> <file> # Rollback changes
```

### Installation Management
```bash
eri-rpg install          # Install Claude Code commands and hooks
eri-rpg uninstall        # Remove from Claude Code
eri-rpg install-status   # Check installation status
```

## Real Example Output

```
$ eri-rpg list
eritrainer: /home/alex/OneTrainer/eritrainer (python, indexed (today))
onetrainer: /home/alex/OneTrainer/modules (python, indexed (today))
ai-toolkit: /home/alex/ai-toolkit (python, indexed (today))

$ eri-rpg find erirpg "agent"
Matching modules in erirpg:

  agent/__init__.py (0.63)
    EriRPG Agent API.
  agent/spec.py (0.49)
    Spec file parsing for agent-driven workflows.
  agent/run.py (0.11)
    Run state management.

$ eri-rpg install-status
EriRPG Installation Status:
  Commands: /eri:execute, /eri:quick, /eri:status
  Hooks: PreToolUse, PreCompact, SessionStart
```

## Claude Code Integration

EriRPG includes hooks for Claude Code that:

1. **PreToolUse** - Blocks Edit/Write without active preflight or quick fix
2. **PreCompact** - Saves state before context compaction
3. **SessionStart** - Reminds about incomplete runs

### Quick Setup

```bash
eri-rpg install
```

This automatically:
- Installs `/eri:*` slash commands
- Configures hooks in `~/.claude/settings.json`
- Sets up enforcement for Edit/Write/MultiEdit tools

To remove:
```bash
eri-rpg uninstall
```

See [docs/CLAUDE_CODE.md](docs/CLAUDE_CODE.md) for manual setup.

## Known Issues

### Working
- ✅ Project registration and indexing
- ✅ Module search (`find`)
- ✅ Learning storage and recall (v2 knowledge)
- ✅ Quick fix mode (single-file edits)
- ✅ Cleanup command (list/prune stale runs)
- ✅ Basic rollback functionality
- ✅ PreToolUse hook enforcement
- ✅ One-command installer (`eri-rpg install`)
- ✅ Python parser
- ✅ Rust parser (basic)
- ✅ C parser (basic)

### Partially Working
- ⚠️ Full agent workflow (Agent.from_goal) - works but complex
- ⚠️ Verification gating - implemented but not all projects have configs
- ⚠️ Take/transplant mode - needs more testing
- ⚠️ Context generation - works but token estimates may be off

### Not Working / Incomplete
- ❌ `hooks.py` shadows `hooks/` directory (module import conflict)
- ❌ Auto-learning sometimes fails on complex files
- ❌ MCP server not implemented
- ❌ Batch learn mode (`--batch` flag) not implemented
- ❌ Some CLI commands are stubs from original design

### Known Bugs
- Path normalization issues with nested `.eri-rpg` directories
- Preflight state can get stale if session crashes

## Architecture

```
erirpg/
├── cli.py           # All CLI commands
├── registry.py      # Project registry
├── indexer.py       # Code indexing
├── graph.py         # Dependency graph
├── memory.py        # Knowledge storage (v2)
├── preflight.py     # Preflight checks
├── verification.py  # Test running
├── quick.py         # Quick fix mode
├── install.py       # Claude Code installer
├── agent/           # Agent API
│   ├── __init__.py  # Main Agent class
│   ├── run.py       # Run state
│   ├── plan.py      # Plan generation
│   └── learner.py   # Auto-learning
├── hooks/           # Claude Code hooks
│   ├── pretooluse.py
│   ├── precompact.py
│   └── sessionstart.py
├── parsers/         # Language parsers
│   ├── python.py
│   ├── rust.py
│   └── c.py
└── modes/           # High-level workflows
    ├── take.py      # Transplant mode
    ├── work.py      # Modify mode
    └── new.py       # New project mode
```

## Requirements

- Python 3.10+
- click
- pyyaml

Optional:
- pytest (for verification)
- ruff (for linting)

## License

MIT

## Contributing

This is a personal project. Issues and PRs welcome but response time may vary.
