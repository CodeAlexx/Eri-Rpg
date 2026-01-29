# Getting Started with EriRPG

## First Time Setup

### 1. Initialize Your Project
```bash
eri-rpg init myproject --path ~/projects/myapp
```
This creates `.eri-rpg/` directory with config, state, and knowledge files.
Starts in **lite tier** (basic tracking, no enforcement).

### 2. Install Hooks (Recommended)
```bash
eri-rpg install
```
This installs Claude Code hooks that protect your code from accidental edits.

### 3. Start Working

**Option A: Quick Fix (single file)**
```bash
/eri:quick myproject src/file.py "fix the bug"
# Make edits...
/eri:done myproject
```

**Option B: Full Workflow (multi-file)**
```bash
/eri:execute "implement user authentication"
```

## Choosing Your Tier

| Tier | Best For | Commands |
|------|----------|----------|
| **lite** | Quick tasks, learning | quick, done, session |
| **standard** | Ongoing projects | + discuss, learn, decide, roadmap |
| **full** | Production apps | + execute, spec, plan, verify |

Upgrade anytime:
```bash
eri-rpg mode myproject --standard
eri-rpg mode myproject --full
```

## Next Steps
- `/eri:help quick` - Learn quick fix mode
- `/eri:help tiers` - Understand tier differences
- `/eri:help new-feature` - Implement your first feature
