# Phase 5 Tickets: Runner and Checkpoints

## P5-001: Runner orchestration loop
Goal
- Implement spec execution with checkpoints.

Changes
- Add `erirpg/runner.py` step loop: context -> execute -> verify.
- Track step status and allow pause/resume.

Acceptance Criteria
- Runner can execute a plan with manual execution steps.

Dependencies
- Phase 4 complete.

## P5-002: Run record storage
Goal
- Persist run state and artifacts.

Changes
- Add `erirpg/runs.py` with RunRecord/StepStatus.
- Save logs and step outputs in `.eri-rpg/runs/`.

Acceptance Criteria
- Runs can be resumed after interruption.

Dependencies
- P5-001.

## P5-003: Per-step context builder
Goal
- Generate minimal, focused context for each step.

Changes
- Extend context generation to accept PlanStep.
- Include relevant modules and constraints for the step.

Acceptance Criteria
- Each step yields a context file in run artifacts.

Dependencies
- P5-001.

## P5-004: Runner CLI commands
Goal
- Expose runner functionality.

Changes
- Add `eri-rpg run`, `resume`, `report` commands.
- Show progress and next steps.

Acceptance Criteria
- CLI can start and resume runs.

Dependencies
- P5-001, P5-002.

## P5-005: Integration test for runner
Goal
- Ensure end-to-end runner correctness.

Changes
- Add a small fixture spec and plan.
- Verify a run produces artifacts and statuses.

Acceptance Criteria
- Integration test passes end-to-end.

Dependencies
- P5-001 to P5-004.
