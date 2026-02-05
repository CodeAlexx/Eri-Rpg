# Completion Box Template

Use after plans are created and validated.

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE {N} PLANNED                                           ║
╠════════════════════════════════════════════════════════════════╣
║  Plans created: {list}                                         ║
║  Research: Level {depth} ({confidence})                        ║
║  Location: .planning/phases/{NN-name}/                         ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Execute the plans

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:execute-phase {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This will spawn executors to build the code for each plan.
```

**Replace:**
- `{N}` — Phase number
- `{list}` — Plan names (01-PLAN.md, 02-PLAN.md, etc.)
- `{depth}` — Research depth level (0-3)
- `{confidence}` — HIGH/MEDIUM/LOW or "skipped"
- `{NN-name}` — Phase directory name (01-setup)
