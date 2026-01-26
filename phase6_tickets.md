# Phase 6 Tickets: Verification

## P6-001: Verification config
Goal
- Allow specs or repo config to define verification steps.

Changes
- Define verification settings in spec or config file.
- Support lint/test commands.

Acceptance Criteria
- Config is parsed and applied.

Dependencies
- Phase 5 complete.

## P6-002: Verification runner
Goal
- Execute verification commands and collect output.

Changes
- Implement `erirpg/verification.py`.
- Capture stdout/stderr and exit codes.

Acceptance Criteria
- Failures are reported clearly with command output.

Dependencies
- P6-001.

## P6-003: Verification integration
Goal
- Gate runner progress based on verification.

Changes
- Run verification after each step or at checkpoints.
- Stop or flag runs on failure.

Acceptance Criteria
- Failed verification halts or marks step failed.

Dependencies
- P6-002.

## P6-004: Verification CLI
Goal
- Allow manual verification and report viewing.

Changes
- Add `eri-rpg verify <run_id>` and `eri-rpg report <run_id>`.

Acceptance Criteria
- Reports include verification output and status.

Dependencies
- P6-002.

## P6-005: Verification tests
Goal
- Lock in verification behavior.

Changes
- Add tests for success and failure cases.

Acceptance Criteria
- Tests cover exit codes, output capture, and reporting.

Dependencies
- P6-002.
