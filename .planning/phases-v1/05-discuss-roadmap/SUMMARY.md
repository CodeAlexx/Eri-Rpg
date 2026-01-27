# Phase 05: Discuss & Roadmap

## Status: Complete

## Objective

Add goal clarification (discuss mode) and multi-phase planning (roadmaps) before spec generation.

## What Was Built

1. **Discussion Mode** (`discuss.py`)
   - Detect vague goals
   - Generate clarifying questions
   - Store Q&A for context
   - Enrich goal with answers

2. **Roadmap System** (`memory.py`)
   - Milestone dataclass
   - Roadmap with phases
   - Progress tracking
   - Link specs/runs to milestones

3. **CLI Commands**
   - discuss, discuss-answer, discuss-show, discuss-resolve, discuss-clear
   - roadmap, roadmap-add, roadmap-next, roadmap-edit

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Embedded in Discussion | Roadmap belongs to a goal discussion |
| Auto-detect vague goals | Help users who don't know they need discussion |
| Questions by goal type | Different questions for add/fix/refactor |
| Milestone → Spec linking | Track which specs implement which phases |

## Files Created/Modified

- `erirpg/discuss.py` (new)
- `erirpg/memory.py` (added Discussion, Milestone, Roadmap)
- `erirpg/cli.py` (added commands)

## Workflow

```
1. User has vague goal: "improve the API"
2. EriRPG detects vagueness, suggests discussion
3. User answers clarifying questions
4. User adds roadmap phases
5. Discussion enriches goal context
6. Spec generated with full context
```
