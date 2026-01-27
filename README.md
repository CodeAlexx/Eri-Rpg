# EriRPG

**Spec-driven development toolkit for AI-assisted coding.**

EriRPG helps manage complex code changes by enforcing a structured workflow: discuss → plan → learn → preflight → edit → verify. Originally designed for cross-project "transplants" (copying features between codebases), it now supports general development workflows.

## Status: v2.0

Production-ready for personal use. See [docs/MANUAL.md](docs/MANUAL.md) for complete documentation.

## What It Does

1. **Discussion Mode** - Clarify vague goals with structured Q&A before planning
2. **Roadmap Planning** - Break large goals into phased milestones
3. **Project Registry** - Register and index codebases (Python, Rust, C, Dart)
4. **Knowledge Storage** - Save learnings about modules to avoid re-reading code
5. **Preflight Checks** - Verify understanding before making changes
6. **Run Tracking** - Track multi-step changes with rollback capability
7. **Run Summaries** - Track decisions and generate summaries of completed runs
8. **Quick Fix Mode** - Lightweight single-file edits without full ceremony
9. **Claude Code Integration** - Hooks enforce workflow in AI coding sessions
10. **Multi-Agent Configuration** - Toggle parallel execution and subagent delegation

## Quick Start

```bash
# Install
pip install -e /path/to/eri-rpg

# Set up Claude Code integration
eri-rpg install

# Register a project
eri-rpg add myproject /path/to/project

# Index it (builds dependency graph)
eri-rpg index myproject

# Start a discussion for a vague goal
eri-rpg discuss myproject "improve the caching system"

# Or generate a spec directly for a clear goal
eri-rpg goal-plan myproject "add retry logic to api.py"

# Start the run
eri-rpg goal-run myproject
```

## Core Commands

### Project Management
```bash
eri-rpg add <name> <path>      # Register project
eri-rpg remove <name>          # Unregister project
eri-rpg list                   # List registered projects
eri-rpg index <name>           # Build dependency graph
```

### Discussion & Planning
```bash
eri-rpg discuss <project> "<goal>"        # Start discussion for vague goal
eri-rpg discuss-answer <project> <n> "answer"  # Answer question N
eri-rpg discuss-resolve <project>         # Mark discussion complete
eri-rpg roadmap-add <project> "Phase" "Description"  # Add milestone
eri-rpg roadmap <project>                 # Show roadmap progress
```

### Knowledge
```bash
eri-rpg learn <project> <file>  # Store learning about a module
eri-rpg recall <project> <file> # Retrieve stored learning
eri-rpg knowledge <project>     # Show all learnings
eri-rpg relearn <project> <file> # Force re-read
```

### Search & Analysis
```bash
eri-rpg find <project> <query>  # Search modules
eri-rpg show <project>          # Show project structure
eri-rpg impact <project> <file> # Analyze change impact
```

### Run Management
```bash
eri-rpg goal-plan <project> "<goal>"  # Generate spec from goal
eri-rpg goal-run <project>            # Start/resume run
eri-rpg runs <project>                # List runs
eri-rpg cleanup <project>             # Show stale runs
eri-rpg cleanup <project> --prune     # Delete stale runs
eri-rpg rollback <project> <file>     # Rollback changes
```

### Quick Fix Mode
```bash
eri-rpg quick <project> <file> "description"  # Start quick fix
eri-rpg quick-done <project>                  # Commit and complete
eri-rpg quick-cancel <project>                # Restore and abort
eri-rpg quick-status <project>                # Check status
```

### Installation
```bash
eri-rpg install          # Install Claude Code commands and hooks
eri-rpg uninstall        # Remove from Claude Code
eri-rpg install-status   # Check installation status
```

### Configuration
```bash
eri-rpg config <project> --show           # Show current settings
eri-rpg config <project> --multi-agent on # Enable multi-agent mode
eri-rpg config <project> --concurrency 5  # Set max concurrent agents
```

## Claude Code Integration

EriRPG includes hooks for Claude Code that:

1. **PreToolUse** - Blocks Edit/Write without active preflight or quick fix
2. **PreCompact** - Saves state before context compaction
3. **SessionStart** - Reminds about incomplete runs

### Slash Commands

After `eri-rpg install`:

