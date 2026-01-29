# Decision Tracking Workflow

Decision tracking is built into EriRPG to prevent "why did we choose X?" amnesia.

## The Philosophy

```
Discuss → Decide → Defer → Do → Document
```

## Core Commands

### Log Decisions
Track choices with full rationale:
```bash
eri-rpg log-decision myproject "Auth method" "JWT" "Stateless, works with mobile"
eri-rpg log-decision myproject "Database" "PostgreSQL" "Need ACID for payments"
```

### Review Decisions
```bash
eri-rpg list-decisions myproject
eri-rpg list-decisions myproject --search "auth"
```

### Defer Ideas
Capture ideas for later (don't lose them!):
```bash
eri-rpg defer myproject "Add OAuth providers" --tags v2,auth
eri-rpg defer myproject "Add caching layer" --tags perf,v2
```

### Review Deferred
```bash
eri-rpg deferred myproject
eri-rpg deferred myproject --tag v2
```

### Promote to Roadmap
When ready to implement a deferred idea:
```bash
eri-rpg promote myproject IDEA-001 --goal "v2 release"
```

## Example Workflow

```bash
# 1. Start discussing a feature
eri-rpg discuss myproject "add payments"

# 2. Make decisions, log them
eri-rpg log-decision myproject "Provider" "Stripe" "Best docs, team knows it"

# 3. Defer v2 ideas that come up
eri-rpg defer myproject "Add PayPal support" --tags v2,payments

# 4. Complete the discussion
eri-rpg discuss-resolve myproject

# 5. Later, check what was decided
eri-rpg list-decisions myproject --search "payment"
```

## Why This Matters

| Problem | Solution |
|---------|----------|
| "Why did we choose X?" | `list-decisions` shows rationale |
| "I had an idea but forgot" | `defer` captures it |
| "What's planned for v2?" | `deferred --tag v2` |
| New dev asks "why JWT?" | Decision log explains |

## Tier Required
Decision commands require **standard** tier or higher.
