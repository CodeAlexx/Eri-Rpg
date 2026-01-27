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
Always use PYTHONPATH for eri-rpg commands:
PYTHONPATH=/home/alex/eri-rpg python3 -m erirpg.cli <command>
Or install once per session:
pip install -e /home/alex/eri-rpg --break-system-packages
</setup>

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
1) Resolve run state:
   - If .eri-rpg/runs has an incomplete run, resume it.
   - If a goal is provided and an incomplete run exists, ask whether to resume or start new.
   - If no run exists, create a new Agent.from_goal($ARGUMENTS).

2) Execute steps until complete:
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

3) Finish:
   - Loop until agent.is_complete().
   - Print agent.get_report() and a short change summary.
</process>
