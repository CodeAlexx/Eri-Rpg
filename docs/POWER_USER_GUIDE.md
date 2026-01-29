# EriRPG + SuperClaude Power User Guide

> **One tool. Three tiers. From vibe coder to senior engineer.**

This guide helps you tap the full power of EriRPG and SuperClaude at every skill level.

---

## Quick Reference Card

| Your Level | Start Here | Graduate To |
|------------|------------|-------------|
| **Vibe Coder** | `/sc:implement` + Quick Fix | Lite tier |
| **Junior Dev** | Lite tier + `/sc:analyze` | Standard tier |
| **Mid-Level** | Standard tier + learning | Full tier |
| **Senior Engineer** | Full tier + automation | Custom workflows |

---

## Part 1: For Vibe Coders (Just Get It Done)

### Your Essential Commands

```bash
# "I just want Claude to build something"
/sc:implement "add a login button"
/sc:build myproject

# "Something broke"
/sc:troubleshoot "the button doesn't work"

# "Explain this to me"
/sc:explain "what does this function do"
```

### Quick Fix Mode (Your Best Friend)

When you just need to change ONE file:

```bash
eri-rpg quick myproject src/app.py "fix the typo"
# Make your edits...
eri-rpg quick-done myproject   # Commits it
# OR
eri-rpg quick-cancel myproject  # Oops, undo everything
```

**Why use quick fix?** It snapshots your file, lets you edit, and either commits or restores. No broken files.

### SuperClaude Commands for Beginners

| Command | What It Does | When to Use |
|---------|--------------|-------------|
| `/sc:implement` | Builds features | "Add X to my app" |
| `/sc:build` | Compiles/packages | "Make it run" |
| `/sc:troubleshoot` | Finds problems | "It's broken" |
| `/sc:explain` | Teaches you | "What is this?" |
| `/sc:test` | Runs tests | "Does it work?" |

### Your First Project Setup

```bash
# 1. Initialize (starts in lite tier - perfect for beginners)
eri-rpg init myproject --path ~/projects/myapp

# 2. Install hooks (protects your code)
eri-rpg install

# 3. Start coding!
/sc:implement "create a todo list app"
```

---

## Part 2: For Junior Developers (Learning the Ropes)

### Lite Tier Commands (Your Toolkit)

**Workflow Commands:**
```bash
eri-rpg take myproject "implement user auth"  # Start a feature
eri-rpg work myproject auth                   # Switch to working on auth
eri-rpg done myproject "added login form"     # Mark complete
```

**Tracking Commands:**
```bash
eri-rpg todo myproject "add password validation"  # Track tasks
eri-rpg notes myproject "API key is in .env"      # Leave notes for yourself
eri-rpg session myproject                         # See current state
eri-rpg handoff myproject                         # Generate summary for next session
```

### Upgrade to Standard Tier

When you're ready for more power:

```bash
# First, index your codebase (builds understanding)
eri-rpg index myproject

# Then upgrade
eri-rpg mode myproject --standard
```

### SuperClaude Analysis (Level Up Your Skills)

```bash
# Understand code before touching it
/sc:analyze src/auth/ --focus security

# Get estimates before committing
/sc:estimate "how long to add OAuth?"

# Clean up messy code
/sc:cleanup src/legacy/
```

### Learning from Your Code

```bash
# After reading a complex file, store what you learned
eri-rpg learn myproject src/auth/jwt.py

# Later, recall what you knew
eri-rpg recall myproject src/auth/jwt.py

# Store patterns you discover
eri-rpg pattern myproject "all handlers use try/catch" --gotcha "forgot logging"
```

---

## Part 3: For Mid-Level Developers (Taking Control)

### Standard Tier Commands

**Exploration (Understand Before You Change):**
```bash
eri-rpg show myproject              # Project structure
eri-rpg find myproject "auth"       # Find auth-related code
eri-rpg impact myproject auth.py    # What breaks if I change this?
```

**Discussion (Plan Before You Build):**
```bash
eri-rpg discuss myproject "should we use JWT or sessions?"
eri-rpg discuss-answer myproject 1 "JWT because mobile app"
eri-rpg discuss-resolve myproject 1  # Ready to implement
```

**Decisions (Track Why You Did Things):**
```bash
eri-rpg log-decision myproject "chose PostgreSQL over MongoDB" \
    --rationale "need ACID transactions" \
    --alternatives "MongoDB,SQLite" \
    --tradeoffs "more setup, but safer data"

eri-rpg list-decisions myproject  # Review past decisions
```

