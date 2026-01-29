---
name: eri:session
description: Show or update current session state
argument-hint: "<project>"
---

# /eri:session - Session Management

Track session state including decisions, blockers, and progress.

## Usage
```bash
# Show session state
eri-rpg session <project>

# Generate handoff for next session
eri-rpg handoff <project>
```

## Session State Includes
- Current workflow phase
- Active run (if any)
- Recent decisions
- Blockers/questions
- Files modified
- Time spent

## Handoff
When ending a session, generate a handoff summary:
```bash
eri-rpg handoff myapp

# Creates .eri-rpg/resume.md with:
# - What was being worked on
# - Current step
# - Decisions made
# - What's next
```

## Tier
Available in: **all tiers**
