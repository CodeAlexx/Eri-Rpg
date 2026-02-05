# Discussion Completion Box

Use this format when discussion is complete:

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE {N} DISCUSSED                                         ║
╠════════════════════════════════════════════════════════════════╣
║  Decisions captured: {count}                                   ║
║  Claude's discretion: {count} areas                            ║
║  Deferred ideas: {count}                                       ║
║  Context: .planning/phases/{XX-name}/CONTEXT.md                ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Plan the phase

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The planner will read CONTEXT.md and honor your locked decisions.
Claude has discretion on: {list areas}

{If deferred ideas exist:}
## Noted for Later
- {deferred idea 1} — future phase
- {deferred idea 2} — future phase
```

## STATE.md Update

```markdown
## Current Phase
**Phase {N}: {phase-name}** - discussed (ready to plan)

## Last Action
Completed discuss-phase {N}
- Decisions captured: {count}
- Claude's discretion areas: {count}
- Deferred ideas: {count}
- Context file: .planning/phases/{XX-name}/CONTEXT.md

## Next Step
Run `/coder:plan-phase {N}` to create execution plans
```

## Global State Update

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```
