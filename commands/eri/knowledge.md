---
name: eri:knowledge
description: Show all stored knowledge for a project
argument-hint: "<project>"
---

# /eri:knowledge - View All Knowledge

See everything EriRPG knows about a project.

## Usage
```bash
eri-rpg knowledge <project>
```

## Output Includes
- All learned modules
- Stored patterns
- Decisions made
- Gotchas captured

## Related Commands
```bash
# Specific module
eri-rpg recall <project> <file>

# Decisions only
eri-rpg list-decisions <project>

# Patterns only
eri-rpg patterns <project>

# Search
eri-rpg memory search <project> "<query>"

# Stale knowledge
eri-rpg memory stale <project>
```

## Tier
Requires: **standard** or higher
