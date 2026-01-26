# Phase 1 Tickets: Core Correctness

## P1-001: Fix mapping provenance in transplant plans
Goal
- Ensure plan mappings point to the true source module, not a topo-sorted dependency.

Changes
- Add an explicit primary module to Feature (or a per-interface source map).
- Use that source mapping in plan_transplant when building Mapping entries.
- Update any downstream consumers that assumed components[0] is the source.

Acceptance Criteria
- For a feature with dependencies, generated plans map interfaces to the correct source file.
- Unit test verifies mapping provenance with a fixture graph.

Dependencies
- None.

## P1-002: Resolve relative imports for Python indexing
Goal
- Accurately capture internal dependencies when relative imports are used.

Changes
- Add current module path context to resolve_import_to_module.
- Implement relative import resolution based on module path and level.
- Pass file context from indexer to parser or resolver.

Acceptance Criteria
- Graph edges include relative imports for a simple package fixture.
- Unit test confirms internal deps for relative imports.

Dependencies
- None.

## P1-003: Align CLI language support with indexer
Goal
- Prevent users from selecting languages that are not supported by the indexer.

Changes
- Update CLI --lang choices to match indexer support (python, c, rust).
- Update new-project language options to match indexer support.
- Add clear error message if an unsupported language is requested.

Acceptance Criteria
- CLI and new mode only show supported languages.
- Indexing a project with unsupported language fails fast with a clear message.

Dependencies
- None.

## P1-004: Language-aware context fences
Goal
- Ensure context files use the correct code fence language for each file.

Changes
- Use file extension or module language to choose fence (python, rust, c, text).
- Apply to both transplant context and work context generators.

Acceptance Criteria
- Python files render as ```python, Rust as ```rust, C as ```c.
- Unknown extensions fall back to ```text.

Dependencies
- None.

## P1-005: Normalize state phases
Goal
- Make phase handling consistent across modes and status reporting.

Changes
- Add "building" (or replace with existing phase) in State.get_next_step.
- Ensure new mode uses a phase recognized by State.
- Update status messaging to avoid "Unknown state".

Acceptance Criteria
- `eri-rpg status` displays a valid next step in new mode.
- No phase results in "Unknown state" unless genuinely invalid.

Dependencies
- None.

## P1-006: Add core tests and fixtures
Goal
- Lock in core correctness and prevent regressions.

Changes
- Add a minimal tests/ structure.
- Include fixtures for a Python package with relative imports.
- Add tests for mapping provenance, relative imports, and context fences.

Acceptance Criteria
- `pytest` passes with the new tests.
- Tests fail before fixes and pass after fixes.

Dependencies
- P1-001, P1-002, P1-004, P1-005 (tests depend on implemented behavior).
