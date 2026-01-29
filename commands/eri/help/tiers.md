# EriRPG Tiers Explained

## The Three Tiers

### Lite Tier (Default)
**Best for:** Quick tasks, learning EriRPG, simple projects

**Commands available:**
- `quick` / `quick-done` / `quick-cancel` - Single file edits
- `take` / `work` / `done` / `next` - Basic workflow
- `todo` / `notes` / `session` / `handoff` - Tracking
- `init` / `add` / `remove` / `list` - Setup

**Does NOT require:** Indexing

---

### Standard Tier
**Best for:** Ongoing projects, team work, decision tracking

**Adds these commands:**
- `show` / `find` / `impact` - Codebase exploration
- `learn` / `recall` / `pattern` - Knowledge capture
- `discuss` / `discuss-answer` / `discuss-resolve` - Planning
- `log-decision` / `defer` / `promote` - Decision tracking
- `roadmap` / `roadmap-add` - Long-term planning

**Requires:** Indexed codebase (`eri-rpg index myproject`)

---

### Full Tier
**Best for:** Production apps, complex features, verification

**Adds these commands:**
- `execute` / `run` / `status` - Agent runs
- `spec` / `plan` - Formal specifications
- `verify` / `gaps` - Test verification
- `research` - Pre-planning research
- `memory` / `rollback` - Memory management
- `cleanup` - State management
- `serve` - Web dashboard

**Requires:** Indexed codebase

---

## Upgrading Tiers

```bash
# Check current tier
eri-rpg mode myproject

# Upgrade
eri-rpg mode myproject --standard
eri-rpg mode myproject --full

# Downgrade (if needed)
eri-rpg mode myproject --lite
```

## Tier vs Mode

- **Tier** = What features are available (lite/standard/full)
- **Mode** = Whether enforcement is active (bootstrap/maintain)

New projects start in **lite tier + bootstrap mode** (no enforcement).
After graduating: **full tier + maintain mode** (full enforcement).
