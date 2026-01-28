# Changelog

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