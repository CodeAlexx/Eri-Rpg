# Usage Guide

## Workflow Overview

EriRPG supports three main workflows:

1. **Quick Fix** - Single-file edits (typos, small bugs)
2. **Guided Work** - Multi-file changes with tracking
3. **Transplant** - Copy features between projects

## 1. Project Setup

### Register a Project

```bash
eri-rpg add myproject /path/to/project
```

Language is auto-detected (Python, Rust, C supported).

### Index the Project

```bash
eri-rpg index myproject
```

This builds a dependency graph used for search and impact analysis.

### List Projects

```bash
eri-rpg list
```

Output:
```
myproject: /path/to/project (python, indexed (today))
```

## 2. Knowledge Management

### Learn About a Module

After reading and understanding a file:

```bash
eri-rpg learn myproject src/utils.py \
  -s "Utility functions for string manipulation" \
  -p "Provides validate_email, slugify, and sanitize_html"
```

Interactive mode (prompts for details):
```bash
eri-rpg learn myproject src/utils.py
```

### Recall Knowledge

```bash
eri-rpg recall myproject src/utils.py
```

Output:
```
# src/utils.py

**Summary**: Utility functions for string manipulation
**Purpose**: Provides validate_email, slugify, and sanitize_html

## Key Functions
- validate_email(s): Returns True if valid email format
- slugify(s): Converts string to URL-safe slug

## Gotchas
- slugify() doesn't handle unicode well
```

### Show All Knowledge

```bash
eri-rpg knowledge myproject
```

## 3. Quick Fix Mode

For simple, single-file changes:

```bash
# Start quick fix
eri-rpg quick myproject src/utils.py "Fix regex in validate_email"

# Output:
# Quick fix mode activated
#   File: src/utils.py
#   Edit the file, then run: eri-rpg quick-done myproject

# Make your edits...

# Complete (commits automatically)
eri-rpg quick-done myproject

# Or cancel and restore original
eri-rpg quick-cancel myproject
```

### Check Status

```bash
eri-rpg quick-status myproject
```

## 4. Search and Analysis

### Find Modules

```bash
eri-rpg find myproject "validation"
```

Output:
```
Matching modules in myproject:

  src/validators.py (0.85)
    Input validation utilities
  src/forms/validation.py (0.72)
    Form field validators
```

### Show Project Structure

```bash
eri-rpg show myproject
```

### Analyze Impact

```bash
eri-rpg impact myproject src/utils.py
```

Shows what depends on a module and what would be affected by changes.

## 5. Run Management

### List Runs

```bash
eri-rpg runs myproject
```

Output:
```
Runs for myproject:

  ○ abc123def456
    Goal: Add user authentication...
    Status: IN_PROGRESS (2/5 steps)
```

### Cleanup Stale Runs

```bash
# List stale runs
eri-rpg cleanup myproject

# Delete runs older than 7 days
eri-rpg cleanup myproject --prune

# Delete runs older than 1 day
eri-rpg cleanup myproject --prune --days 1

# Force delete without confirmation
eri-rpg cleanup myproject --prune --force
```

## 6. Rollback

### Rollback Learning

```bash
# Show available versions
eri-rpg history myproject src/utils.py

# Rollback to previous version (learning only)
eri-rpg rollback myproject src/utils.py

# Rollback to specific version
eri-rpg rollback myproject src/utils.py -v 2
```

### Rollback Code

```bash
# Preview what would be restored
eri-rpg rollback myproject src/utils.py --code --dry-run

# Actually restore the file
eri-rpg rollback myproject src/utils.py --code

# Use git instead of snapshots
eri-rpg rollback myproject src/utils.py --code --use-git
```

## 7. Advanced: Full Agent Workflow

For complex multi-file changes, use the Python API:

