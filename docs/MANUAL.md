# EriRPG Complete Manual

**Version 2.1** | Spec-driven development toolkit for AI-assisted coding

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Core Concepts](#core-concepts)
4. [Workflows](#workflows)
5. [CLI Reference](#cli-reference)
6. [Agent API Reference](#agent-api-reference)
7. [Claude Code Integration](#claude-code-integration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

EriRPG enforces a structured workflow for AI-assisted code changes:

```
Goal → Discuss → Spec → Run → Verify
```

### What to Expect

**EriRPG will:**
- Block direct file edits without proper workflow (preflight)
- Track all changes made during a run
- Auto-learn modules after you edit them
- Provide rollback capability
- Verify changes with tests

**EriRPG will NOT:**
- Write code for you (it's a workflow tool, not a code generator)
- Replace your judgment (you decide what to implement)
- Work without registration (projects must be added first)

### Key Benefits

1. **Structured Changes** - No more "I forgot what I changed"
2. **Knowledge Retention** - Learn once, recall anytime
3. **Safe Experimentation** - Rollback if things go wrong
4. **Verification** - Tests run automatically
5. **Multi-phase Projects** - Roadmaps break large goals into phases

---

## Installation

### Quick Install

```bash
# Clone and install
git clone https://github.com/CodeAlexx/Eri-Rpg.git
cd Eri-Rpg
pip install -e .

# Set up Claude Code integration
eri-rpg install

# Verify
eri-rpg --version
```

### Manual Setup

See [INSTALL.md](INSTALL.md) for detailed instructions.

---

## Core Concepts

### Projects

A **project** is a registered codebase that EriRPG tracks.

```bash
# Register
eri-rpg add myproject /path/to/code

# Index (builds dependency graph)
eri-rpg index myproject

# List registered projects
eri-rpg list
```

### Knowledge

**Knowledge** is stored information about modules you've read and understood.

```bash
# Learn a module
eri-rpg learn myproject src/utils.py

# Recall what you learned
eri-rpg recall myproject src/utils.py

# View all knowledge
eri-rpg knowledge myproject
```

Knowledge prevents re-reading code you already understand and enables preflight checks.

### Specs

A **spec** defines what needs to be done. It contains:

- **goal** - What to accomplish
- **steps** - Ordered actions (learn, create, modify, verify)
- **must_haves** - Verification requirements
- **constraints** - Rules to follow

```yaml
# Example spec (.eri-rpg/specs/abc123.yaml)
id: abc123
goal: "Add caching to API responses"
project: myproject
steps:
  - id: learn
    action: learn
    targets: [api/handlers.py]
  - id: implement
    action: modify
    targets: [api/handlers.py]
    depends_on: [learn]
  - id: verify
    action: verify
must_haves:
  truths:
    - "All API responses are cached"
  artifacts:
    - path: api/handlers.py
      exports: [CacheMiddleware]
  key_links:
    - from_file: api/handlers.py
      to_file: api/cache.py
      pattern: "from.*cache.*import"
```

### Runs

A **run** is an execution of a spec. It tracks:

- Current step
- Files learned
- Files edited
- Decisions made
- Duration and timing

```bash
# List runs
eri-rpg runs myproject

# View run status
eri-rpg status myproject
```

### Discussions

A **discussion** clarifies goals before creating specs. Used for:

- Vague goals ("improve performance")
- New projects (few files exist)
- Complex features needing breakdown

```bash
# Start a discussion
eri-rpg discuss myproject "improve the API"

# Answer questions
eri-rpg discuss-answer myproject "Which endpoints?" "The /users endpoint"

# Resolve when done
eri-rpg discuss-resolve myproject
```

### Roadmaps

A **roadmap** breaks large goals into phases (milestones).

```bash
# Add milestones to a discussion
eri-rpg roadmap-add myproject "Phase 1: Research" "Understand current implementation"
eri-rpg roadmap-add myproject "Phase 2: Implement" "Add the new feature"
eri-rpg roadmap-add myproject "Phase 3: Test" "Verify everything works"

# View roadmap
eri-rpg roadmap myproject

# Advance to next phase
eri-rpg roadmap-next myproject
```

### Decisions

**Decisions** are logged choices with context and rationale.

```bash
# Log a decision with full context
eri-rpg log-decision myproject "Auth method" "JWT" "Stateless, works with microservices"

# List recent decisions
eri-rpg list-decisions myproject
eri-rpg list-decisions myproject --search "auth"
```

Decisions help future sessions understand why choices were made.

### Deferred Ideas

**Deferred ideas** capture "v2/later" features during discussion.

```bash
# Capture an idea for later
eri-rpg defer myproject "Add caching layer" --tags v2,perf

# List deferred ideas
eri-rpg deferred myproject
eri-rpg deferred myproject --tag v2

# Promote to a roadmap milestone when ready
eri-rpg promote myproject IDEA-001 --goal "Build feature X"
```

### Session State

**Session state** tracks context for handoff between sessions.

```bash
# View current session state
eri-rpg session myproject

# Generate handoff summary for next session
eri-rpg handoff myproject

# View verification gaps
eri-rpg gaps myproject
```

---

## Workflows

### Workflow 1: Quick Fix (Simple Changes)

For single-file edits like typos, small bugs, config changes.

```bash
# Start quick fix
eri-rpg quick myproject src/config.py "Fix typo in default value"

# Make your edits (EriRPG allows this specific file)

# Complete when done
eri-rpg quick-done myproject

# Or cancel if something went wrong
eri-rpg quick-cancel myproject
```

### Workflow 2: Spec-Driven (Complex Changes)

For multi-file changes, new features, refactoring.

```bash
# Generate a spec from a goal
eri-rpg goal-plan myproject "Add user authentication"

# Start execution
eri-rpg goal-run myproject

# Follow the steps in order (use Agent API in code)
```

**Using the Agent API:**

```python
from erirpg.agent import Agent

# Resume the run
agent = Agent.resume('/path/to/myproject')

# Execute steps
while not agent.is_complete():
    step = agent.next_step()
    agent.start_step()

    # Preflight before any edits
    report = agent.preflight(['src/auth.py'], 'modify')
    if not report.ready:
        print(report.format())
        break

    # Make edits through the agent
    agent.edit_file('src/auth.py', old_content, new_content)

    # Complete the step
    agent.complete_step(
        files_touched=['src/auth.py'],
        notes='Added login endpoint'
    )

# Generate summary when done
summary = agent.generate_summary("Implemented user authentication")
print(summary.to_dict())
```

### Workflow 3: Discussion + Roadmap (Large Projects)

For complex goals that need clarification and phasing.

```bash
# 1. Start discussion (auto-generates questions)
eri-rpg discuss myproject "Build a REST API"

# 2. Answer the questions
eri-rpg discuss-answer myproject "What endpoints?" "CRUD for users and posts"
eri-rpg discuss-answer myproject "Authentication?" "JWT tokens"

# 3. Add roadmap phases
eri-rpg roadmap-add myproject "Setup" "Project structure and dependencies"
eri-rpg roadmap-add myproject "Users API" "User CRUD endpoints"
eri-rpg roadmap-add myproject "Posts API" "Post CRUD endpoints"
eri-rpg roadmap-add myproject "Auth" "JWT authentication"

# 4. Resolve discussion
eri-rpg discuss-resolve myproject

# 5. Work through each phase
eri-rpg goal-plan myproject  # Uses current roadmap milestone
eri-rpg goal-run myproject
# ... complete the phase ...
eri-rpg roadmap-next myproject  # Advance to next phase
```

---

## CLI Reference

### Project Management

| Command | Description |
|---------|-------------|
| `eri-rpg add <name> <path>` | Register a project |
| `eri-rpg remove <name>` | Unregister a project |
| `eri-rpg list` | List all projects |
| `eri-rpg index <name>` | Build dependency graph |
| `eri-rpg show <name>` | Show project structure |

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
| `eri-rpg impact <project> <file>` | Analyze change impact |
| `eri-rpg deps <project> <file>` | Show dependencies |

### Spec & Run Management

| Command | Description |
|---------|-------------|
| `eri-rpg goal-plan <project> "<goal>"` | Generate spec from goal |
| `eri-rpg goal-run <project>` | Start/resume run |
| `eri-rpg status <project>` | Show current run status |
| `eri-rpg runs <project>` | List all runs |
| `eri-rpg cleanup <project>` | Show stale runs |
| `eri-rpg cleanup <project> --prune` | Delete stale runs |

### Discussion & Roadmap

| Command | Description |
|---------|-------------|
| `eri-rpg discuss <project> "<goal>"` | Start goal discussion |
| `eri-rpg discuss-answer <project> "<q>" "<a>"` | Answer a question |
| `eri-rpg discuss-show <project>` | Show current discussion |
| `eri-rpg discuss-resolve <project>` | Mark discussion complete |
| `eri-rpg discuss-clear <project>` | Clear discussion |
| `eri-rpg roadmap <project>` | View roadmap |
| `eri-rpg roadmap-add <project> "<name>" "<desc>"` | Add milestone |
| `eri-rpg roadmap-next <project>` | Advance to next phase |
| `eri-rpg roadmap-edit <project> <index> "<name>" "<desc>"` | Edit milestone |

### Decision Logging

| Command | Description |
|---------|-------------|
| `eri-rpg log-decision <project> "<context>" "<choice>" "<rationale>"` | Log a decision with full rationale |
| `eri-rpg list-decisions <project> [--search "<term>"] [--limit N]` | List recent decisions |
| `eri-rpg decision <project> "<description>"` | Quick decision record |
| `eri-rpg decisions <project>` | List all decisions |

### Deferred Ideas

| Command | Description |
|---------|-------------|
| `eri-rpg defer <project> "<idea>" [--tags v2,perf,ui]` | Capture a deferred idea |
| `eri-rpg deferred <project> [--tag <tag>] [--all]` | List deferred ideas |
| `eri-rpg promote <project> <idea_id> [--goal "<goal>"]` | Promote idea to milestone |

### Session Management

| Command | Description |
|---------|-------------|
| `eri-rpg session <project>` | Show current session state |
| `eri-rpg handoff <project>` | Generate session handoff summary |
| `eri-rpg gaps <project>` | View verification gaps |

### Configuration

| Command | Description |
|---------|-------------|
| `eri-rpg config <project> --show` | Show project configuration |
| `eri-rpg config <project> --multi-agent on\|off` | Toggle multi-agent mode |
| `eri-rpg config <project> --concurrency N` | Set concurrency level |

### Project Metadata

| Command | Description |
|---------|-------------|
| `eri-rpg describe <project> ["<text>"]` | Get/set project description |
| `eri-rpg todo <project> ["<text>"]` | Add/list TODOs |
| `eri-rpg notes <project> ["<text>"]` | Add/get notes |
| `eri-rpg patterns <project>` | List learned patterns |

### Pattern Analysis & Implementation

| Command | Description |
|---------|-------------|
| `eri-rpg analyze <project>` | Detect project patterns, conventions, extension points |
| `eri-rpg analyze <project> --force` | Re-analyze even if patterns exist |
| `eri-rpg implement <project> "<feature>"` | Plan implementation using patterns |
| `eri-rpg implement <project> "<feature>" --plan-only` | Show plan without executing |
| `eri-rpg transplant --from project:path --to target` | Extract feature and implement in target |
| `eri-rpg transplant --from file.md --to target` | Implement from description file |
| `eri-rpg describe-feature <project> <path>` | Extract feature description from source |

### Quick Fix Mode

| Command | Description |
|---------|-------------|
| `eri-rpg quick <project> <file> "<desc>"` | Start quick fix |
| `eri-rpg quick-done <project>` | Complete quick fix |
| `eri-rpg quick-cancel <project>` | Cancel and restore |
| `eri-rpg quick-status <project>` | Check status |

### Rollback

| Command | Description |
|---------|-------------|
| `eri-rpg rollback <project> <file>` | Show available snapshots |
| `eri-rpg rollback <project> <file> --code` | Restore file content |
| `eri-rpg rollback <project> <file> --learning` | Restore learning |

### Installation

| Command | Description |
|---------|-------------|
| `eri-rpg install` | Install Claude Code integration |
| `eri-rpg uninstall` | Remove Claude Code integration |
| `eri-rpg install-status` | Check installation status |

---

## Agent API Reference

### Creating an Agent

```python
from erirpg.agent import Agent

# From a goal (creates spec + run)
agent = Agent.from_goal("add caching", project_path="/path/to/project")

# From an existing spec file
agent = Agent.from_spec("/path/to/spec.yaml", project_path="/path/to/project")

# Resume an existing run
agent = Agent.resume("/path/to/project")
```

### Step Execution

```python
# Get current/next step
step = agent.current_step()
step = agent.next_step()

# Start a step
agent.start_step()

# Check progress
completed, total = agent.progress()
is_done = agent.is_complete()
```

### Preflight (MANDATORY)

```python
# Run preflight before any edits
report = agent.preflight(
    files=['src/module.py'],
    operation='modify',  # or 'create', 'delete'
    strict=True  # False to skip learning requirement
)

if not report.ready:
    print(f"Blockers: {report.blockers}")
    print(f"Must learn first: {report.must_learn_first}")
```

### File Operations

```python
# Edit a file (requires preflight)
agent.edit_file(
    file_path='src/module.py',
    old_content='def old():',
    new_content='def new():',
    description='Renamed function'
)

# Write a new file
agent.write_file(
    file_path='src/new_module.py',
    content='# New module\n',
    description='Created new module'
)
```

### Step Completion

```python
# Complete a step
agent.complete_step(
    files_touched=['src/module.py'],
    notes='Implemented feature X'
)

# Skip a step
agent.skip_step(reason='Not needed')

# Fail a step
agent.fail_step(error='Tests failed')
```

### Decisions & Summaries

```python
# Record a decision during the run
agent.add_decision(
    decision="Used Redis for caching",
    rationale="Better performance than file-based cache"
)

# Generate summary when complete
summary = agent.generate_summary("Added caching with Redis")
print(summary.to_dict())
# {
#   "run_id": "...",
#   "one_liner": "Added caching with Redis",
#   "decisions": [...],
#   "artifacts_created": [...],
#   "duration_seconds": 120.5
# }
```

### Context & Reports

```python
# Get context for current step
context = agent.get_context()
print(context)  # Formatted knowledge and refs

# Get run report
report = agent.get_report()
# {
#   "id": "...",
#   "goal": "...",
#   "status": "completed",
#   "progress": "4/4 steps",
#   "files_learned": [...],
#   "steps": [...]
# }
```

---

## Claude Code Integration

### How It Works

EriRPG installs hooks into Claude Code that:

1. **PreToolUse** - Blocks Edit/Write/MultiEdit without active preflight
2. **PreCompact** - Saves run state before context compaction
3. **SessionStart** - Reminds about incomplete runs

### Slash Commands

After `eri-rpg install`, these commands are available in Claude Code:

| Command | Description |
|---------|-------------|
| `/eri:execute` | Run the EriRPG agent loop |
| `/eri:start` | Start enforcement at session beginning |
| `/eri:guard` | Intercept all file edits |
| `/eri:status` | Show current run status |

### Enforcement Behavior

**Without active run/preflight:**
```
Edit tool blocked:
╔══════════════════════════════════════════════════════╗
║  ERI-RPG ENFORCEMENT: Preflight required             ║
╠══════════════════════════════════════════════════════╣
║  Run preflight before modifying files:               ║
║    agent.preflight(['path/to/file.py'], 'modify')    ║
╚══════════════════════════════════════════════════════╝
```

**With active preflight:**
- Only files in preflight target list can be edited
- Edits are tracked in run state
- Auto-learn happens on step completion

### Bypass for Quick Fixes

Quick fix mode allows single-file edits without full workflow:

```bash
eri-rpg quick myproject src/config.py "Fix typo"
# Now src/config.py can be edited directly
```

---

## Troubleshooting

### "No active ERI-RPG agent"

**Cause:** Trying to edit files without starting a run.

**Fix:**
```python
from erirpg.agent import Agent
agent = Agent.from_goal("your goal", project_path=".")
# or
agent = Agent.resume(".")
```

### "Preflight required"

**Cause:** Trying to edit without running preflight.

**Fix:**
```python
report = agent.preflight(['file.py'], 'modify')
if report.ready:
    agent.edit_file(...)
```

### "Must learn target modules first"

**Cause:** Preflight requires knowledge of files being edited.

**Fix:**
```bash
eri-rpg learn myproject path/to/file.py
```

Or use `strict=False`:
```python
report = agent.preflight(['file.py'], 'modify', strict=False)
```

### "File not in preflight target list"

**Cause:** Trying to edit a file not included in preflight.

**Fix:** Include all files you plan to edit in preflight:
```python
report = agent.preflight(['file1.py', 'file2.py'], 'modify')
```

### Run stuck or stale

**Fix:**
```bash
# Check status
eri-rpg status myproject

# Clean up stale runs
eri-rpg cleanup myproject --prune

# Start fresh
eri-rpg goal-run myproject
```

### Tests failing after changes

**Fix:**
```bash
# Rollback the file
eri-rpg rollback myproject src/broken.py --code

# Or manually fix and re-run verification
pytest tests/
```

---

## Best Practices

1. **Always preflight** - Even if you're "just making a small change"
2. **Learn before modify** - Understanding prevents mistakes
3. **Use discussions for vague goals** - Clarify before committing to a spec
4. **Use roadmaps for large projects** - Break into manageable phases
5. **Record decisions** - Future you will thank present you
6. **Commit after each phase** - Don't let changes pile up
7. **Run tests often** - Catch issues early

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) and [CHANGES.md](../CHANGES.md) for detailed release notes.

**v2.1** (Current - January 27, 2026)
- Decision logging and deferred ideas
- Domain detection and gray area questions
- Rich session state with handoff support
- Gap closure for verification failures
- Performance optimization (O(n^2) -> O(n) graph algorithms)
- Fixed 46 silent exception handlers
- Fixed nested .eri-rpg directory detection

**v2.0** (January 26, 2026)
- Discuss mode for goal clarification
- Roadmaps for multi-phase projects
- must_haves for spec verification
- Run summaries with decision tracking
- Multi-agent configuration
- Dart language parser
- Smart test selection
- Bash command detection in hooks

**v0.1.0**
- Initial release
- Project registration and indexing
- Knowledge storage
- Quick fix mode
- Claude Code integration