**Roadmap (Long-Term Planning):**
```bash
eri-rpg roadmap-add myproject "v1.0 MVP" --must-haves "auth,dashboard,export"
eri-rpg roadmap myproject           # View roadmap
eri-rpg roadmap-next myproject      # Move to next phase
```

### SuperClaude for Architecture

```bash
# Design systems properly
/sc:design "microservices architecture for payment processing"

# Document what you build
/sc:document src/api/ --format wiki

# Complex multi-step tasks
/sc:task "migrate database to PostgreSQL"

# Git workflows
/sc:git commit    # Smart commit messages
/sc:git review    # Self-review before PR
```

### Flags That Make You Faster

```bash
# Think deeper on complex problems
/sc:analyze --think        # 4K tokens of analysis
/sc:analyze --think-hard   # 10K tokens, cross-module

# Compress output when context is tight
/sc:analyze --uc           # Ultra-compressed symbols

# Focus on what matters
/sc:improve --focus security
/sc:analyze --focus performance
```

---

## Part 4: For Senior Engineers (Full Control)

### Upgrade to Full Tier

```bash
eri-rpg mode myproject --full
```

### Full Tier: The Complete Arsenal

**Agent Runs (Automated Multi-Step Work):**
```bash
# Start a full agent run with verification
/eri:execute "refactor auth module to use OAuth2"

# Check run status
eri-rpg status myproject

# Resume interrupted work
/eri:execute  # Auto-resumes incomplete runs
```

**Specs & Plans (Formal Requirements):**
```bash
# Generate a spec from discussion
eri-rpg spec new myproject "payment-integration"

# View generated plan
eri-rpg plan show myproject

# Execute step by step
eri-rpg plan next myproject
```

**Goal-Driven Development:**
```bash
# High-level goal → spec → execution
eri-rpg goal-plan myproject "add Stripe payments"
eri-rpg goal-run myproject
eri-rpg goal-status myproject
```

**Verification (Never Ship Broken Code):**
```bash
# Configure verification
eri-rpg verify config myproject

# Run verification
eri-rpg verify run myproject

# See what failed
eri-rpg gaps myproject
```

**Memory Management:**
```bash
eri-rpg memory status myproject      # Knowledge health
eri-rpg memory search myproject "auth"  # Find learnings
eri-rpg memory stale myproject       # Find outdated knowledge
eri-rpg rollback myproject auth.py 1 # Revert to version 1
```

### SuperClaude Power Features

**Personas (Specialized Thinking):**
```bash
/sc:analyze --persona-security    # Think like a security expert
/sc:improve --persona-performance # Think like a performance engineer
/sc:design --persona-architect    # Think like a systems architect
```

**Wave Mode (Complex Operations):**
```bash
# For large-scale changes across many files
/sc:improve . --wave-mode --focus quality

# Enterprise-grade analysis
/sc:analyze . --wave-strategy enterprise --ultrathink
```

**MCP Integration (External Tools):**
```bash
# Use library docs
/sc:implement "add React Query" --c7

# UI component generation
/sc:design "dashboard layout" --magic

# End-to-end testing
/sc:test e2e --play
```

**Delegation (Parallel Work):**
```bash
# Analyze in parallel
/sc:analyze . --delegate folders

# Multi-focus analysis
/sc:analyze . --delegate auto --parallel-focus
```

### EriRPG Slash Commands (In-Session)

When working inside a project, these commands set your workflow phase AND persona:

```
/analyze    - Understand codebase (aliases: /a)
/discuss    - Plan approach (aliases: /d, /plan)
/implement  - Write code (aliases: /i, /build)
/review     - Critique code (aliases: /r, /check)
/debug      - Fix problems (aliases: /db, /fix)

/architect  - Systems perspective
/dev        - Pragmatic perspective
/critic     - Find issues perspective
/mentor     - Teaching mode
```

### Drift Integration (Pattern Consistency)

```bash
eri-rpg drift-status myproject      # Check drift integration
eri-rpg sync-patterns myproject     # Sync with Drift
eri-rpg drift-impact myproject auth.py  # Pattern-aware impact
eri-rpg enrich-learnings myproject  # Add pattern data to learnings
```

---

## Part 5: GSD Workflow (Get Stuff Done)

GSD is a *workflow philosophy* built into EriRPG - not a separate tool. These are all `eri-rpg` commands that implement decision tracking and idea capture to prevent "decision amnesia."

### The GSD Philosophy

```
Discuss → Decide → Defer (what you can't do now) → Do → Document
```