```python
from erirpg.agent import Agent

# Create agent for a goal
agent = Agent.from_goal(
    "Add input validation to all forms",
    project_path="/path/to/project"
)

# Execute the workflow
while not agent.is_complete():
    step = agent.current_step()
    context = agent.get_context()

    # Preflight (REQUIRED before edits)
    report = agent.preflight(["src/forms.py"], "modify")
    if not report.ready:
        print(report.format())
        break

    # Make changes via agent methods
    agent.edit_file(
        "src/forms.py",
        old_content="...",
        new_content="...",
        description="Add validation"
    )

    # Complete step (runs verification)
    if agent.complete_step(files_touched=["src/forms.py"]):
        print("Step completed")
    else:
        print("Verification failed!")
        break

# Get report
print(agent.get_report())
```


## 8. Research Phase

Run research before implementing complex features:

```bash
# Auto-detect discovery level
eri-rpg research myproject --goal "add oauth login"

# Force deep research
eri-rpg research myproject --goal "redesign auth" --level 3
```

Discovery levels:
- **0 (skip)**: Internal work, typos, simple fixes
- **1 (quick)**: Single library lookup
- **2 (standard)**: Choosing between options
- **3 (deep)**: Architectural decisions

Output saved to `.eri-rpg/research/RESEARCH.md` with:
- Stack choices (library, version, why, alternatives)
- Pitfalls to avoid
- Anti-patterns
- Code examples

## 9. Wave Execution

Execute plans with parallel support and checkpointing:

```bash
# Execute latest plan
eri-rpg execute myproject

# Execute specific plan
eri-rpg execute myproject --plan-id abc123

# Start fresh (ignore checkpoint)
eri-rpg execute myproject --no-resume

# Start from specific wave
eri-rpg execute myproject --wave 2
```

Features:
- Steps grouped into waves by dependencies
- Parallel execution within waves (if steps are parallelizable)
- Checkpoint after each wave
- Resume from interruption automatically
- Avoid patterns shown before each step


## 8. Research Phase

Run research before implementing complex features:

```bash
# Auto-detect discovery level
eri-rpg research myproject --goal "add oauth login"

# Force deep research
eri-rpg research myproject --goal "redesign auth" --level 3
```

Discovery levels:
- **0 (skip)**: Internal work, typos, simple fixes
- **1 (quick)**: Single library lookup
- **2 (standard)**: Choosing between options
- **3 (deep)**: Architectural decisions

Output saved to `.eri-rpg/research/RESEARCH.md` with:
- Stack choices (library, version, why, alternatives)
- Pitfalls to avoid
- Anti-patterns
- Code examples

## 9. Wave Execution

Execute plans with parallel support and checkpointing:

```bash
# Execute latest plan
eri-rpg execute myproject

# Execute specific plan
eri-rpg execute myproject --plan-id abc123

# Start fresh (ignore checkpoint)
eri-rpg execute myproject --no-resume

# Start from specific wave
eri-rpg execute myproject --wave 2
```

Features:
- Steps grouped into waves by dependencies
- Parallel execution within waves (if steps are parallelizable)
- Checkpoint after each wave
- Resume from interruption automatically
- Avoid patterns shown before each step

## Tips

1. **Start small** - Use quick fix mode for single files
2. **Learn as you go** - Store knowledge when you understand something
3. **Index regularly** - Re-index after major changes: `eri-rpg index myproject`
4. **Check status** - Use `eri-rpg runs myproject` to see what's in progress
5. **Cleanup** - Prune stale runs periodically

## Common Issues

### "No active run" error

The hook is blocking edits. Either:
- Start a quick fix: `eri-rpg quick project file "desc"`
- Or use the full agent workflow with preflight

### Stale preflight state

If you get blocked after a crash:
```bash
# Remove stale state
rm /path/to/project/.eri-rpg/preflight_state.json

# Or cleanup runs
eri-rpg cleanup myproject --prune --force
```

### Knowledge is stale

The file changed since you learned it:
```bash
eri-rpg relearn myproject src/utils.py
```
