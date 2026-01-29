---
name: eri:push
description: Push changes after verification
argument-hint: "<project>"
---

# /eri:push - Verified Push

Push changes only after verification passes.

## Recommended Workflow
```bash
# 1. Complete work
eri-rpg done myapp "finished feature"

# 2. Verify everything passes
eri-rpg verify run myapp

# 3. Check for gaps
eri-rpg gaps myapp

# 4. If clean, push
git push origin <branch>
```

## With SuperClaude
```bash
/sc:git commit   # Smart commit
# then
git push
```

## Pre-Push Checklist
- [ ] All tests passing (`eri-rpg verify run`)
- [ ] No gaps (`eri-rpg gaps`)
- [ ] Changes committed
- [ ] Meaningful commit message

## Tier
Available in: **all tiers**
