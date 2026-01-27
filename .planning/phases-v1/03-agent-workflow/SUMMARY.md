# Phase 03: Agent Workflow

## Status: Complete

## Objective

Create spec-driven agent execution with mandatory preflight, tracked edits, and verification.

## What Was Built

1. **Spec System** (`spec.py`)
   - Spec dataclass with goal, steps, constraints
   - SpecStep for individual actions
   - must_haves for verification requirements
   - YAML serialization

2. **Plan & Run** (`agent/plan.py`, `agent/run.py`)
   - Plan generated from spec
   - Step execution tracking
   - Run state persistence
   - Decision and summary tracking

3. **Agent API** (`agent/__init__.py`)
   - `Agent.from_goal()` - Create from goal string
   - `Agent.from_spec()` - Create from spec file
   - `Agent.resume()` - Resume existing run
   - Preflight enforcement
   - File editing through agent

4. **Preflight System** (`preflight.py`)
   - Check learning exists for targets
   - Validate operation type
   - Create snapshots
   - Block edits without preflight

5. **Verification** (`verification.py`)
   - Run pytest/npm test
   - Check must_haves requirements
   - Report pass/fail

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| YAML for specs | Human-writable, supports comments |
| Mandatory preflight | Core enforcement mechanism |
| Agent-only edits | All changes tracked |
| Auto-learn on complete | Keep knowledge fresh |

## Files Created

- `erirpg/spec.py`
- `erirpg/preflight.py`
- `erirpg/verification.py`
- `erirpg/agent/__init__.py`
- `erirpg/agent/plan.py`
- `erirpg/agent/run.py`
- `erirpg/agent/learner.py`

## CLI Commands

```bash
eri-rpg goal-plan <project> "<goal>"  # Generate spec
eri-rpg goal-run <project>            # Execute spec
eri-rpg status <project>              # Show progress
eri-rpg runs <project>                # List runs
```

## Agent API

```python
from erirpg.agent import Agent

agent = Agent.resume(project_path)
while not agent.is_complete():
    step = agent.next_step()
    agent.start_step()
    
    report = agent.preflight(['file.py'], 'modify')
    if report.ready:
        agent.edit_file('file.py', old, new)
        agent.complete_step(files_touched=['file.py'])
```
