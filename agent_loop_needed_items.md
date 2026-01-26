# Agent Loop Needed Items (Claude Code)

Goal: The user states a goal once; the agent runs all CLI steps, writes code,
stores learnings, and advances the plan without human shell commands.

## Core Orchestration
- Agent runner entrypoint (e.g., `eri-rpg agent "<goal>"`) that:
  - Parses goal -> spec -> plan.
  - Starts a run and iterates steps until done.
  - Writes run logs and emits a final summary.
- Non-interactive flows for prompts (especially `new`):
  - Support `--answers` or `--spec` to avoid manual question prompts.

## Step Execution Loop
- For each plan step:
  - Generate focused context (existing `runner.prepare_step`).
  - Apply code changes (Claude Code applies diffs/patches).
  - Mark the step complete with metadata (files touched, notes).
- A machine-readable step context (JSON) for agent parsing, plus Markdown for
  display (already present).

## Memory and Auto-Learn
- Store learnings automatically after step completion:
  - New CLI/API call for v2 knowledge store (e.g., `memory learn`).
  - Create CodeRefs for touched files to track staleness.
  - Summarize intent, key functions, and gotchas based on diff and step goal.
- Update plans and contexts to prefer v2 knowledge instead of re-reading files.

## Change Detection and Safety
- File change detection per step (git diff or tracked file list).
- Risk gating:
  - High-risk steps require explicit approval or a "confirm" flag.
  - Enforce verification commands when specified in the plan.

## Reporting and UX
- Run report with: steps completed, files changed, tests run, learnings stored.
- Clear failure modes: resume a run, retry a step, or rollback guidance.

## Integration Notes
- Agent mode runs inside Claude Code (tool-enabled), not web chat.
- CLI remains the tool; the agent owns when/how to invoke it.
