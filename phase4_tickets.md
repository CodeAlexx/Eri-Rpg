# Phase 4 Tickets: Planner

## P4-001: Plan and PlanStep models
Goal
- Create a durable plan structure for execution.

Changes
- Add `Plan` and `PlanStep` in `erirpg/planner.py`.
- Include step dependencies and verification commands.

Acceptance Criteria
- Plans serialize/deserialize and preserve ordering.

Dependencies
- Phase 3 complete.

## P4-002: Plan generation heuristics
Goal
- Convert specs into ordered steps.

Changes
- Implement rule-based step generation for TaskSpec.
- Use graph + knowledge to select relevant modules.

Acceptance Criteria
- Plans are generated for a TaskSpec without manual steps.

Dependencies
- P4-001.

## P4-003: Dependency ordering and risk weighting
Goal
- Ensure safe, deterministic execution order.

Changes
- Use graph deps to order steps.
- Optionally flag risky steps based on impact.

Acceptance Criteria
- Steps always respect dependencies.

Dependencies
- P4-002.

## P4-004: Plan persistence and CLI
Goal
- Persist and inspect plans.

Changes
- Save plans to `.eri-rpg/plans/`.
- Add `eri-rpg plan <spec>` and `eri-rpg plan show`.

Acceptance Criteria
- Plans can be generated and reviewed via CLI.

Dependencies
- P4-001, P4-002.

## P4-005: Planner tests
Goal
- Verify deterministic planning.

Changes
- Tests for plan generation and dependency ordering.

Acceptance Criteria
- Identical inputs produce identical plans.

Dependencies
- P4-001 to P4-004.
