# EriRPG Complete Manual

**Alpha v0.56** | Making Claude better at complex code changes

---

## Table of Contents

1. [For Users](#for-users)
   - [What EriRPG Does](#what-erirpg-does)
   - [Installation](#installation)
   - [Slash Commands](#slash-commands)
   - [Tiers](#tiers)
   - [Example Sessions](#example-sessions)
2. [How It Works](#how-it-works)
   - [Core Concepts](#core-concepts)
   - [Workflows](#workflows)
3. [CLI Reference](#cli-reference) *(What Claude uses internally)*
4. [Agent API Reference](#agent-api-reference) *(For developers extending EriRPG)*
5. [Troubleshooting](#troubleshooting)

---

# For Users

## What EriRPG Does

EriRPG gives Claude a structured workflow and persistent memory. You talk to Claude normally; Claude uses EriRPG internally to be more effective.

**With EriRPG, Claude will:**
- Remember code it has read (no re-reading the same files)
- Track decisions and context across sessions
- Verify changes with tests before marking complete
- Follow a structured workflow: discuss → plan → implement → verify
- Rollback if something goes wrong
- Challenge bad ideas and require intent (see [EMPOWERMENT.md](/EMPOWERMENT.md))

**What you need to do:**
- Install EriRPG (one time)
- Register your projects
- Use slash commands to tell Claude what you want

That's it. Claude handles the rest.

## Installation

```bash
# Install EriRPG
git clone https://github.com/CodeAlexx/Eri-Rpg.git
cd Eri-Rpg
pip install -e .

# Register your project
eri-rpg add myproject /path/to/your/code

# Install Claude Code integration
eri-rpg install

# Verify installation
eri-rpg install-status
```

### Project Management Commands

These are the only CLI commands you need to run directly:

| Command | Description |
|---------|-------------|
| `eri-rpg add <name> <path>` | Register a project |
| `eri-rpg remove <name>` | Unregister a project |
| `eri-rpg list` | List registered projects |
| `eri-rpg install` | Set up Claude Code hooks |
| `eri-rpg install-status` | Check installation |
| `eri-rpg mode <project> --standard` | Upgrade tier |

## Slash Commands

Talk to Claude using these commands:

| Command | What it does |
|---------|--------------|
| `/eri:start` | Begin a coding session |
| `/eri:execute "goal"` | Execute a goal with full workflow |
| `/eri:quick file.py "desc"` | Quick single-file edit |
| `/eri:debug "problem"` | Start triage-first debugging |
| `/eri:status` | Check current state |
| `/eri:resume` | Continue from last session |
| `/eri:recall module` | Get Claude's stored knowledge |
| `/eri:knowledge` | Show all stored knowledge |
| `/eri:discuss "goal"` | Clarify a vague goal |
| `/eri:roadmap` | View project milestones |
| `/eri:decide "choice"` | Log a decision |
| `/eri:persona` | Set or show active persona |
| `/eri:help` | Get help |

## Tiers

| Tier | What Claude can do | Enable with |
|------|-------------------|-------------|
| **lite** | Quick fixes, search, cross-project queries | Default |
| **standard** | + Discussion mode, goal clarification | `eri-rpg mode <project> --standard` |
| **full** | + Agent runs, specs, verification | `eri-rpg mode <project> --full` |

## Example Sessions

### Quick Fix

```
You: /eri:quick src/config.py "fix the timeout value"
Claude: [Makes the edit, verifies, commits]
Done.
```

### Feature Implementation

```
You: /eri:start
You: Add retry logic to the API client

Claude: [Internally:]
  - Recalls what it knows about the API client
  - Creates a plan
  - Implements with verification
  - Tracks the decision

Claude: Done. Added exponential backoff retry to api/client.py.
        Tested with 3 retry attempts, 1s/2s/4s delays.
```

### Complex Goal (needs clarification)

```
You: /eri:discuss "improve performance"

Claude: I have some questions:
  1. What specific aspect? (API, database, frontend)
  2. What's the success criteria?
  3. Any constraints?

You: Database queries are slow. Need <100ms response.

Claude: Got it. Creating a roadmap:
  - Phase 1: Profile slow queries
  - Phase 2: Add indexes
  - Phase 3: Benchmark

You: /eri:execute

Claude: [Works through each phase with verification]
```

### Resume After Break

```
You: /eri:resume

Claude: Last session: Adding auth to the API
        Phase 2/3 complete (JWT implementation done)
        Next: Add middleware

You: Continue

Claude: [Picks up where it left off]
```

### Debugging

```
You: /eri:debug "diffusers pipeline crashes with OOM"

Claude: Debug triage:
  1. Origin: Is this internal code or ported from external source?
  2. Symptom: What's happening vs expected?
  3. Changed: What changed recently?

  Integration debugging flagged: diffusers
  Comparing our implementation vs their docs...

You: It's ported from their example code

Claude: [Checks version compatibility, API usage, then diagnoses]
```

## Personas

Claude automatically adapts its persona based on what it's doing:

| Persona | Auto-triggers when |
|---------|-------------------|
| analyzer | Reading/searching code |
| backend | Editing .py, .js, .ts files |
| frontend | Editing .jsx, .tsx, .css files |
| qa | Running tests |
| devops | Git operations, Docker, deploy |
| scribe | Editing docs/markdown |
| security | Working with auth/crypto files |
| architect | Using Task tool, planning |
| debug | Running `/eri:debug` |

The persona shows in your status line: `🎭 analyzer`

You can manually set it: `/eri:persona architect`

But usually auto-detection is best - it adapts as you work.

## Known Externals (Integration Debugging)

When debugging, Claude checks for known external tools. If your problem mentions one, it flags for integration debugging.

Default externals: onetrainer, simpletuner, ai-toolkit, kohya, diffusers, transformers, accelerate, pytorch

Configure per project:
```
/eri:debug-config --list           # Show known tools
/eri:debug-config --add comfyui    # Add one
/eri:debug-config --remove pytorch # Remove one
```

---

# How It Works

## Core Concepts

### Knowledge Graph

Claude stores what it learns about your code:
- Module summaries
- Function signatures
- Dependencies
- Patterns and conventions

This persists across sessions. Claude recalls instantly instead of re-reading.

### Specs & Plans

For complex changes, Claude creates a spec:
- Goal definition
- Ordered steps
- Verification criteria

This prevents "I forgot what I was doing" mid-task.

### Decisions

Claude logs important choices:
- What was decided
- Why (rationale)
- Context

Future sessions can understand past reasoning.

### Runs

A run tracks execution of a spec:
- Current step
- Files touched
- Decisions made
- Duration

Enables resume after interruption.

## Workflows

### Quick Fix (All Tiers)

For simple single-file changes:
1. You: `/eri:quick file.py "description"`
2. Claude makes the edit
3. Claude verifies and completes

### Spec-Driven (Full Tier)

For complex multi-file changes:
1. Claude creates a spec from your goal
2. Executes steps in order
3. Verifies each step
4. Generates summary when done

### Discussion + Roadmap (Standard+ Tier)

For vague or large goals:
1. Claude asks clarifying questions
2. Breaks goal into phases
3. Works through each phase
4. Tracks progress on roadmap

---

# CLI Reference

> **Note:** This section documents what Claude uses internally. You don't need to run these commands directly - use the slash commands above instead.

### Knowledge Management

| Command | Description |
|---------|-------------|
| `eri-rpg learn <project> <file>` | Store learning about a module |
| `eri-rpg recall <project> <file>` | Retrieve stored learning |
| `eri-rpg knowledge <project>` | Show all learnings |
| `eri-rpg relearn <project> <file>` | Force re-learn |
| `eri-rpg forget <project> <file>` | Remove learning |

### Search & Analysis

| Command | Description |
|---------|-------------|
| `eri-rpg find <project> <query>` | Search modules |
| `eri-rpg show <project>` | Show project structure |
| `eri-rpg impact <project> <file>` | Analyze change impact |
| `eri-rpg index <project>` | Build dependency graph |

### Cross-Project Search

| Command | Description |
|---------|-------------|
| `eri-rpg find-interface "Name"` | Find class/function across all projects |
| `eri-rpg find-package torch` | Find all usages of a package |
| `eri-rpg find-dependents file.py` | Find dependents across projects |
| `eri-rpg db-stats` | Show database statistics |

### Spec & Run Management

| Command | Description |
|---------|-------------|
| `eri-rpg goal-plan <project> "goal"` | Generate spec from goal |
| `eri-rpg goal-run <project>` | Start/resume run |
| `eri-rpg status <project>` | Show current run status |
| `eri-rpg runs <project>` | List all runs |
| `eri-rpg cleanup <project> --prune` | Delete stale runs |

### Discussion & Roadmap

| Command | Description |
|---------|-------------|
| `eri-rpg discuss <project> "goal"` | Start goal discussion |
| `eri-rpg discuss-answer <project> <n> "answer"` | Answer question N |
| `eri-rpg discuss-resolve <project>` | Mark discussion complete |
| `eri-rpg roadmap <project>` | View roadmap |
| `eri-rpg roadmap-add <project> "phase" "desc"` | Add milestone |
| `eri-rpg roadmap-next <project>` | Advance to next phase |

### Decision Logging

| Command | Description |
|---------|-------------|
| `eri-rpg log-decision <project> "ctx" "choice" "why"` | Log decision with rationale |
| `eri-rpg list-decisions <project>` | List recent decisions |
| `eri-rpg defer <project> "idea"` | Capture idea for later |

### Quick Fix Mode

| Command | Description |
|---------|-------------|
| `eri-rpg quick <project> <file> "desc"` | Start quick fix |
| `eri-rpg quick-done <project>` | Complete quick fix |
| `eri-rpg quick-cancel <project>` | Cancel and restore |

### Session & Handoff

| Command | Description |
|---------|-------------|
| `eri-rpg session <project>` | Show session state |
| `eri-rpg handoff <project>` | Generate handoff summary |
| `eri-rpg resume` | Show resume context |

### Session Context (New)

| Command | Description |
|---------|-------------|
| `eri-rpg snapshot --alias "name"` | Checkpoint with readable name |
| `eri-rpg add-decision "ctx" "choice" "why"` | Log decision to SQLite |
| `eri-rpg add-blocker "desc" --severity HIGH` | Track blocker |
| `eri-rpg add-action "action" --priority 5` | Queue next action |
| `eri-rpg recall-decision --last 10` | List recent decisions |
| `eri-rpg generate-context` | Generate CONTEXT.md |
| `eri-rpg generate-status` | Generate STATUS.md |

Session context persists in SQLite and is automatically:
- Captured before context compaction (PreCompact hook)
- Presented at session start (SessionStart hook)
- Includes git branch for context

### Configuration

| Command | Description |
|---------|-------------|
| `eri-rpg config <project> --show` | Show settings |
| `eri-rpg config <project> --multi-agent on` | Enable multi-agent |
| `eri-rpg mode <project> --full` | Set tier |

---

# Agent API Reference

> **Note:** This section is for developers extending EriRPG or building custom integrations.

### Creating an Agent

```python
from erirpg.agent import Agent

# From a goal
agent = Agent.from_goal("add caching", project_path="/path/to/project")

# Resume existing run
agent = Agent.resume("/path/to/project")
```

### Step Execution

```python
# Get next step
step = agent.next_step()
agent.start_step()

# Preflight before edits (required)
report = agent.preflight(['src/module.py'], 'modify')
if report.ready:
    agent.edit_file('src/module.py', old, new)

# Complete step
agent.complete_step(files_touched=['src/module.py'], notes='Added feature')
```

### Decisions & Summaries

```python
# Record decision
agent.add_decision("Used Redis", rationale="Better performance")

# Generate summary
summary = agent.generate_summary("Added caching")
```

---

# Troubleshooting

### "Preflight required"

**What it means:** Claude tried to edit without checking first.

**What to do:** This is internal - Claude handles it. If you see this repeatedly, try `/eri:status` to check state.

### "Must learn target modules first"

**What it means:** Claude needs to read the file before editing.

**What to do:** Claude handles this automatically. If stuck, try `/eri:recall <module>` to check knowledge.

### Run stuck or stale

**What to do:**
```
/eri:status          # Check what's happening
/eri:cleanup         # Clear stale state if needed
```

### Claude isn't using EriRPG

**What to do:**
1. Check installation: `eri-rpg install-status`
2. Start session: `/eri:start`
3. Check project registered: `eri-rpg list`

---

## Version History

**v0.57-alpha** (January 2026)
- SQLite session context persistence
- Automatic git branch tracking
- Session aliases for human-readable names
- EMPOWERMENT.md directive for AI behavior
- Blockers and next actions tracking
- Auto-generated CONTEXT.md and STATUS.md

**v0.56-alpha** (January 2026)
- Decision logging and deferred ideas
- Session handoff support
- Cross-project SQLite search
- Performance optimizations
- Discussion mode for goal clarification
- Roadmaps for multi-phase projects

**v0.1.0**
- Initial release
