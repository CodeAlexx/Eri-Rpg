---
name: eri:execute
description: Execute or resume an EriRPG run with verification and auto-learning
argument-hint: "<goal>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

<setup>
export ERI_RPG_PATH=/home/alex/eri-rpg
PYTHONPATH=$ERI_RPG_PATH python3 -m erirpg.cli <command>

Or install once per session:
pip install -e /home/alex/eri-rpg --break-system-packages
</setup>

<mode-selection>
BEFORE starting, decide which mode fits the task:

QUICK FIX MODE - Use when:
- Single file edit (typo, small bug, minor tweak)
- No multi-step workflow needed
- Simple change that doesn't need tracking

  eri-rpg quick <project> <file> "<description>"
  # Make edits...
  eri-rpg quick-done <project>

FULL AGENT MODE - Use when:
- Multi-file changes
- Feature implementation
- Transplant between projects
- Anything requiring spec/steps/learning

  Agent.from_goal("<goal>", project_path="...")

LEARN MODE - Use when:
- Just exploring/reading code
- No edits planned
- Building knowledge for later

  eri-rpg learn <project> <file>  # After understanding
  eri-rpg recall <project> <file> # To retrieve knowledge

CLEANUP MODE - Use when:
- Stale runs blocking progress
- Need to start fresh

  eri-rpg cleanup <project>          # List runs
  eri-rpg cleanup <project> --prune  # Delete stale runs
</mode-selection>

<objective>
Run the EriRPG agent loop end-to-end. The user provides only the goal.
You run all commands, edit files, verify results, and auto-learn.
Resume an incomplete run if it exists.
</objective>

<context>
Goal: $ARGUMENTS
Working dir: current repo unless user specifies another.
Use erirpg.agent (Python API) for run state, context, and auto-learning.
</context>

<process>
1) MODE SELECTION:
   - Check if this is a single-file quick fix → use quick fix mode
   - Check if this is exploration only → use learn mode
   - Check for stale runs blocking work → cleanup first
   - Otherwise → proceed with full agent mode

2) Resolve run state:
   - If .eri-rpg/runs has an incomplete run, resume it.
   - If a goal is provided and an incomplete run exists, ask whether to resume or start new.
   - If no run exists, create a new Agent.from_goal($ARGUMENTS).

3) Execute steps until complete:
   - Get step context via agent.get_context().
   - Read only the required files.
   - Implement changes.
   - Call agent.complete_step(files_touched=[...], notes="...").
   - Verification is mandatory:
     * Use .eri-rpg/verification.json if present.
     * Else if Python project, run pytest (and optional ruff).
     * Else if Node project, run npm test (and optional npm run lint).
     * If unclear, ask ONE question for the command.
   - Show verification output and exit codes.
   - Never claim success if verification failed or was skipped.

4) Finish:
   - Loop until agent.is_complete().
   - Print agent.get_report() and a short change summary.
</process>
