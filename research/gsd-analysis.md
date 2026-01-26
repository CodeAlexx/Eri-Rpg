# GSD Analysis

Analysis of [Get Shit Done](https://github.com/glittercowboy/get-shit-done) for EriRPG design.

## Structure

### Commands (`commands/gsd/`)

| Command | Purpose |
|---------|---------|
| `new-project.md` | Full init: questions → research → requirements → roadmap |
| `plan-phase.md` | Research + plan + verify for a phase |
| `execute-phase.md` | Execute plans in parallel waves |
| `discuss-phase.md` | Capture implementation decisions before planning |
| `verify-work.md` | Manual user acceptance testing |
| `map-codebase.md` | Analyze existing codebase structure |
| `progress.md` | Show current position and next steps |
| `quick.md` | Ad-hoc tasks with GSD guarantees |
| `debug.md` | Systematic debugging with persistent state |
| `add-phase.md` | Append phase to roadmap |
| `insert-phase.md` | Insert urgent work between phases |
| `resume-work.md` | Context restoration |
| `pause-work.md` | Context handoff when pausing |

### Agents (`agents/`)

| Agent | Purpose |
|-------|---------|
| `gsd-executor.md` | Executes plans, atomic commits, deviation handling |
| `gsd-planner.md` | Creates PLAN.md with task breakdown and dependencies |
| `gsd-verifier.md` | Verifies phase goals achieved |
| `gsd-plan-checker.md` | Validates plans before execution |
| `gsd-project-researcher.md` | Researches domain (stack, features, architecture, pitfalls) |
| `gsd-research-synthesizer.md` | Combines research outputs |
| `gsd-roadmapper.md` | Creates roadmaps with phase breakdown |
| `gsd-codebase-mapper.md` | Analyzes existing codebase |
| `gsd-debugger.md` | Investigates bugs systematically |
| `gsd-integration-checker.md` | Verifies cross-phase integration |

### Templates (`get-shit-done/templates/`)

- `project.md` - PROJECT.md structure
- `requirements.md` - REQUIREMENTS.md with REQ-IDs
- `roadmap.md` - Phases with success criteria
- `phase-prompt.md` - Plan template
- `summary.md` - Execution summary format
- `research-project/` - STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

## State Management

### Files Created

| File | Purpose | Essential? |
|------|---------|------------|
| `.planning/PROJECT.md` | Vision, context, key decisions | Yes |
| `.planning/REQUIREMENTS.md` | Scoped requirements with REQ-IDs | Yes |
| `.planning/ROADMAP.md` | Phases with success criteria | Yes |
| `.planning/STATE.md` | Current position, decisions, blockers | Yes |
| `.planning/config.json` | Workflow preferences | Optional |
| `.planning/research/` | Domain research outputs | Optional |
| `.planning/phases/XX-name/` | Plan files, summaries, verification | Yes |
| `.planning/codebase/` | Existing code analysis | Optional |

### STATE.md Format

```markdown
## Current Position
Phase: 2 of 5 (Authentication)
Plan: 01 of 03
Status: In progress
Last activity: 2026-01-25 - Started 02-01-PLAN.md

## Decisions Made
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| JWT over sessions | Stateless, edge-compatible | Phase 02 |

## Blockers/Concerns
- None currently

## Session Continuity
Last session: 2026-01-25 14:30
Stopped at: Completed 02-01-PLAN.md
```

### What's Essential vs Bloat

**Essential:**
- PROJECT.md - keeps context across sessions
- ROADMAP.md - knows where you are
- PLAN.md files - executable prompts
- STATE.md - session continuity
- Atomic commits per task

**Bloat:**
- 4 parallel research agents per phase
- Plan checker + verifier + integration checker chains
- Deep research before simple tasks
- Web search for domain knowledge

## Token Usage Analysis

### Where GSD Gets Heavy

1. **Research Phase** (~15-30K tokens)
   - Spawns 4 parallel researchers (stack, features, architecture, pitfalls)
   - Each does web search + synthesis
   - Synthesizer combines outputs

2. **Plan Creation** (~5-10K tokens)
   - Planner creates plans
   - Plan checker verifies
   - Loop until pass

3. **Execution** (~20-50K tokens per plan)
   - Executor implements tasks
   - Per-task commits
   - Deviation handling

4. **Verification** (~5-10K tokens)
   - Verifier checks goals
   - Integration checker for cross-phase

**Total per phase: 50-100K tokens**

### Web Search Triggers

GSD uses web search when:
- `new-project` researches domain ecosystem
- `research-phase` investigates implementation approaches
- Agent encounters unfamiliar library

**Problem:** No concept of "I have onetrainer locally at /path - read THAT"

## What Works

1. **Spec-driven approach**
   - Define requirements → derive roadmap → execute plans
   - Requirements trace to phases

2. **Atomic commits**
   - Each task gets its own commit
   - Clean git history
   - Easy bisect

3. **XML-structured plans**
   - Clear task definitions
   - Verification criteria built-in
   - Executor knows exactly what to do

4. **Fresh context per task**
   - Plans are prompts
   - Executor spawned fresh
   - No context rot within execution

5. **Goal-backward planning**
   - Derive must-haves from user perspective
   - Observable truths, not implementation details

6. **Wave-based parallelism**
   - Independent plans run parallel
   - Dependencies computed upfront

## What's Bloated

1. **100 agents for a bug fix**
   - Every operation spawns agents
   - Researcher + planner + checker + executor + verifier
   - Simple tasks get enterprise treatment

2. **Web search when local code exists**
   - User says "refactor from onetrainer"
   - GSD searches web for random blog posts
   - Actual code is on disk, ignored

3. **No external project registry**
   - No concept of registered projects
   - Can't say "use patterns from project X"
   - Each session starts fresh

4. **No dependency graph**
   - Doesn't know zimage_pipeline affects klein_9b
   - No impact analysis
   - Changes break things unexpectedly

5. **Context rot across files**
   - Writing file 10, forgot interfaces from file 1
   - No persistent knowledge graph
   - Must re-read everything each session

6. **Unwired outputs**
   - Generated code is 60% right
   - Imports wrong
   - Connections missing
   - Glue code absent

## Key Insights for EriRPG

1. **Keep state management** - PROJECT.md, ROADMAP.md, STATE.md are valuable
2. **Keep atomic commits** - per-task commits with clear messages
3. **Keep XML task structure** - clear verification criteria
4. **Drop web research** - read local code instead
5. **Add project registry** - know where external projects live
6. **Add dependency graph** - know what affects what
7. **Add interface tracking** - don't forget what file 1 defined
8. **Add wiring verification** - check connections, not just files
