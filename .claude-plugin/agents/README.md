# EriRPG Agent Specifications

Agent specs for the EriRPG workflow system.

## Agents

| Agent | Purpose | Spawned By |
|-------|---------|------------|
| planner | Creates execution plans from phase goals | /coder:plan-phase |
| executor | Executes plan tasks and creates summaries | /coder:execute-phase |
| verifier | Validates completed work | /coder:verify-work |
| plan-checker | Reviews plans for quality | /coder:plan-phase --check |
| phase-researcher | Research for phase planning | /coder:plan-phase (Level 2+) |
| roadmapper | Creates project roadmaps | /coder:new-project |
| codebase-mapper | Maps codebase structure | /coder:map-codebase |
| debugger | Diagnoses issues | /coder:doctor |
| research-synthesizer | Synthesizes research findings | Research phases |
| project-researcher | Domain research before roadmap | /coder:new-project |

## File Naming

Files are named without the `eri-` prefix. When skills call:
```
Task(subagent_type="eri-planner", ...)
```

Claude Code loads `planner.md` from this directory.

## Architecture

Agents are specialized Claude personas with:
- Role definition and constraints
- Task-specific instructions
- Success criteria and output format
- Integration with `.planning/` directory structure

## Memory

Agents with `memory: project` retain learning across sessions:
- Patterns discovered
- Mistakes to avoid
- Project-specific conventions
