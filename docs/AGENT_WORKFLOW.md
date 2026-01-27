# Agent Workflow

The practical, enforced, "smart by default" workflow.

## High Level

1. Start or resume a run
2. Start the next step
3. Preflight the exact files you intend to touch
4. Edit only via Agent APIs
5. Complete the step (auto-verification + auto-learn)
6. Repeat until complete

## Minimal Execution Loop
```python
from erirpg.agent import Agent

goal = "refactor loader config to support xyz"
project_path = "."

agent = Agent.resume(project_path) or Agent.from_goal(goal, project_path=project_path)

while not agent.is_complete():
    step = agent.start_step() or agent.current_step()
    context = agent.get_context()
    
    # Pick targets for this step
    targets = ["toolkit/config/loader.py"]
    
    # Mandatory preflight
    report = agent.preflight(targets, operation="refactor", strict=True)
    if not report.ready:
        print(report.format())
        break
    
    # Make changes ONLY via agent APIs
    # agent.edit_file("toolkit/config/loader.py", old, new, description="...")
    
    # Complete step: runs verification, auto-learns, auto-commits
    ok = agent.complete_step(files_touched=targets, notes="Refactor loader config")
    if not ok:
        break

print(agent.get_report())
```

## Smart Defaults

| Feature | Default | Override |
|---------|---------|----------|
| Verification | Mandatory | `skip_verification=True` |
| Auto-learning | On | - |
| Auto-commit | On | `auto_commit=False` |
| Preflight enforcement | Strict | `strict=False` |

## Practical Tips

- **Keep steps small** (1-3 files) for fast verification and easy rollback
- **Re-run preflight** if new files become necessary mid-step
- **Add verification.json** for deterministic tests

## Error Recovery
```python
# If preflight fails (missing learnings)
if not report.ready:
    for file in report.must_learn_first:
        # Learn the missing module
        agent.learn(file)
    # Re-run preflight
    report = agent.preflight(targets, operation="refactor")

# If verification fails
ok = agent.complete_step(files_touched=targets, notes="...")
if not ok:
    # Option 1: Fix and retry
    agent.edit_file(...)
    ok = agent.complete_step(files_touched=targets, notes="Fixed")
    
    # Option 2: Rollback changes
    agent.rollback(targets)
    
    # Option 3: Skip verification (use sparingly)
    agent.complete_step(..., skip_verification=True)
```

## Quick Fix vs Full Run

| Scenario | Use |
|----------|-----|
| Single file, simple fix | `eri-rpg quick` |
| Multi-file refactor | `Agent.from_goal()` |
| Feature transplant | `Agent.from_spec()` with take mode |

```python
# Quick fix (no ceremony)
from erirpg.quick import QuickAgent
q = QuickAgent("myproject")
q.fix("src/utils.py", "fix import")
# ... make edit ...
q.done()  # commits

# Full run (enforced workflow)
agent = Agent.from_goal("refactor config system", project_path=".")
# ... full loop ...
```

## Resume After Compaction

EriRPG survives context compaction:
```python
# After session restart
agent = Agent.resume(project_path)
if agent:
    print(f"Resuming: {agent.spec.goal}")
    print(f"Current step: {agent.current_step().description}")
    # Continue where you left off
else:
    # No incomplete run, start fresh
    agent = Agent.from_goal(goal, project_path=project_path)
```

## Debugging
```python
# Check run state
print(agent.progress())
print(agent.get_report())

# Check preflight state
report = agent.preflight(targets, operation="refactor")
print(report.format())  # Shows blockers, impact zone, readiness

# Check what's learned
from erirpg.memory import load_knowledge
k = load_knowledge(project_path)
for path, learning in k.learnings.items():
    print(f"{path}: {learning.summary}")
```

## Common Patterns

### Learn Before Refactor
```python
# Learn all files in impact zone first
for file in report.impact_zone:
    if file not in k.learnings:
        agent.learn(file)
```

### Atomic Multi-File Change
```python
# Preflight ALL files at once
targets = ["src/a.py", "src/b.py", "src/c.py"]
report = agent.preflight(targets, operation="refactor")

# Edit all, then complete once
agent.edit_file("src/a.py", ...)
agent.edit_file("src/b.py", ...)
agent.edit_file("src/c.py", ...)
agent.complete_step(files_touched=targets, notes="Atomic refactor")
# Single commit, single verification
```

### Bail Out Safely
```python
# Something went wrong, rollback changes
agent.rollback(targets)  # Restores files from snapshots
agent.fail_step("Couldn't complete due to X")  # Marks step as failed
# Git still has your commits if you need them
```

## Available Agent Methods

| Method | Purpose |
|--------|---------|
| `from_goal(goal, project_path)` | Create agent from goal string |
| `from_spec(spec_path)` | Create agent from spec file |
| `resume(project_path)` | Resume incomplete run |
| `is_complete()` | Check if all steps done |
| `start_step()` | Begin next step |
| `current_step()` | Get current step |
| `next_step()` | Get next pending step |
| `preflight(files, operation)` | Validate before editing |
| `edit_file(path, old, new, desc)` | Edit existing file |
| `write_file(path, content)` | Write new file |
| `complete_step(files, notes)` | Finish step with verification |
| `verify_step()` | Run verification manually |
| `skip_step(reason)` | Skip current step |
| `fail_step(reason)` | Mark step as failed |
| `rollback(files)` | Restore files from snapshots |
| `learn(file)` | Store learning about file |
| `recall(file)` | Get stored learning |
| `get_context()` | Get context for current step |
| `get_report()` | Get full run report |
| `progress()` | Get progress summary |
