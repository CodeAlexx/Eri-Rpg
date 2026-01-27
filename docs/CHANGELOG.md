# Changelog

## v0.1.0 (2026-01-26)

Initial release.

### Features

**Core**
- Project registry (add, remove, list)
- Code indexing with dependency graph
- Support for Python, Rust, C parsing
- Module search (find command)
- Impact analysis

**Knowledge Management**
- Learn command with summary, purpose, key functions, gotchas
- Recall command to retrieve learnings
- Version history for learnings
- Rollback to previous versions (learning and code)
- Staleness detection (file changed since last learn)

**Quick Fix Mode**
- Lightweight single-file edits
- Automatic snapshots
- Auto-commit on completion
- Cancel and restore

**Run Management**
- Run state tracking for multi-step workflows
- Progress tracking (steps completed/total)
- Cleanup command for stale runs
- List runs command

**Agent API**
- `Agent.from_goal()` - create from goal string
- `Agent.resume()` - resume incomplete run
- Preflight checks (required before edits)
- `edit_file()` and `write_file()` methods
- `complete_step()` with automatic verification
- Automatic learning after steps

**Verification**
- Integration with pytest (Python projects)
- Integration with npm test (Node projects)
- Custom verification via `.eri-rpg/verification.json`
- Verification gating (step fails if tests fail)

**Claude Code Integration**
- PreToolUse hook (blocks unauthorized edits)
- PreCompact hook (saves state before compaction)
- SessionStart hook (reminds about incomplete runs)
- Plugin structure with slash commands

### Known Issues

- `hooks.py` shadows `hooks/` directory (module import conflict)
- Path normalization issues with nested `.eri-rpg` directories
- Some CLI commands are stubs from original design
- MCP server not implemented
- Batch learn mode not implemented

### Internal

- ~3000 lines in cli.py
- ~1600 lines in agent/__init__.py
- ~1000 lines in memory.py
- Python 3.10+ required

## Planned

Future versions may include:

- [ ] MCP server for direct Claude integration
- [ ] Batch learn mode (`--batch` flag)
- [ ] Better error messages
- [ ] More language parsers
- [ ] Performance improvements for large codebases
- [ ] Web UI for knowledge browsing
