# Full Plan: EriRPG Spec-Driven Runner

## Mission
Build a lean spec-driven runner that turns specs into verified changes with durable memory, outperforming GSD in reliability, speed, and retention.

## Assumptions
- CLI-first, Python-based, local-only analysis.
- Claude is the default executor, with optional scripted execution later.
- Graph + knowledge + context remain the core pipeline.

## Success Criteria
- End-to-end `spec -> plan -> run -> verify -> report` works reliably.
- Plan mappings point to correct source modules; relative imports resolved.
- Learnings persist across reindex and are flagged stale when source changes.
- At least one real workflow completes faster or more reliably than GSD.

## Phase 0: Discovery and Definition
Goals
- Define what "better than GSD" means for this project.
- Choose 1-2 real workflows as acceptance tests.

Tasks
- Collect example tasks and acceptance checks.
- Draft minimal `TaskSpec` template.
- Define success metrics (time, tokens, failures).

Deliverables
- Spec template + acceptance checklist.
- Baseline metrics on current EriRPG behavior.

Acceptance
- Example specs are defined and reviewed.
- Metrics and targets are documented.

## Phase 1: Core Correctness
Goals
- Fix correctness gaps in planning and dependency graphs.

Tasks
- Fix mapping provenance in `erirpg/ops.py`.
- Resolve relative imports in `erirpg/parsers/python.py` and `erirpg/indexer.py`.
- Align CLI language options with actual indexer support.
- Use language-aware code fences in context output.
- Normalize state phases (including "building").
- Add baseline tests for graph/extract/plan/context.

Deliverables
- Accurate plan mappings.
- Dependency graphs include relative imports.
- Tests enforce core behavior.

Acceptance
- Tests cover mapping and relative import scenarios.
- `eri-rpg index` matches language support advertised in CLI.

## Phase 2: Durable Memory
Goals
- Make knowledge persistent and stale-aware.

Tasks
- Create a dedicated knowledge store (e.g., `.eri-rpg/knowledge.json`).
- Add `source_hash` and `source_mtime` to learnings.
- Merge or migrate knowledge on reindex.
- Update `learn` and `recall` commands for staleness warnings.

Deliverables
- Learnings survive reindex.
- Stale learnings are detected and reported.

Acceptance
- Reindex does not remove knowledge.
- Stale modules are flagged consistently.

## Phase 3: Spec Schema and CLI
Goals
- Formalize specs as inputs for planning and execution.

Tasks
- Implement `TaskSpec`, `ProjectSpec`, `TransplantSpec` in `erirpg/specs.py`.
- Add validation + normalization.
- Add `eri-rpg spec new` and `eri-rpg spec validate` commands.

Deliverables
- Spec files saved to `.eri-rpg/specs/`.
- Validation errors are clear and actionable.

Acceptance
- Invalid specs fail with explicit errors.
- Valid specs round-trip through parse/serialize.

## Phase 4: Planner
Goals
- Convert specs into ordered, verifiable steps.

Tasks
- Implement `Plan` and `PlanStep` in `erirpg/planner.py`.
- Generate steps using graph and knowledge.
- Save plans to `.eri-rpg/plans/` with dependencies and verify commands.

Deliverables
- Deterministic plan generation for a spec.

Acceptance
- Plans include dependencies and verification commands.
- Plan output is stable across runs.

## Phase 5: Runner and Checkpoints
Goals
- Orchestrate execution with pause/resume.

Tasks
- Implement `erirpg/runner.py` (step loop: context -> execute -> verify).
- Implement `erirpg/runs.py` for run logs and artifacts.
- Add `eri-rpg run`, `resume`, and `report` commands.

Deliverables
- Run artifacts stored in `.eri-rpg/runs/`.
- Runner can pause and resume.

Acceptance
- A spec can be executed end-to-end with checkpoints.
- Runner produces a report with step status.

## Phase 6: Verification
Goals
- Automated testing gates after steps.

Tasks
- Implement `erirpg/verification.py` for lint/test commands.
- Add config-driven verification rules.
- Integrate verification into runner loop.

Deliverables
- Verification reports with pass/fail and diagnostics.

Acceptance
- Failing tests halt or flag runs correctly.
- Reports include command output and next steps.

## Phase 7: UX and Hardening
Goals
- Improve usability and stability.

Tasks
- Better diagnostics and failure summaries.
- Impact-aware ordering using graph analysis.
- Performance tuning for indexing and planning.
- Documentation and quickstart examples.

Deliverables
- Clearer output, faster runs, and updated docs.

Acceptance
- Users can complete a full run without manual fixes to tooling output.

## Phase 8: Evaluation and Iterate
Goals
- Prove it is better than GSD on real tasks.

Tasks
- Benchmark workflow vs GSD.
- Collect failure cases and iterate.

Deliverables
- Comparison report and prioritized fixes.

Acceptance
- At least one workflow shows measurable improvement.

## MVP Workflow (Example)
- Spec: "Add dark mode to settings" with acceptance tests.
- Plan: identify modules, step edits, verify with tests.
- Run: context pack per step, manual execution via Claude, verification report.

## Risks and Mitigations
- Risk: incorrect graph edges -> wrong plan.
  Mitigation: relative import resolution + tests.
- Risk: stale knowledge -> bad guidance.
  Mitigation: staleness detection.
- Risk: CLI promises unsupported languages.
  Mitigation: align options with indexer support.

## First Sprint (2 weeks)
- Fix mapping provenance and relative imports.
- Add language-aware code fences.
- Normalize state phases.
- Add baseline tests.
- Define TaskSpec schema and validation.

## Open Questions
- Should decisions be stored globally or per project?
- Do we implement TS/Go indexing now or hide from CLI?
- How strict should staleness enforcement be (warn vs block)?
