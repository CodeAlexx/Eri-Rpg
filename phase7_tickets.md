# Phase 7 Tickets: UX and Hardening

## P7-001: Better diagnostics and failure summaries
Goal
- Make failures fast to understand and fix.

Changes
- Add structured diff summaries in reports.
- Summarize failed verification output with hints.

Acceptance Criteria
- Reports are readable and actionable.

Dependencies
- Phase 6 complete.

## P7-002: Impact-aware planning
Goal
- Reduce risk by ordering steps with impact awareness.

Changes
- Use graph impact to reorder or flag steps.
- Add warnings for high-impact changes.

Acceptance Criteria
- High-impact steps are flagged in plan output.

Dependencies
- Phase 4 complete.

## P7-003: Performance tuning
Goal
- Improve indexing and planning speed.

Changes
- Add caching for parsed files and incremental indexing.
- Avoid reprocessing unchanged modules.

Acceptance Criteria
- Indexing is faster on repeated runs.

Dependencies
- Phase 1 complete.

## P7-004: Documentation and quickstart
Goal
- Make onboarding straightforward.

Changes
- Add a quickstart spec and example run.
- Update README with new commands.

Acceptance Criteria
- New users can complete an example run from docs.

Dependencies
- Phase 3 complete.

## P7-005: UX polish
Goal
- Improve CLI output consistency and clarity.

Changes
- Standardize progress messages and status output.
- Add clear next-step hints.

Acceptance Criteria
- CLI output is consistent across modes.

Dependencies
- Phase 5 complete.
