---
name: eri:phase
description: Show current workflow phase
argument-hint: "<project>"
---

# /eri:phase - Current Phase

See what phase you're in and what's next.

## Usage
```bash
# Via session
eri-rpg session <project>

# Via status
eri-rpg status <project>
```

## Workflow Phases
1. **discuss** - Clarifying requirements
2. **research** - Investigating solutions
3. **plan** - Creating execution plan
4. **execute** - Implementing
5. **verify** - Testing
6. **done** - Complete

## In-Session Commands
When working, use slash commands to switch phases:
```
/analyze    - Understand codebase
/discuss    - Plan approach
/implement  - Write code
/review     - Critique
/debug      - Fix problems
```

## Tier
Available in: **all tiers**
