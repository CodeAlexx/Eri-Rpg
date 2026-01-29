---
name: eri:commit
description: Commit changes with EriRPG context
argument-hint: "<project> [message]"
---

# /eri:commit - Context-Aware Commits

Commit changes with EriRPG tracking context.

## For Quick Fixes
```bash
# Quick fix commits automatically
eri-rpg quick myapp src/file.py "fix typo"
# ... edit ...
eri-rpg quick-done myapp  # Auto-commits
```

## For Agent Runs
Agent runs track changes automatically. After completing:
```bash
# Changes are tracked, use git normally
git add -A
git commit -m "feat: add authentication

Implements JWT-based auth with refresh tokens.

EriRPG Run: abc123
Steps completed: 5/5
Verification: PASSING"
```

## With SuperClaude
```bash
/sc:git commit   # Smart commit message generation
```

## Best Practice
Let EriRPG track changes, then commit with context:
1. Complete work via `/eri:execute` or `/eri:quick`
2. Review changes: `git status`, `git diff`
3. Commit with run context in message

## Tier
Available in: **all tiers**
