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

### Directory Architecture

- `erirpg/agents/` - Version control storage for agent specs (eri-*.md prefix)
- `~/.eri-rpg/agents/` - Production loading directory (*.md, no prefix)
- Files are copied/renamed during install from repo → production
- **Do not change DEFAULT_AGENTS_DIR to package directory** - that breaks the architecture

Key modules:
- `erirpg/agent/` - Agent API for Claude Code integration
- `erirpg/cli.py` - Command-line interface
- `erirpg/verification.py` - Verification system
- `erirpg/memory.py` - Knowledge/learning system

## Verification

For this project:
- Run: `python -m pytest tests/ -v`
- Or syntax check: `python -m py_compile erirpg/<file>.py`

## Self-Correction Protocol

When I make a mistake or break something:
1. **Document the fix in CLAUDE.md** - Add what went wrong and how to prevent it
2. **Return to planning mode** - Don't push through suboptimal solutions
3. **Create snapshots before risky changes** - Always have a restore point

## Guardrails (from Boris Cherny's tips)

### Planning First
- Invest effort in planning before implementation
- When issues arise, return to planning mode rather than pushing through

### Self-Documentation
- After corrections, update CLAUDE.md with lessons learned
- Establish personalized guidelines that reduce future mistakes

### Quality Gates
- "Grill me on these changes" - challenge my own work
- Request elegant reimplementations when code smells
- Write detailed specifications to reduce ambiguity

### Subagents for Context
- Delegate complex tasks to subagents to preserve main context
- Don't try to hold everything in one session

## Lessons Learned

### Never Improvise When Agents Fail (2026-02-03)
**Problem**: When Task tool fails (API 500, timeout), I default to "I'll do it myself" - reading agent specs and manually doing the work. This causes context exhaustion and state drift.
**Fix**: Added explicit failure handling to skill files (plan-phase.md, execute-phase.md).
**Rule**: When agent spawn fails:
1. Retry once
2. If still fails, STOP and report to user with options
3. NEVER do the agent's job manually
4. Wait for user decision

**Why**: Agents have isolated context by design. Manual execution defeats the purpose and degrades quality.

### Bootstrap Deadlock (2026-02-03)
**Problem**: Added coder-gate enforcement that parsed EXECUTION_STATE.json, but if JSON was corrupted, couldn't fix it because the hook blocked all edits.
**Fix**: Added `.planning/` to early-exit list in pretooluse.py (line 295-299).
**Prevention**: Always allow writes to config/state directories before enforcement checks run.
