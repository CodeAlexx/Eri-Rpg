# Phase 0 Tickets: Discovery and Definition

## P0-001: Define success metrics and target workflows
Goal
- Establish what "better than GSD" means in measurable terms.

Changes
- Define metrics: time-to-context, tokens, verification pass rate, manual fixes.
- Choose 1-2 real workflows to serve as acceptance tests.
- Document expected outputs and acceptance checks.

Acceptance Criteria
- Metrics and targets are documented.
- At least two workflows with acceptance checklists exist.

Dependencies
- None.

## P0-002: Draft minimal TaskSpec template and checklist
Goal
- Provide a canonical spec template for early pilots.

Changes
- Create a TaskSpec template with required fields.
- Provide a short example spec with acceptance tests.
- Add a lightweight checklist for reviewers.

Acceptance Criteria
- Template and example spec are available in repo docs/templates.
- Checklist is included and used for the initial workflows.

Dependencies
- None.

## P0-003: Baseline current EriRPG
Goal
- Capture baseline metrics before major changes.

Changes
- Run the selected workflows with current EriRPG.
- Capture timing, token estimates, and failure notes.
- Store results in a baseline report.

Acceptance Criteria
- Baseline report exists and is referenced by later comparisons.

Dependencies
- P0-001.

## P0-004: Lock key decisions
Goal
- Prevent churn by fixing early design decisions.

Changes
- Decide knowledge scope (per-project vs global).
- Decide staleness policy (warn vs block).
- Decide language support to ship in MVP.
- Record decisions in a persistent file.

Acceptance Criteria
- Decisions are documented and referenced by Phase 1+ work.

Dependencies
- P0-001.
