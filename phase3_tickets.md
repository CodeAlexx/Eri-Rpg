# Phase 3 Tickets: Spec Schema and CLI

## P3-001: Implement spec models and versioning
Goal
- Formalize specs as first-class inputs.

Changes
- Add `TaskSpec`, `ProjectSpec`, `TransplantSpec` in `erirpg/specs.py`.
- Add spec versioning and upgrade hooks.

Acceptance Criteria
- Specs serialize/deserialize reliably.

Dependencies
- Phase 2 complete.

## P3-002: Spec validation and normalization
Goal
- Ensure specs are correct before planning.

Changes
- Add schema validation with clear errors.
- Normalize fields (trim, defaults, canonical paths).

Acceptance Criteria
- Invalid specs fail with actionable messages.

Dependencies
- P3-001.

## P3-003: CLI spec commands
Goal
- Provide CLI entry points for spec workflows.

Changes
- `eri-rpg spec new <type>` for templates.
- `eri-rpg spec validate <path>` for validation.
- `eri-rpg spec show <path>` for rendering.

Acceptance Criteria
- CLI commands work for at least TaskSpec.

Dependencies
- P3-001, P3-002.

## P3-004: Spec storage conventions
Goal
- Standardize spec location and IDs.

Changes
- Store specs under `.eri-rpg/specs/`.
- Use deterministic IDs (slug + timestamp or hash).

Acceptance Criteria
- Specs can be listed and discovered.

Dependencies
- P3-003.

## P3-005: Spec tests
Goal
- Lock spec parsing behavior.

Changes
- Add round-trip tests for each spec type.
- Add validation error tests.

Acceptance Criteria
- Tests pass and cover invalid cases.

Dependencies
- P3-001, P3-002.
