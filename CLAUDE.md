# EriRPG Project Instructions

## MANDATORY - EriRPG Enforcement

Use `/eri:start` at session begin.
Use `/eri:execute` for ALL code tasks.
No exceptions. No bypassing.

Direct file edits without an active EriRPG run are forbidden.
If you find yourself about to use Edit/Write directly, STOP and use `/eri:execute "<task>"` instead.

## Project Context

EriRPG is a spec-driven development framework that enforces structured execution with verification.

Key modules:
- `erirpg/agent/` - Agent API for Claude Code integration
- `erirpg/cli.py` - Command-line interface
- `erirpg/verification.py` - Verification system
- `erirpg/memory.py` - Knowledge/learning system

## Verification

For this project:
- Run: `cd /home/alex/eri-rpg && python -m pytest tests/ -v`
- Or syntax check: `python -m py_compile erirpg/<file>.py`
