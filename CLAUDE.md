@EMPOWERMENT.md

## MANDATORY - Coder Workflow Enforcement

On session start or /clear: run `/coder:init`

**Every skill calls its CLI first. Follow the CLI output exactly.**

Direct file edits without an active plan are forbidden.
`/coder:execute-phase` auto-creates EXECUTION_STATE.json to allow edits.

## Workflow

1. `/coder:init` - recover context
2. `/coder:plan-phase N` - create plans (calls CLI, spawns eri-planner)
3. `/coder:execute-phase N` - execute plans (calls CLI, auto-creates EXECUTION_STATE.json, spawns eri-executor for each plan)
4. `/coder:verify-work N` - validate completion

## How It Works

- Skill files are thin - they just call CLI and follow output
- CLI returns JSON with everything needed (plans, files, settings, instructions)
- CLI auto-creates EXECUTION_STATE.json so hooks allow edits
- Agent specs (eri-executor, eri-planner) have the deep logic
- On completion: `python3 -m erirpg.cli coder-end-plan` to re-enable enforcement

## Project Context

EriRPG is a spec-driven development framework that enforces structured execution with verification.

Key modules:
- `erirpg/agent/` - Agent API for Claude Code integration
- `erirpg/cli.py` - Command-line interface
- `erirpg/verification.py` - Verification system
- `erirpg/memory.py` - Knowledge/learning system

## Verification

For this project:
- Run: `python -m pytest tests/ -v`
- Or syntax check: `python -m py_compile erirpg/<file>.py`
