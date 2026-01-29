---
name: eri:pattern
description: Store a reusable pattern or gotcha
argument-hint: "<project> <pattern> [--gotcha]"
---

# /eri:pattern - Store Pattern

Capture patterns, conventions, and gotchas for future reference.

## Usage
```bash
# Store a pattern
eri-rpg pattern <project> "<pattern description>"

# Store a gotcha (warning/anti-pattern)
eri-rpg pattern <project> "<gotcha>" --gotcha

# List patterns
eri-rpg patterns <project>
```

## Example
```bash
# Patterns
eri-rpg pattern myapp "All API handlers use try/catch with error logging"
eri-rpg pattern myapp "Use dependency injection for services"

# Gotchas
eri-rpg pattern myapp "Don't use raw SQL - always use ORM" --gotcha
eri-rpg pattern myapp "Redis connection must be closed in finally block" --gotcha
```

## When to Capture
- Discover a convention while reading code
- Make a decision about how to do things
- Find a footgun to avoid
- Learn from a bug

## Tier
Requires: **standard** or higher
