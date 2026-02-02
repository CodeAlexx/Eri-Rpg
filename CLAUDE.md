@EMPOWERMENT.md

## MANDATORY - Coder Workflow Enforcement

On session start or /clear: run `/coder:init`

Use `/coder:plan-phase` before implementing.
Use `/coder:execute-phase` for ALL code tasks.
No exceptions. No bypassing.

Direct file edits without an active plan are forbidden.
If you find yourself about to use Edit/Write directly, STOP and use the coder workflow instead.

## Workflow

1. `/coder:init` - recover context
2. `/coder:plan-phase N` - create plan for phase N
3. `/coder:execute-phase N` - implement the plan
4. `/coder:verify-work N` - validate completion

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
