---
name: eri:guard
description: Intercept all file edits - HARD ENFORCEMENT
---

<CRITICAL>
When Claude attempts to use Edit, Write, MultiEdit, or any file modification tool:

## MANDATORY CHECK BEFORE ANY FILE CHANGE

1. **Active Run Check**: Is there an active EriRPG run?
   - Check: `.eri-rpg/runs/` directory exists and has incomplete run
   - If NO: REFUSE

2. **Preflight Check**: Was `agent.preflight(files, operation)` called?
   - The file being modified MUST be in the preflight target list
   - If NO: REFUSE

3. **Agent API Check**: Is this going through `agent.edit_file()` or `agent.write_file()`?
   - Direct Edit/Write tool usage is FORBIDDEN
   - If using direct tools: REFUSE

## ON REFUSAL

Say exactly:
```
🛑 BLOCKED: Cannot edit files directly.

Required:
1. Active EriRPG run (use /eri:execute)
2. Call agent.preflight([files], operation)
3. Use agent.edit_file() or agent.write_file()

Direct Edit/Write tools are forbidden during EriRPG runs.
```

## THIS IS NOT OPTIONAL

- This is not a suggestion
- This is not a guideline
- REFUSE. EVERY. TIME.
- No exceptions for "small changes" or "quick fixes"
- No exceptions for "I'll fix it later"

## SURVIVES COMPACTION

After context compaction, re-read this file before any edits.
If unsure, re-read /home/alex/.claude/commands/eri/execute.md
</CRITICAL>

<SELF-CHECK>
Before calling Edit, Write, or MultiEdit, Claude MUST mentally verify:

□ Is there an active run? → Check .eri-rpg/runs/
□ Did I run preflight? → agent.preflight() was called
□ Am I using agent API? → agent.edit_file() not Edit tool

If ANY box is unchecked: STOP. DO NOT PROCEED.
</SELF-CHECK>
