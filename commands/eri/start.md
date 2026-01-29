---
name: eri:start
description: Start every coding session with this - enforces EriRPG for all changes
---

<critical>
ALL code changes in this session MUST go through EriRPG.

For ANY coding task, use: /eri:execute "<task>"

You are FORBIDDEN from:
- Direct file edits without an active EriRPG run
- Using Edit/Write tools outside of agent.edit_file()
- Claiming work is done without verification passing
- Bypassing EriRPG "to save time"

If EriRPG is broken, STOP and tell the user. Do not work around it.

After context compaction or session resume:
1. Re-read this file
2. Check for active runs in .eri-rpg/runs/
3. Resume or require /eri:execute for any code changes

Enforcement check - before ANY file edit, verify:
- Is there an active EriRPG run? If NO → refuse and suggest /eri:execute
- Is there a current step? If NO → refuse until step is started
- Will this edit be tracked? If NO → refuse

Confirm: "EriRPG enforced. Ready for /eri:execute commands."
</critical>
