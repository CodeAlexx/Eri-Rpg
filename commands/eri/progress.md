---
name: eri:progress
description: Show progress on current work
argument-hint: "<project>"
---

# /eri:progress - Progress Report

See where you are in the current workflow.

## Usage
```bash
# Current run progress
eri-rpg status <project>

# Session state
eri-rpg session <project>

# Roadmap progress
eri-rpg roadmap <project>

# Run history
eri-rpg runs <project>
```

## Status Output
```
Project: myapp
Mode: maintain (full tier)
Current Run: abc123
  Goal: Add user authentication
  Progress: 3/5 steps complete
  Current Step: Create login endpoint
  Files touched: 4
  Verification: PASSING
```

## Related Commands
```bash
eri-rpg info <project>       # Detailed project info
eri-rpg handoff <project>    # Generate summary for next session
eri-rpg gaps <project>       # Show what needs fixing
```

## Tier
Available in: **all tiers** (detail varies by tier)
