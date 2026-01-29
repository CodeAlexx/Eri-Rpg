# Changelog

## v0.55.0-alpha (2026-01-28)

Knowledge sync, instant preflight, and persona system (SuperClaude replacement).

### New Features

**Persona System** (replaces SuperClaude's static ~20k token prompts)
- 5 focused personas: architect, dev, critic, analyst, mentor
- Auto-detection from user input triggers
- Stage-to-persona mapping (implement→dev, review→critic, etc.)
- `eri-rpg persona --list` - Show available personas
- `eri-rpg workflow --list` - Show stages and their default personas
- `eri-rpg ctx` - Generate dynamic CLAUDE.md (~400 tokens vs 20k)
- `eri-rpg commands` - Show slash commands

**Slash Commands**
- Workflow: `/analyze`, `/discuss`, `/implement`, `/review`, `/debug`
- Personas: `/architect`, `/dev`, `/critic`, `/analyst`, `/mentor`
- Management: `/roadmap`, `/status`, `/learn`, `/context`, `/help`
- Aliases: `/a`, `/i`, `/r`, `/db`, `/arch`, etc.

**New Modules**
- `erirpg/persona.py` - Persona definitions and detection
- `erirpg/workflow.py` - Stage management with persona mapping
- `erirpg/commands.py` - Slash command parsing
- `erirpg/session_context.py` - Dynamic context builder
- `erirpg/claudemd.py` - CLAUDE.md generator

**Knowledge Sync Command**
- `eri-rpg sync [project]` - Compare codebase files against knowledge.json
- `eri-rpg sync --learn` - Auto-learn unknown/stale files using parsers
- `eri-rpg sync --json` - Output as JSON for scripting
- `eri-rpg sync --lang python` - Limit to specific language
- Categories: known (up-to-date), stale (changed), unknown (new), deleted (removed)

**Instant Preflight**
- Preflight now uses cached `learnings_status` from `preflight_state.json`
- ~12ms lookup time instead of computing file hashes per-file
- Run `eri-rpg sync --learn` to populate cache for instant preflight

### Why This Replaces SuperClaude

| SuperClaude | EriRPG |
|-------------|--------|
| ~20k static tokens always loaded | ~400 dynamic tokens from project |
| Manual `/persona:architect` switch | Auto-detect from context |
| Generic rules for any project | Patterns learned from THIS codebase |
| No memory between sessions | StoredLearning persists |

### Version Cleanup
- Corrected version strings across all modules to 0.55.0-alpha

---

## v0.54.0-alpha (2026-01-28)

Bootstrap/Maintain mode system.

### New Features

**Bootstrap/Maintain Mode**
- Two-mode system for project lifecycle management
- **Bootstrap mode**: No enforcement, hooks pass through (for new/developing projects)
- **Maintain mode**: Full enforcement, requires preflight/runs (for stable projects)
- Migration: existing projects with learnings → maintain, empty → bootstrap

**New CLI Commands**
- `eri-rpg init <name> --path <path>` - Initialize project in bootstrap mode
- `eri-rpg graduate <project>` - Learn all files and enable maintain mode
- `eri-rpg mode <project> [--bootstrap|--maintain]` - Show/toggle mode
- `eri-rpg info <project>` - Show detailed project status with mode
- `eri-rpg list` now shows mode badges: `[BOOTSTRAP]` or `[MAINTAIN]`

**Hook Integration**
- pretooluse hook checks mode before enforcing
- Bootstrap mode: immediate pass-through, no blocking
- Maintain mode: full enforcement (existing behavior)

**UI Updates**
- Mode badges in sidebar (B=bootstrap yellow, M=maintain green)
- Mode badge and enforcement status in project header
- Mode info in runs partial

### Workflow

```bash
# New project workflow
eri-rpg init my-app --path ~/my-app   # bootstrap, no enforcement
# ... build freely ...
eri-rpg graduate my-app               # learn + enable enforcement

# Temporary disable for refactoring
eri-rpg mode my-app --bootstrap
# ... major refactor ...
eri-rpg graduate my-app               # re-learn everything
```

---

## v2.2.0 (2026-01-27)

Mojo language support.

### New Features

**Mojo Language Support**
- Full parsing support for `.mojo` and `.🔥` file extensions
- Project detection via `mojoproject.toml`
- `eri-rpg add --lang mojo` option
- Extracts: imports, fn/def functions, structs, traits, aliases
- Python interop detection (`Python.import_module`)
- Type parameter parsing (`fn name[T: Trait](...)`)
- Decorator support (`@value`, `@register_passable`, etc.)

**Parser Features**
- `parse_mojo_file()` - Full source file parsing
- `resolve_mojo_import()` - Import resolution
- `classify_mojo_package()` - External package detection
- `is_mojo_file()` - Extension checking (handles 🔥 emoji)

### About Mojo

Mojo is a systems programming language by Modular, designed for AI/ML:
- Superset of Python syntax
- `fn` for typed functions, `def` for dynamic
- `struct` for value types (not classes)
- `trait` for interfaces
- SIMD and ownership built into type system
- Python interoperability

---

## v2.1.0 (2026-01-27)

Research pipeline and wave execution.

### New Features

**Research Pipeline**
- `eri-rpg research <project> --goal "..."` - Run research for a goal
- Discovery level detection (0=skip, 1=quick, 2=standard, 3=deep)
- Automatic caching by goal hash
- RESEARCH.md output with stack choices, pitfalls, anti-patterns
- Avoid patterns injected into plan steps from research findings

**Wave Execution**
- `eri-rpg execute <project>` - Execute plan in waves
- Steps grouped into waves based on dependencies
- Parallel execution for parallelizable steps within a wave
- Checkpoint saves after each wave for resumable execution
- `--no-resume` flag to start fresh

**Discussion Context**
- DiscussionContext dataclass captures phase outputs
- CONTEXT.md generated after discuss phase
- Discovery level recommendation included
- "Claude's discretion" items tracked from "you decide" answers

**Plan Enhancements**
- `AvoidPattern` dataclass for patterns to avoid
- `CircularDependencyError` for dependency cycle detection
- Step fields: `action`, `avoid`, `done_criteria`, `checkpoint_type`, `wave`
- `compute_waves()` algorithm for wave assignment
- `Plan.waves` property for grouped steps

**Must-Haves Validation**
- `MustHaves` dataclass: observable_truths, required_artifacts, key_links
- `validate_plan()` detects gaps before execution
- `derive_must_haves_from_goal()` heuristic extraction

### Internal Changes

- New modules: `discovery.py`, `research.py`, `must_haves.py`, `modes/discuss.py`
- Enhanced `agent/plan.py` with wave computation
- Enhanced `agent/run.py` with WaveExecutor, StepResult, WaveResult, WaveCheckpoint
- CLI commands: `research`, `execute`

---


## v2.0.0