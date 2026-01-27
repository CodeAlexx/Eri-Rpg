# EriRPG Changes Log

All changes since January 26, 2026 (v2.0 development sprint).

---

## January 27, 2026

### GSD-Inspired Features (commit `269b019`)

Major feature addition inspired by GSD (Get Shit Done) tool:

**New Classes (memory.py):**
- `Decision` - Track choices with context, rationale, alternatives, source
- `DeferredIdea` - Capture "v2/later" ideas with tags and promotion tracking
- `SessionState` - Rich session state for handoff between sessions
- `Blocker` - Track blockers preventing progress
- `Gap` - Analyze verification failures

**New Functions (discuss.py):**
- `detect_domain()` - Identify domain from goal (ui, api, cli, data, backend, testing)
- `get_gray_area_questions()` - Domain-specific clarifying questions
- `log_decision()` - Log a decision with full context
- `defer_idea()` - Capture deferred ideas
- `get_decisions()` - Query logged decisions
- `get_deferred_ideas()` - Query deferred ideas
- `answer_question_with_logging()` - Auto-detect deferred ideas in answers
- `promote_idea_to_milestone()` - Convert deferred idea to roadmap milestone

**New CLI Commands:**
| Command | Description |
|---------|-------------|
| `log-decision <project> <context> <choice> <rationale>` | Log a decision with full rationale |
| `list-decisions <project> [--search] [--limit]` | List recent decisions |
| `defer <project> <idea> [--tags]` | Capture a deferred idea |
| `deferred <project> [--tag] [--all]` | List deferred ideas |
| `promote <project> <idea_id> [--goal]` | Promote idea to milestone |
| `session <project>` | Show current session state |
| `handoff <project>` | Generate session handoff summary |
| `gaps <project>` | View verification gaps |

**KnowledgeStore v2.2.0:**
- Added `user_decisions` field
- Added `deferred_ideas` field
- Added CRUD methods for new data types

### Hook Fix (commit `9ce5ee4`)

Fixed nested `.eri-rpg` directory detection in pretooluse hook:
- Stops searching at home directory (not a valid project root)
- Finds ALL `.eri-rpg` directories between file and home
- Prefers paths with `quick_fix_state.json` for active quick fixes
- Falls back to outermost `.eri-rpg` (closest to home = project root)

### Performance Optimization (commit `4989feb`)

Graph algorithms optimized from O(n^2) to O(n):
- `topo_sort()`: Use `deque.popleft()` instead of `list.pop(0)`
- `get_dependents()`: O(1) via pre-built `_dependents_index`
- `get_transitive_deps()`: Added LRU cache (maxsize=512)
- New `clear_caches()` method for cache invalidation

Expected speedup: 5-10x for projects with 100+ modules.

### Silent Exception Fix (commit `b9e22a7`)

Fixed 46 silent exception handlers across 19 files:
- Changed `except Exception:` to `except Exception as e:`
- All failures now print `[EriRPG] <error>` to stderr
- Critical for debugging daily driver usage

Files fixed: memory.py, hooks/pretooluse.py, hooks/sessionstart.py, hooks/precompact.py, cli.py, quick.py, agent/__init__.py, agent/learner.py, agent/run.py, modes/work.py, modes/take.py, install.py, specs.py, ops.py, context.py, parsers/python.py, verification.py, preflight.py, write_guard.py

---

## January 26, 2026

### Multi-Agent Configuration (commits `4288328`, `304cefa`, `348a67d`)

**New Module (config.py):**
- `MultiAgentConfig` dataclass - Control parallel execution
- `ProjectConfig` dataclass - Project-level settings

**New CLI Command:**
| Command | Description |
|---------|-------------|
| `config <project> --show` | Show configuration |
| `config <project> --multi-agent on\|off` | Toggle multi-agent mode |
| `config <project> --concurrency N` | Set concurrency level |

**Agent Integration:**
- Wired config into Agent class
- Added `parallelizable` and `depends_on` fields to Step
- Hook now allows `~/.claude/` paths

### Bash Command Detection (commits `34e3b25`, `682fac9`, `5d126cc`)

Closed the Bash write loophole in pretooluse hook:
- Detects file-writing Bash commands (cat >, echo >, tee, etc.)
- Treats detected writes like Edit/Write tool calls
- Updated hook matcher to include Bash

### Dart Parser (commit `2edbf2d`)

**New Module (parsers/dart.py):**
- Extracts: imports, classes, mixins, extensions, enums, typedefs, functions
- Handles: package imports, dart SDK imports, relative imports
- Supports: Dart 3 modifiers (base, final, interface, sealed)

### Run Summaries & Decisions (commits `bbfd2f5`, `7b176e8`)

