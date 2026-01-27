# EriRPG Project Planning

## Vision

A spec-driven development toolkit that enforces structured workflows for AI-assisted coding. Originally designed for cross-project "transplants" (copying features between codebases), evolved into a general-purpose workflow enforcement system.

## Core Problem

AI coding assistants (Claude Code, Copilot, etc.) make changes without tracking what they did, why, or how to undo it. This leads to:
- "What did I change?" confusion
- Lost context after session ends
- No rollback capability
- Re-reading the same code repeatedly
- Unverified changes breaking things

## Solution

Enforce a structured workflow:
```
Goal → Discuss → Spec → Preflight → Edit → Verify → Learn
```

Every code change goes through this pipeline. No exceptions.

## Design Principles

1. **Enforcement over suggestion** - Block bad behavior, don't just warn
2. **Spec-driven** - Human writes what, agent figures out how
3. **Knowledge retention** - Learn once, recall forever
4. **Safe by default** - Preflight required, rollback available
5. **Verification built-in** - Tests run automatically
6. **Claude Code native** - Hooks integrate seamlessly

## Project Phases

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 01 | Core Infrastructure | Done | Registry, indexing, parsers |
| 02 | Knowledge System | Done | Memory, learning, staleness |
| 03 | Agent Workflow | Done | Specs, plans, runs, preflight |
| 04 | Quick Fix Mode | Done | Lightweight single-file edits |
| 05 | Discuss & Roadmap | Done | Goal clarification, phased planning |
| 06 | Claude Integration | Done | Hooks, installer, commands |

## Tech Stack

- **Language**: Python 3.10+
- **CLI**: Click
- **Config**: YAML
- **Storage**: JSON files in `.eri-rpg/`
- **Testing**: pytest
- **Target**: Claude Code (Anthropic CLI)

## Key Files

```
erirpg/
├── cli.py           # All CLI commands
├── registry.py      # Project registry
├── indexer.py       # Code indexing
├── graph.py         # Dependency graph
├── memory.py        # Knowledge storage
├── preflight.py     # Preflight checks
├── verification.py  # Test running
├── quick.py         # Quick fix mode
├── discuss.py       # Discussion mode
├── spec.py          # Spec definitions
├── install.py       # Claude Code installer
├── agent/           # Agent API
└── hooks/           # Claude Code hooks
```

## Success Metrics

- Zero untracked file edits during enforced sessions
- Knowledge recall accuracy > 95%
- Rollback success rate > 99%
- Test verification catches > 80% of regressions
