---
name: eri:rethink
description: Reconsider current approach
argument-hint: "<project>"
---

# /eri:rethink - Reconsider Approach

When you realize the current approach isn't working, step back and rethink.

## Workflow
```bash
# 1. Check current state
eri-rpg status <project>

# 2. Review what you've learned
eri-rpg knowledge <project>
eri-rpg list-decisions <project>

# 3. If approach is wrong, start new discussion
eri-rpg discuss <project> "RETHINK: <new approach>"

# 4. Log why you're changing
eri-rpg log-decision <project> \
  "Approach change" \
  "Switch from X to Y" \
  "Original approach had problem Z"

# 5. If needed, reset current run
eri-rpg reset <project>
```

## Signs You Need to Rethink
- Verification keeps failing
- Scope creep beyond spec
- Found better approach
- Requirements changed
- Blocked by technical limitation

## Capture the Learning
Always log WHY you're changing:
```bash
eri-rpg log-decision <project> "Pivot" "New approach" "Old approach failed because..."
eri-rpg pattern <project> "Don't use X for Y because Z" --gotcha
```

## Tier
Available in: **all tiers**
