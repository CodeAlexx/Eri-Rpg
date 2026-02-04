# Coder Workflow Audit (2026-02-04)

## Scope
- Reviewed docs: `docs/AUDIT_GSD_VS_CODER.md`, `docs/NOTES.md`, `docs/GSD_AND_WORKFLOW.md`.
- Cross-checked against implementation in `erirpg/skills/`, `erirpg/cli_commands/coder_cmds.py`, and hooks.
- Ran linter: `python3 -m erirpg.scripts.lint_skills --verbose`.

## Executive Verdict
The architecture direction is strong (skills + CLI + thick agents), but operations are currently inconsistent. The biggest issue is contract drift between docs, skills, hooks, and linter behavior.

## Strengths
- Strong phase orchestration detail in updated skills (`erirpg/skills/execute-phase.md`, `erirpg/skills/plan-phase.md`).
- Good verification primitives in CLI (`check_phase_verification`, human verification blocking in `erirpg/cli_commands/coder_cmds.py:139` and `erirpg/cli_commands/coder_cmds.py:4062`).
- Good research depth model in `erirpg/agents/eri-phase-researcher.md`.
- Useful diagnostics concept in `/coder:doctor` (`erirpg/skills/doctor.md`).

## Findings (Workflow Smoothness)

### High
1. Completion guardrail is failing on critical skills.
   - Linter requires `<completion>` tags (`erirpg/scripts/lint_skills.py:107`), and enforces `execute-phase.md` + `plan-phase.md` (`erirpg/scripts/lint_skills.py:25`).
   - Those two files currently do not contain `<completion>` sections (`erirpg/skills/execute-phase.md:334`, `erirpg/skills/plan-phase.md:343`).
   - Result: documented completion contract is not actually green.

2. Docs claim coder edit enforcement that code no longer applies.
   - `pretooluse.py` explicitly allows all coder project edits (`erirpg/hooks/pretooluse.py:307`, `erirpg/hooks/pretooluse.py:352`).
   - This conflicts with docs that say missing `EXECUTION_STATE.json` blocks edits.

3. PostToolUse behavior conflicts with its own docstring and can add friction.
   - Docstring says no per-edit auto-commit (`erirpg/hooks/posttooluse.py:5`), but hook always runs verification/commit path on edit (`erirpg/hooks/posttooluse.py:259`).
   - It also includes `.planning` projects in scope (`erirpg/hooks/posttooluse.py:69`, `erirpg/hooks/posttooluse.py:224`).

### Medium
4. Skill-CLI JSON contract drift in plan-phase.
   - Skill expects keys like `phase_number`, `phase_name`, `settings`, `paths` (`erirpg/skills/plan-phase.md:30`).
   - CLI returns different shape (`phase`, `phase_info`, `workflow`) (`erirpg/cli_commands/coder_cmds.py:1937`).

5. Docs contain stale correctness claims.
   - `docs/AUDIT_GSD_VS_CODER.md` says issue is fully fixed and still shows old line-count table (`docs/AUDIT_GSD_VS_CODER.md:5`, `docs/AUDIT_GSD_VS_CODER.md:308`).
   - `docs/NOTES.md` references a helper not found in current code (`docs/NOTES.md:177`).

6. No `/coder:linter` command even though workflow depends on lint checks.
   - Current lint entrypoint is only `python3 -m erirpg.scripts.lint_skills`.

## Recommendations

### 1) Introduce `/coder:linter` (md + cli coupled)
- Add CLI command: `coder-linter` (wrap `lint_skills` with `--json`).
- Add skill: `erirpg/skills/linter.md` that calls `python3 -m erirpg.cli coder-linter`.
- Make `/coder:doctor` call this first and include results in diagnosis.

### 2) Resolve completion contract mismatch
- Option A (strict): add `<completion>...</completion>` blocks to `plan-phase.md` and `execute-phase.md`.
- Option B (safer migration): update linter to accept both `<completion>` and `<step name="*_completion">`.

### 3) Clarify and simplify enforcement model
- If coder is intentionally non-blocking, update docs to reflect that and remove blocker language.
- If light gating is desired, warn (not block) when `EXECUTION_STATE.json` is missing and auto-suggest next command.

### 4) Reduce operational noise in hooks
- Scope auto-commit logic to `.eri-rpg` workflow only, or gate by config flag.
- Keep `.planning` projects as track-only by default.

### 5) Add regression tests for workflow contracts
- Add tests for:
  - skill-to-CLI JSON key compatibility,
  - linter pass/fail on required skills,
  - hook behavior for coder vs eri projects.

## Suggested next command
- Run: `python3 -m erirpg.scripts.lint_skills --verbose`