- `/eri:start` - Initialize EriRPG for a coding session
- `/eri:execute` - Run the full agent workflow
- `/eri:guard` - Check if edits are allowed
- `/eri:status` - Show current run status

## Example Session

```
$ eri-rpg discuss myproject "improve performance"
Discussion started: d8f3a2b1

Questions:
  ○ 1. What specific aspect should be improved?
  ○ 2. Are there constraints (backwards compatibility, etc.)?
  ○ 3. What's the success criteria for this refactor?

$ eri-rpg discuss-answer myproject 1 "Database queries are slow"
$ eri-rpg discuss-answer myproject 2 "Must maintain API compatibility"
$ eri-rpg discuss-answer myproject 3 "Query times under 100ms"

$ eri-rpg roadmap-add myproject "Profile" "Identify slow queries"
$ eri-rpg roadmap-add myproject "Optimize" "Add indexes and caching"
$ eri-rpg roadmap-add myproject "Verify" "Benchmark improvements"

$ eri-rpg discuss-resolve myproject
Discussion resolved. Ready for: eri-rpg goal-plan myproject
```

## Architecture

```
erirpg/
├── cli.py           # All CLI commands
├── registry.py      # Project registry
├── indexer.py       # Code indexing
├── graph.py         # Dependency graph
├── memory.py        # Knowledge storage (v2)
├── discuss.py       # Discussion mode & roadmaps
├── preflight.py     # Preflight checks
├── verification.py  # Test running
├── quick.py         # Quick fix mode
├── install.py       # Claude Code installer
├── config.py        # Project configuration
├── write_guard.py   # Write interception (enforcement)
├── agent/           # Agent API
│   ├── __init__.py  # Main Agent class
│   ├── run.py       # Run state, Decision, RunSummary
│   ├── plan.py      # Plan generation
│   ├── spec.py      # Spec parsing
│   └── learner.py   # Auto-learning
├── hooks/           # Claude Code hooks
│   ├── pretooluse.py
│   ├── precompact.py
│   └── sessionstart.py
├── parsers/         # Language parsers
│   ├── python.py    # AST-based
│   ├── rust.py      # Regex-based
│   ├── c.py         # Regex-based
│   └── dart.py      # Regex-based
└── modes/           # High-level workflows
    ├── take.py      # Transplant mode
    ├── work.py      # Modify mode
    └── new.py       # New project mode
```

## Language Support

| Language | Parser | Status |
|----------|--------|--------|
| Python | AST-based | Full support |
| Rust | Regex | Basic support |
| C/C++ | Regex | Basic support |
| Dart | Regex | Full support |

## Requirements

- Python 3.10+
- click
- pyyaml

Optional:
- pytest (for verification)
- ruff (for linting)

## Documentation

- [docs/MANUAL.md](docs/MANUAL.md) - Complete user manual
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - Version history
- [DESIGN.md](DESIGN.md) - Technical design document
- [.planning/](.planning/) - Development roadmap and phase documentation

## License

MIT

## Contributing

This is a personal project. Issues and PRs welcome but response time may vary.

## Status Details

### Working
- ✅ Project registration and indexing
- ✅ Module search (`find`)
- ✅ Learning storage and recall (v2 knowledge)
- ✅ Quick fix mode (single-file edits)
- ✅ Cleanup command (list/prune stale runs)
- ✅ Basic rollback functionality
- ✅ PreToolUse hook enforcement
- ✅ One-command installer (`eri-rpg install`)
- ✅ Discussion mode with Q&A
- ✅ Roadmap/milestone tracking
- ✅ Run summaries with decision tracking
- ✅ Python parser (AST-based)
- ✅ Rust parser (regex)
- ✅ C parser (regex)
- ✅ Dart parser (regex)

### Partially Working
- ⚠️ Take/transplant mode - works but needs more testing
- ⚠️ Context generation - works but token estimates may be off
- ⚠️ Multi-agent mode - config added, parallel execution in progress

### Not Implemented
- ❌ MCP server
- ❌ Batch learn mode (`--batch` flag)
- ❌ Wave execution (parallel steps)

### Fixed in v2.0
- ~~`hooks.py` shadows `hooks/` directory~~ → Renamed to `write_guard.py`
- ~~Agent workflow too complex~~ → Streamlined with `goal-plan`/`goal-run`
- ~~No goal clarification~~ → Added discussion mode