### EriRPG's GSD Commands

**Decision Logging (Track WHY you chose things):**
```bash
# Log a decision with full context
eri-rpg log-decision myproject "Auth method" "JWT" "Stateless, works with mobile"

# Later, find what you decided
eri-rpg list-decisions myproject
eri-rpg list-decisions myproject --search "auth"
```

**Deferred Ideas (Capture, don't forget):**
```bash
# You're building v1 but think of a v2 feature
eri-rpg defer myproject "Add caching layer" --tags v2,perf

# Later, review deferred ideas
eri-rpg deferred myproject
eri-rpg deferred myproject --tag v2

# When ready, promote to roadmap
eri-rpg promote myproject IDEA-001 --goal "Build v2"
```

### GSD Workflow Example

```bash
# 1. Start discussing a feature
eri-rpg discuss myproject "add user authentication"

# 2. Answer questions, log decisions as you go
eri-rpg log-decision myproject "Token storage" "localStorage" "Simple, works offline"
eri-rpg log-decision myproject "Session length" "7 days" "Balance security/UX"

# 3. Defer ideas that come up but aren't for now
eri-rpg defer myproject "Add OAuth providers" --tags v2,auth
eri-rpg defer myproject "Add 2FA" --tags security,v2

# 4. Resolve discussion, generate spec
eri-rpg discuss-resolve myproject

# 5. Execute - decisions are preserved
eri-rpg goal-run myproject

# 6. Later, review what you decided
eri-rpg list-decisions myproject --search "auth"
```

### Why GSD Matters

| Problem | GSD Solution |
|---------|--------------|
| "Why did I choose X?" | `list-decisions` shows rationale |
| "I had a great idea but forgot" | `defer` captures it immediately |
| "What's planned for v2?" | `deferred --tag v2` shows backlog |
| "New dev asks why JWT not sessions" | Decision log explains it |

### Standard Tier Required

These GSD-style commands require **standard tier** because they integrate with:
- Discussion system (tracking what you're deciding)
- Roadmap (where promoted ideas go)
- Learning (decisions become project knowledge)

```bash
# Upgrade to use GSD
eri-rpg mode myproject --standard
```

### Session State with Decisions

```bash
# See current session with all GSD tracking
eri-rpg session myproject

# Generate handoff with decisions included
eri-rpg handoff myproject
```

### Planned Additions (Roadmap)

Future GSD-style features:
- **Research phase**: Dedicated step before planning (prevent wheel reinvention)
- **Wave execution**: Parallel task execution
- **Must-haves derivation**: Goal → observable truths → required files
- **Discovery levels**: Auto-detect how much research needed

---

## Part 6: Workflows by Task Type

### Bug Fix

| Level | Workflow |
|-------|----------|
| Vibe Coder | `/sc:troubleshoot "describe bug"` |
| Junior | `eri-rpg quick proj file "fix bug"` → fix → `quick-done` |
| Mid | `eri-rpg learn` the module first → `quick` → fix → `quick-done` |
| Senior | `/eri:execute "fix bug with root cause analysis"` (full verification) |

### New Feature

| Level | Workflow |
|-------|----------|
| Vibe Coder | `/sc:implement "feature description"` |
| Junior | `eri-rpg take proj "feature"` → `/sc:implement` → `eri-rpg done` |
| Mid | `discuss` → `log-decision` → `take` → implement → `done` |
| Senior | `goal-plan` → `spec new` → `/eri:execute` → verify → ship |

### Refactoring

| Level | Workflow |
|-------|----------|
| Vibe Coder | `/sc:improve path/` |
| Junior | `/sc:analyze` first → `/sc:improve` |
| Mid | `eri-rpg impact` → `learn` affected files → `/sc:improve` |
| Senior | `/sc:analyze --wave-mode` → `plan` → `/eri:execute` with verification |

### Code Review

| Level | Workflow |
|-------|----------|
| Vibe Coder | `/sc:analyze path --focus quality` |
| Junior | `/review` in-session command |
| Mid | `/sc:analyze --think-hard --focus security,quality` |
| Senior | `/sc:analyze --ultrathink --all-mcp --wave-mode` |

---

## Part 7: Tier Feature Matrix

| Feature | Lite | Standard | Full |
|---------|------|----------|------|
| Quick fix mode | ✅ | ✅ | ✅ |
| Basic workflow (take/work/done) | ✅ | ✅ | ✅ |
| Session tracking | ✅ | ✅ | ✅ |
| Codebase exploration | ❌ | ✅ | ✅ |
| Learning/recall | ❌ | ✅ | ✅ |
| Discussion mode | ❌ | ✅ | ✅ |
| Roadmap management | ❌ | ✅ | ✅ |
| Decision logging (GSD-style) | ❌ | ✅ | ✅ |
| Defer/promote ideas (GSD-style) | ❌ | ✅ | ✅ |
| Agent runs | ❌ | ❌ | ✅ |
| Spec/plan system | ❌ | ❌ | ✅ |
| Verification | ❌ | ❌ | ✅ |
| Memory management | ❌ | ❌ | ✅ |
| Research phase (GSD-style) | ❌ | ❌ | ✅ |
| Drift integration | ❌ | ❌ | ✅ |
| Web dashboard | ❌ | ❌ | ✅ |

### Upgrading Tiers

```bash
# Check current tier
eri-rpg mode myproject

# Upgrade (will prompt to index if needed)
eri-rpg mode myproject --standard
eri-rpg mode myproject --full

# Downgrade if needed
eri-rpg mode myproject --lite
```

---

## Part 8: SuperClaude + EriRPG Synergy

### Best Combinations

| Task | SuperClaude | EriRPG |
|------|-------------|--------|
| Understand new codebase | `/sc:load` + `/sc:analyze` | `eri-rpg learn` after |
| Build feature safely | `/sc:implement` | Use within agent run |
| Fix bug with confidence | `/sc:troubleshoot` | `quick` mode |
| Refactor safely | `/sc:improve` | `impact` → `learn` first |
| Document project | `/sc:document` | `eri-rpg describe` |
| Review before merge | `/sc:analyze --focus quality,security` | `eri-rpg verify` |

### The Ultimate Workflow (Senior)

```bash
# 1. Start session with enforcement
/eri:start

# 2. Analyze the task
/sc:analyze . --think-hard

# 3. Plan with EriRPG
eri-rpg discuss myproject "task description"
eri-rpg goal-plan myproject "refined goal"

# 4. Execute with verification
/eri:execute "implement the plan"

# 5. Review and ship
/sc:analyze . --focus security,quality
/sc:git commit
```

---

## Part 9: Troubleshooting

### "I'm blocked by EriRPG"

```bash
# Check what's blocking
eri-rpg status myproject

# Clear stale state
eri-rpg cleanup myproject --prune

# Disable temporarily (bootstrap mode)
eri-rpg mode myproject --bootstrap

# Re-enable when ready
eri-rpg mode myproject --maintain
```

### "Commands are hidden"

Commands are tier-gated. Upgrade to access:

```bash
# See your tier
eri-rpg mode myproject

# Upgrade
eri-rpg mode myproject --standard  # or --full
```

### "Hooks won't install"

```bash
# Check status
eri-rpg install-status

# Reinstall
eri-rpg uninstall
eri-rpg install
```

### "Index is out of date"

```bash
# Re-index
eri-rpg index myproject --force
```

---

## Part 10: Cheat Sheet

### Vibe Coder Daily Commands
```
/sc:implement "what you want"
/sc:troubleshoot "what's broken"
/sc:explain "what you don't understand"
```

### Junior Dev Daily Commands
```
eri-rpg quick proj file "description"  # Safe single-file edit
eri-rpg quick-done proj                # Commit it
/sc:analyze path/                      # Understand before edit
```

### Mid-Level Daily Commands
```
eri-rpg learn proj file               # After understanding
eri-rpg impact proj file              # Before changing
eri-rpg discuss proj "approach"       # Plan first
eri-rpg log-decision proj "choice"    # Document why
```

### Senior Daily Commands
```
/eri:start                            # Enforce all edits
/eri:execute "goal"                   # Full agent run
eri-rpg verify run proj               # Never ship broken
/sc:analyze --ultrathink --wave-mode  # Deep analysis
```

### Decision & Idea Tracking (GSD-style)
```
eri-rpg log-decision proj "context" "choice" "why"  # Track decisions
eri-rpg list-decisions proj                          # Review decisions
eri-rpg defer proj "idea" --tags v2                  # Capture for later
eri-rpg deferred proj                                # See backlog
eri-rpg promote proj IDEA-001                        # Move to roadmap
```

---

## Part 11: Getting Help

```bash
# EriRPG help
eri-rpg --help
eri-rpg <command> --help

# SuperClaude help
/sc:index                # Browse all commands

# In-session
/help                    # EriRPG slash commands
```

---

*Built for humans who want to ship code with confidence.*

**Version**: 0.55.0-alpha | **Tiers**: lite → standard → full