**New Classes (agent/run.py):**
- `Decision` - Track decisions during runs
- `RunSummary` - Generate post-run summaries

**Agent API:**
- `agent.add_decision(decision, rationale)` - Record a decision
- `agent.generate_summary(one_liner)` - Generate run summary

### Must-Haves Verification (commit `d81b15f`)

**New Classes (spec.py):**
- `Artifact` - Expected file with exports
- `KeyLink` - Required import between files
- `MustHaves` - Container for truths, artifacts, key_links

**Spec Updates:**
- Added `must_haves` field to Spec
- Added `verify_must_haves()` method

### Roadmap Support (commit `5c665d5`)

**New Classes (memory.py):**
- `Milestone` - A phase in the roadmap
- `Roadmap` - Collection of milestones with current index

**New CLI Commands:**
| Command | Description |
|---------|-------------|
| `roadmap <project>` | View roadmap |
| `roadmap-add <project> <name> <desc>` | Add milestone |
| `roadmap-next <project>` | Advance to next phase |
| `roadmap-edit <project> <index> <name> <desc>` | Edit milestone |

### Discuss Mode (commit `1d05d8b`)

**New Module (discuss.py):**
- `generate_questions()` - Auto-generate clarifying questions
- Question types: scope, constraints, priorities, specifics
- Integration with knowledge store

**New CLI Commands:**
| Command | Description |
|---------|-------------|
| `discuss <project> <goal>` | Start goal discussion |
| `discuss-answer <project> <q> <a>` | Answer a question |
| `discuss-show <project>` | Show current discussion |
| `discuss-resolve <project>` | Mark discussion complete |
| `discuss-clear <project>` | Clear discussion |

### Project Metadata (commits `253edb8`, `0c3384c`)

**New Registry Fields:**
- `description` - Project description
- `todos` - Project TODO list
- `notes` - Free-form notes

**New CLI Commands:**
| Command | Description |
|---------|-------------|
| `describe <project> [text]` | Get/set description |
| `todo <project> [text]` | Add/list TODOs |
| `notes <project> [text]` | Add/get notes |
| `decision <project> <desc>` | Record a decision |
| `decisions <project>` | List decisions |
| `patterns <project>` | List patterns |

### Smart Test Selection (commit `692f1c3`)

New verification feature:
- Find tests that import changed files
- Prioritize relevant tests for faster feedback
- Added to `verification.py`

### Documentation & Cleanup (commits `cf0ef6c`, `729c139`, `13762a9`, `c062a8f`)

**New Documentation:**
- `docs/ARCHITECTURE.md` - System architecture
- `docs/CHANGELOG.md` - Version history
- `docs/CLAUDE_CODE.md` - Integration guide
- `docs/INSTALL.md` - Installation instructions
- `docs/USAGE.md` - Usage guide
- `docs/AGENT_WORKFLOW.md` - Agent API examples
- `docs/MANUAL.md` - Complete user manual

**Removed:**
- Obsolete phase ticket files
- Planning scratch files
- Research source directories

### Installer & Hooks (commit `8307b5c`)

**New Module (install.py):**
- `eri-rpg install` - Install Claude Code integration
- `eri-rpg uninstall` - Clean removal
- `eri-rpg install-status` - Check installation

**New Hooks:**
- `hooks/precompact.py` - Save state before context compaction
- `hooks/sessionstart.py` - Remind about incomplete runs

### Core Fixes (commits `39f33f7`, `76415f1`)

**Unified Specs:**
- `erirpg/spec.py` is now canonical
- `erirpg/agent/spec.py` re-exports from canonical

**Mandatory Verification:**
- `complete_step()` returns False if verification fails
- Stores stdout/stderr in run log

**Path Normalization:**
- Fixed in preflight.py and hooks
- Uses `Path(__file__).parent` for portability

### Planning Directory (commit `2a15c88`)

Added GSD-style `.planning/` directory:
- `PROJECT.md` - Project vision
- `ROADMAP.md` - Future plans
- `phases-v1/` - 6 completed development phases

Each phase includes: SUMMARY.md, FEATURES.md, PITFALLS.md, ARCHITECTURE.md

### Hooks.py Shadowing Fix (commit `cee64bd`)

Renamed `erirpg/hooks.py` to `erirpg/write_guard.py`:
- Resolves Python module shadowing issue
- `hooks/` directory now properly accessible

---

## Summary Statistics

- **Commits:** 31
- **New files:** 40+
- **New CLI commands:** 25+
- **Lines added:** ~10,000+
- **Performance improvements:** O(n^2) -> O(n) for graph operations
- **Bug fixes:** 46 silent exceptions, nested .eri-rpg detection, hooks.py shadowing
