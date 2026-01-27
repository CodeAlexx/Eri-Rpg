# Changelog

## v2.0.0 (2026-01-26)

Major feature release adding discussion mode, roadmaps, and run summaries.

### New Features

**Discuss Mode**
- `eri-rpg discuss` - Start goal clarification before spec generation
- `eri-rpg discuss-answer` - Answer clarifying questions
- `eri-rpg discuss-show` - View current discussion
- `eri-rpg discuss-resolve` - Mark discussion complete
- `eri-rpg discuss-clear` - Clear discussion
- Auto-detects vague goals and new projects that need discussion
- Questions generated based on goal type (add, fix, refactor, transplant)

**Roadmaps**
- `eri-rpg roadmap` - View project roadmap
- `eri-rpg roadmap-add` - Add milestone/phase
- `eri-rpg roadmap-next` - Advance to next phase
- `eri-rpg roadmap-edit` - Edit existing milestone
- Milestones track: name, description, spec_id, run_id, done status
- Progress tracking with percentage complete

**Spec Verification (must_haves)**
- `truths` - Grep-based assertions that must be true
- `artifacts` - Files that must exist with expected exports
- `key_links` - Import patterns between files
- `Spec.verify_must_haves()` - Verify all requirements after run
- New dataclasses: `Artifact`, `KeyLink`, `MustHaves`

**Run Summaries**
- `agent.add_decision()` - Record decisions during execution
- `agent.generate_summary()` - Generate run summary
- `Decision` dataclass - id, decision, rationale, step_id, timestamp
- `RunSummary` dataclass - one_liner, decisions, artifacts_created, duration
- Decisions tracked in run state and persisted

### Improvements

- Discussion enriches goals with context for better specs
- Roadmap milestones can be linked to specs and runs
- Full serialization support for all new dataclasses
- Agent API methods delegate to RunState for clean separation

### Internal Changes

- Added `discuss.py` module for discussion mode
- Extended `memory.py` with Discussion, Milestone, Roadmap classes
- Extended `spec.py` with MustHaves, Artifact, KeyLink classes
- Extended `agent/run.py` with Decision, RunSummary classes
- Updated `agent/__init__.py` with new public methods

---

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
- Spec-driven execution with Agent API
- Preflight enforcement
- Auto-learn on step completion

**Claude Code Integration**
- PreToolUse hook (blocks unauthorized edits)
- PreCompact hook (saves state before compaction)
- SessionStart hook (reminds about incomplete runs)
- One-command installer (`eri-rpg install`)
- Slash commands (/eri:execute, /eri:start, /eri:guard, /eri:status)

### Known Issues

- `hooks.py` shadows `hooks/` directory (module import conflict)
- Auto-learning sometimes fails on complex files
- Path normalization issues with nested `.eri-rpg` directories
- Preflight state can get stale if session crashes
