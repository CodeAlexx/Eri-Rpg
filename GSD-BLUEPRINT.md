# GSD (Get Shit Done) - Complete Technical Blueprint

**Analysis Date:** 2026-01-29
**Source:** https://github.com/glittercowboy/get-shit-done

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 File Structure

```
~/.claude/
├── commands/gsd/          # Slash commands (entry points)
│   ├── new-project.md
│   ├── discuss-phase.md
│   ├── plan-phase.md
│   ├── execute-phase.md
│   ├── verify-work.md
│   ├── quick.md
│   ├── debug.md
│   └── ... (20+ commands)
├── agents/                # Specialized subagents
│   ├── gsd-planner.md
│   ├── gsd-executor.md
│   ├── gsd-verifier.md
│   ├── gsd-plan-checker.md
│   ├── gsd-project-researcher.md
│   ├── gsd-phase-researcher.md
│   ├── gsd-research-synthesizer.md
│   ├── gsd-roadmapper.md
│   ├── gsd-debugger.md
│   ├── gsd-codebase-mapper.md
│   └── gsd-integration-checker.md
├── get-shit-done/
│   ├── workflows/         # Detailed process definitions
│   │   ├── execute-phase.md
│   │   ├── execute-plan.md
│   │   ├── verify-phase.md
│   │   ├── verify-work.md
│   │   ├── diagnose-issues.md
│   │   └── ...
│   ├── templates/         # Output templates
│   │   ├── project.md
│   │   ├── requirements.md
│   │   ├── roadmap.md
│   │   ├── state.md
│   │   ├── summary.md
│   │   └── ...
│   └── references/        # Deep-dive documentation
│       ├── checkpoints.md
│       ├── verification-patterns.md
│       ├── tdd.md
│       └── ...
└── hooks/                 # Runtime hooks
    ├── gsd-statusline.js
    └── gsd-check-update.js
```

### 1.2 Project Artifacts (`.planning/`)

```
.planning/
├── PROJECT.md            # Vision, constraints, requirements, decisions
├── REQUIREMENTS.md       # Scoped v1/v2/out-of-scope with REQ-IDs
├── ROADMAP.md            # Phases with goals, success criteria, mappings
├── STATE.md              # Living memory - position, decisions, blockers
├── config.json           # Workflow preferences
├── research/             # Domain research (optional)
│   ├── STACK.md
│   ├── FEATURES.md
│   ├── ARCHITECTURE.md
│   ├── PITFALLS.md
│   └── SUMMARY.md
├── codebase/             # Brownfield analysis (optional)
│   ├── STACK.md
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md
│   └── CONCERNS.md
├── phases/
│   └── 01-setup/
│       ├── 01-01-PLAN.md
│       ├── 01-01-SUMMARY.md
│       ├── 01-02-PLAN.md
│       ├── 01-02-SUMMARY.md
│       ├── 01-VERIFICATION.md
│       ├── 01-UAT.md
│       └── 01-CONTEXT.md
├── quick/                # Ad-hoc tasks
│   └── 001-fix-bug/
│       ├── PLAN.md
│       └── SUMMARY.md
├── debug/                # Debug sessions
│   ├── active-session.md
│   └── resolved/
└── todos/
    └── pending/
```

---

## 2. COMPLETE WORKFLOW STAGES

### 2.1 Stage: Initialize Project (`/gsd:new-project`)

**Purpose:** Take user from idea to ready-for-planning

**Internal Flow:**
```
Phase 1: Setup
├── Check if project exists (abort if yes)
├── Initialize git repo
└── Detect existing code (brownfield detection)

Phase 2: Brownfield Offer
├── If code exists, offer /gsd:map-codebase first
└── Or proceed to questioning

Phase 3: Deep Questioning
├── Open: "What do you want to build?"
├── Follow threads (challenge vagueness, surface assumptions)
├── Context checklist (background verification)
└── Decision gate: "Ready to create PROJECT.md?"

Phase 4: Write PROJECT.md
├── Synthesize all context
├── Initialize requirements (hypotheses for greenfield)
├── Record key decisions
└── Commit

Phase 5: Workflow Preferences
├── Mode: YOLO vs Interactive
├── Depth: Quick/Standard/Comprehensive
├── Parallelization: On/Off
├── Git tracking: On/Off
├── Model profile: Quality/Balanced/Budget
├── Workflow agents: Research/Plan-Check/Verifier
└── Write config.json, commit

Phase 6: Research (Optional)
├── Spawn 4 parallel researchers:
│   ├── Stack researcher → STACK.md
│   ├── Features researcher → FEATURES.md
│   ├── Architecture researcher → ARCHITECTURE.md
│   └── Pitfalls researcher → PITFALLS.md
├── Spawn synthesizer → SUMMARY.md
└── Commit research

Phase 7: Define Requirements
├── Load research (if exists)
├── Present features by category
├── User selects v1 scope per category
├── Generate REQUIREMENTS.md with REQ-IDs
└── Commit

Phase 8: Create Roadmap
├── Spawn gsd-roadmapper with context
├── Derive phases from requirements (not impose structure)
├── Map every v1 requirement to exactly one phase
├── Derive 2-5 success criteria per phase
├── Validate 100% coverage
├── Write ROADMAP.md, STATE.md
├── User approves or requests revision
└── Commit
```

**Artifacts Created:**
- `.planning/PROJECT.md`
- `.planning/config.json`
- `.planning/research/` (optional)
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

---

### 2.2 Stage: Discuss Phase (`/gsd:discuss-phase N`)

**Purpose:** Capture user's implementation preferences before planning

**Internal Flow:**
```
1. Load phase from ROADMAP.md
2. Analyze phase type (UI, API, content, etc.)
3. Identify gray areas based on phase type:
   - Visual features → Layout, density, interactions, empty states
   - APIs/CLIs → Response format, flags, error handling
   - Content systems → Structure, tone, depth
4. Ask about each gray area user selects
5. Continue until user satisfied
6. Write {phase}-CONTEXT.md
```

**Artifacts Created:**
- `.planning/phases/{XX-name}/{phase}-CONTEXT.md`

**Downstream Consumer:**
- Research reads CONTEXT.md to know what patterns to investigate
- Planner reads CONTEXT.md to know what decisions are locked

---

### 2.3 Stage: Plan Phase (`/gsd:plan-phase N`)

**Purpose:** Create executable plans with verification criteria

**Internal Flow:**
```
Phase 1: Research (if enabled)
├── Spawn gsd-phase-researcher
├── Investigate how to implement this phase
├── Write {phase}-RESEARCH.md
└── Read CONTEXT.md decisions

Phase 2: Planning
├── Spawn gsd-planner with:
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   ├── STATE.md
│   ├── CONTEXT.md (if exists)
│   └── RESEARCH.md (if exists)
├── Apply goal-backward methodology:
│   ├── State the goal (outcome, not task)
│   ├── Derive observable truths (3-7)
│   ├── Derive required artifacts (files)
│   ├── Derive required wiring (connections)
│   └── Identify key links (critical connections)
├── Build dependency graph (needs/creates for each task)
├── Assign waves based on dependencies
├── Group tasks into plans (2-3 tasks max, ~50% context)
├── Write PLAN.md files with XML structure
└── Return planning outcome

Phase 3: Plan Checking (if enabled)
├── Spawn gsd-plan-checker
├── Verify 6 dimensions:
│   ├── Requirement coverage (all requirements have tasks)
│   ├── Task completeness (files, action, verify, done)
│   ├── Dependency correctness (no cycles, valid refs)
│   ├── Key links planned (wiring in task actions)
│   ├── Scope sanity (≤3 tasks, ≤8 files per plan)
│   └── Must-haves derivation (user-observable truths)
├── If issues found:
│   ├── Return issues to planner
│   ├── Planner makes targeted revisions
│   └── Re-check until passed
└── Write updated PLAN.md files

Phase 4: Commit
├── Commit all PLAN.md files
└── Update ROADMAP.md
```

**Artifacts Created:**
- `.planning/phases/{XX-name}/{phase}-RESEARCH.md` (optional)
- `.planning/phases/{XX-name}/{phase}-{NN}-PLAN.md` (multiple)

---

### 2.4 Stage: Execute Phase (`/gsd:execute-phase N`)

**Purpose:** Execute all plans with wave-based parallelization

**Internal Flow:**
```
Phase 1: Discovery
├── Validate phase exists
├── List all PLAN.md files
├── Filter out completed (have SUMMARY.md)
├── Extract wave numbers from frontmatter
└── Group by wave

Phase 2: Wave Execution
For each wave in order:
├── Before spawning: Describe what's being built
├── Read plan contents (@ syntax doesn't work across Task)
├── Spawn gsd-executor for each plan in wave (parallel)
│   Each executor:
│   ├── Load plan, STATE.md
│   ├── Execute tasks sequentially
│   ├── Handle deviations automatically (rules 1-3)
│   ├── Stop for architectural changes (rule 4)
│   ├── Commit each task atomically
│   ├── Create SUMMARY.md
│   └── Update STATE.md
├── Wait for all agents to complete
├── Verify SUMMARYs created
├── Handle checkpoints (see checkpoint flow)
├── Report completion with what was built
└── Proceed to next wave

Phase 3: Verification (if enabled)
├── Spawn gsd-verifier with phase goal
├── Check must_haves against actual codebase:
│   ├── Level 1: Existence (file exists?)
│   ├── Level 2: Substantive (real code, not stub?)
│   └── Level 3: Wired (connected to system?)
├── Create VERIFICATION.md
└── Route by status:
    ├── passed → Continue
    ├── human_needed → Present checklist
    └── gaps_found → Offer /gsd:plan-phase --gaps

Phase 4: Update & Commit
├── Update ROADMAP.md (mark complete)
├── Update STATE.md (position, progress)
├── Update REQUIREMENTS.md (mark requirements Complete)
└── Commit phase completion
```

**Artifacts Created:**
- `.planning/phases/{XX-name}/{phase}-{NN}-SUMMARY.md` (per plan)
- `.planning/phases/{XX-name}/{phase}-VERIFICATION.md`

**Checkpoint Handling Flow:**
```
1. Executor reaches checkpoint task
2. Executor returns structured checkpoint state:
   ├── Completed tasks table with commit hashes
   ├── Current task and blocker
   ├── Checkpoint type and details
   └── What's awaited from user
3. Orchestrator presents to user
4. User responds (approved/issues/decision)
5. Spawn FRESH continuation agent (not resume) with:
   ├── Completed tasks from checkpoint
   ├── Resume point
   └── User response
6. Repeat until plan completes
```

---

### 2.5 Stage: Verify Work (`/gsd:verify-work N`)

**Purpose:** Manual user acceptance testing

**Internal Flow:**
```
1. Load phase goal and must-haves
2. Extract testable deliverables from VERIFICATION.md
3. For each deliverable:
   ├── Present what to test
   ├── User reports: works / broken + description
   └── If broken: spawn gsd-debugger to diagnose
4. For failures found:
   ├── Spawn parallel debuggers
   ├── Each returns ROOT CAUSE FOUND
   ├── Collect diagnoses
   └── Write {phase}-UAT.md with diagnoses
5. If all pass: Mark verified
6. If failures: Offer /gsd:plan-phase --gaps
```

**Artifacts Created:**
- `.planning/phases/{XX-name}/{phase}-UAT.md`

---

### 2.6 Stage: Complete Milestone (`/gsd:complete-milestone`)

**Purpose:** Archive milestone, tag release, prepare for next

**Internal Flow:**
```
1. Verify all phases complete
2. Audit milestone (optional):
   ├── Check cross-phase integration
   ├── Verify E2E flows
   └── Identify gaps for gap phases
3. Archive milestone:
   ├── Create milestone archive entry
   ├── Git tag with version
   └── Update STATE.md
4. Offer /gsd:new-milestone for next version
```

---

## 3. AGENT SPECIFICATIONS

### 3.1 gsd-planner

**Purpose:** Create executable PLAN.md files

**Key Responsibilities:**
- Decompose phases into parallel-optimized plans (2-3 tasks each)
- Build dependency graphs, assign execution waves
- Derive must-haves using goal-backward methodology
- Handle gap closure mode (from verification failures)
- Revise plans based on checker feedback

**Philosophy:**
- Plans ARE prompts (not documents that become prompts)
- Quality degradation curve: 0-30% peak, 30-50% good, 50-70% degrading, 70%+ poor
- 2-3 tasks max per plan, ~50% context budget
- Vertical slices preferred over horizontal layers

**Discovery Levels:**
- Level 0: Skip (pure internal work)
- Level 1: Quick verification (2-5 min, Context7)
- Level 2: Standard research (15-30 min, DISCOVERY.md)
- Level 3: Deep dive (1+ hour, full research)

**Task Anatomy:**
```xml
<task type="auto">
  <name>Task N: Action-oriented name</name>
  <files>src/path/file.ts</files>
  <action>Specific implementation, what to avoid and WHY</action>
  <verify>Command or check to prove completion</verify>
  <done>Measurable acceptance criteria</done>
</task>
```

**Task Types:**
- `auto`: Claude executes autonomously
- `checkpoint:human-verify`: Pauses for user verification
- `checkpoint:decision`: Pauses for user choice
- `checkpoint:human-action`: Truly unavoidable manual steps (rare)

**Goal-Backward Methodology:**
1. State the Goal (outcome, not task)
2. Derive Observable Truths (3-7, user perspective)
3. Derive Required Artifacts (specific files)
4. Derive Required Wiring (connections)
5. Identify Key Links (critical connections)

**must_haves Structure:**
```yaml
must_haves:
  truths:
    - "User can see existing messages"
    - "User can send a message"
  artifacts:
    - path: "src/components/Chat.tsx"
      provides: "Message list rendering"
      min_lines: 30
  key_links:
    - from: "Chat.tsx"
      to: "/api/chat"
      via: "fetch in useEffect"
```

---

### 3.2 gsd-executor

**Purpose:** Execute PLAN.md files with atomic commits

**Key Responsibilities:**
- Execute tasks sequentially within plans
- Handle deviations automatically
- Pause at checkpoints, return structured state
- Create per-task commits
- Produce SUMMARY.md

**Deviation Rules:**
```
RULE 1: Auto-fix bugs
  - Fix immediately, track for Summary
  - Examples: Logic errors, type errors, security vulnerabilities

RULE 2: Auto-add missing critical functionality
  - Add immediately, track for Summary
  - Examples: Missing error handling, input validation, auth checks

RULE 3: Auto-fix blocking issues
  - Fix immediately to unblock
  - Examples: Missing dependency, wrong imports, config errors

RULE 4: Ask about architectural changes
  - STOP, return checkpoint
  - Examples: New database table, switching libraries, API changes
```

**Priority:** If Rule 4 applies → STOP. If Rules 1-3 apply → Fix automatically.

**Commit Protocol:**
```bash
# Per-task commit
{type}({phase}-{plan}): {task-name}

# Types: feat, fix, test, refactor, perf, docs, style, chore
```

**Checkpoint Return Format:**
```markdown
## CHECKPOINT REACHED

**Type:** [human-verify | decision | human-action]
**Plan:** {phase}-{plan}
**Progress:** {completed}/{total} tasks complete

### Completed Tasks
| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | [name] | [hash] | [files] |

### Current Task
**Task {N}:** [name]
**Status:** [blocked | awaiting verification]
**Blocked by:** [specific blocker]

### Checkpoint Details
[Type-specific content]

### Awaiting
[What user needs to do]
```

---

### 3.3 gsd-verifier

**Purpose:** Verify phase goal achievement (not task completion)

**Core Principle:** Task completion ≠ Goal achievement

**Three-Level Verification:**
```
Level 1: Existence
├── Does the file exist?
└── MISSING → fail

Level 2: Substantive
├── Has real implementation (not stub)?
├── Check: Line count, stub patterns, exports
└── STUB → fail

Level 3: Wired
├── Connected to the system?
├── Check: Imported, used, calls correct APIs
└── ORPHANED → warning
```

**Key Link Patterns:**
- Component → API: `fetch/axios call + response handling`
- API → Database: `prisma/db query + result returned`
- Form → Handler: `onSubmit + actual implementation`
- State → Render: `useState + JSX rendering`

**Stub Detection Patterns:**
```bash
# Comment-based stubs
grep -E "TODO|FIXME|XXX|HACK|PLACEHOLDER"

# Placeholder text
grep -E "placeholder|coming soon|will be here"

# Empty implementations
grep -E "return null|return \{\}|return \[\]"

# Console.log only
grep -E "console\.log.*only"
```

**Verification Status:**
- `passed`: All must-haves verified
- `gaps_found`: One or more truths failed
- `human_needed`: Can't verify programmatically

**Gap Output Structure:**
```yaml
gaps:
  - truth: "User can see existing messages"
    status: failed
    reason: "Chat.tsx exists but doesn't fetch from API"
    artifacts:
      - path: "src/components/Chat.tsx"
        issue: "No useEffect with fetch call"
    missing:
      - "API call in useEffect to /api/chat"
      - "State for storing fetched messages"
```

---

### 3.4 gsd-plan-checker

**Purpose:** Verify plans WILL achieve goal (before execution)

**6 Verification Dimensions:**

**1. Requirement Coverage**
- Every phase requirement has task(s)?
- No vague tasks covering multiple requirements?

**2. Task Completeness**
- All `<task type="auto">` have: files, action, verify, done?
- Actions specific enough for clean execution?

**3. Dependency Correctness**
- All depends_on references exist?
- No circular dependencies?
- Wave numbers consistent?

**4. Key Links Planned**
- Wiring mentioned in task actions?
- Component calls API, API queries DB?

**5. Scope Sanity**
- ≤3 tasks per plan?
- ≤8 files per plan?
- Complex domains split properly?

**6. Must-Haves Derivation**
- Truths are user-observable (not implementation details)?
- Artifacts support truths?
- Key links cover critical wiring?

**Issue Severity:**
- `blocker`: Must fix before execution
- `warning`: Should fix, execution may work
- `info`: Minor improvements

---

### 3.5 gsd-project-researcher

**Purpose:** Research domain ecosystem before roadmap

**Research Modes:**
- Ecosystem (default): What tools/approaches exist?
- Feasibility: Can we do X? Blockers?
- Comparison: A vs B - which and why?

**Tool Strategy:**
1. Context7 First (library APIs, current docs)
2. Official Docs via WebFetch
3. WebSearch for ecosystem discovery
4. Verification Protocol (cross-reference)

**Confidence Levels:**
- HIGH: Context7, official docs, official releases
- MEDIUM: WebSearch verified with official source
- LOW: WebSearch only, single source (flag for validation)

**Output Files:**
- `STACK.md`: Technology recommendations
- `FEATURES.md`: Table stakes, differentiators, anti-features
- `ARCHITECTURE.md`: System structure patterns
- `PITFALLS.md`: Common mistakes, prevention strategies
- `SUMMARY.md`: Executive synthesis with roadmap implications

---

### 3.6 gsd-roadmapper

**Purpose:** Create phase structure from requirements

**Key Responsibilities:**
- Derive phases from requirements (not impose structure)
- Validate 100% requirement coverage
- Apply goal-backward thinking at phase level
- Create 2-5 success criteria per phase

**Phase Derivation:**
1. Group requirements by category
2. Identify dependencies
3. Create delivery boundaries (complete, verifiable capabilities)
4. Assign every v1 requirement to exactly one phase

**Good Phase Patterns:**
```
Foundation → Features → Enhancement
├── Phase 1: Setup (scaffolding, CI/CD)
├── Phase 2: Auth (user accounts)
├── Phase 3: Core Content (main features)
├── Phase 4: Social (sharing)
└── Phase 5: Polish (performance)
```

**Anti-Pattern (Horizontal Layers):**
```
Phase 1: All database models ← Too coupled
Phase 2: All API endpoints ← Can't verify
Phase 3: All UI components ← Nothing works until end
```

---

### 3.7 gsd-debugger

**Purpose:** Systematic investigation using scientific method

**Philosophy:**
- User = Reporter, Claude = Investigator
- Don't ask user what's causing bug (investigate yourself)
- Hypothesis must be falsifiable
- One variable at a time

**Investigation Techniques:**
- Binary Search / Divide and Conquer
- Rubber Duck Debugging
- Minimal Reproduction
- Working Backwards
- Differential Debugging
- Git Bisect

**Debug File Protocol:**
```markdown
---
status: gathering | investigating | fixing | verifying | resolved
trigger: "[verbatim user input]"
---

## Current Focus
hypothesis: [current theory]
test: [how testing]
next_action: [immediate next step]

## Symptoms
expected: [should happen]
actual: [actually happens]

## Eliminated
- hypothesis: [wrong theory]
  evidence: [what disproved it]

## Evidence
- checked: [what examined]
  found: [what observed]

## Resolution
root_cause: [when found]
fix: [when applied]
```

**Modes:**
- `find_root_cause_only`: Diagnose but don't fix (for UAT)
- `find_and_fix`: Full cycle (default)

---

### 3.8 gsd-codebase-mapper

**Purpose:** Analyze existing codebases (brownfield)

**Focus Areas:**
- `tech`: STACK.md, INTEGRATIONS.md
- `arch`: ARCHITECTURE.md, STRUCTURE.md
- `quality`: CONVENTIONS.md, TESTING.md
- `concerns`: CONCERNS.md

**Key Principle:** Document quality over brevity. Include file paths with backticks.

---

## 4. ARTIFACT SPECIFICATIONS

### 4.1 PLAN.md Structure

```markdown
---
phase: XX-name
plan: NN
type: execute
wave: N                     # Pre-computed execution wave
depends_on: []              # Plan IDs this requires
files_modified: []          # Files this plan touches
autonomous: true            # false if has checkpoints
user_setup: []              # Human-required setup (optional)
must_haves:
  truths: []                # Observable behaviors
  artifacts: []             # Files that must exist
  key_links: []             # Critical connections
---

<objective>
[What this plan accomplishes]

Purpose: [Why this matters]
Output: [What artifacts will be created]
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: [Action-oriented name]</name>
  <files>path/to/file.ext</files>
  <action>[Specific implementation]</action>
  <verify>[Command or check]</verify>
  <done>[Acceptance criteria]</done>
</task>

</tasks>

<verification>
[Overall phase checks]
</verification>

<success_criteria>
[Measurable completion]
</success_criteria>
```

---

### 4.2 SUMMARY.md Structure

```markdown
---
phase: XX-name
plan: NN
subsystem: [category]
tags: [tech keywords]
requires: [prior phases]
provides: [what delivered]
affects: [future phases]
tech-stack:
  added: [new libraries]
  patterns: [patterns established]
key-files:
  created: [files]
  modified: [files]
decisions: [from "Decisions Made"]
duration: [minutes]
completed: YYYY-MM-DD
---

# Phase [X] Plan [Y]: [Name] Summary

**One-liner:** [Substantive summary - not "Authentication implemented"]

## Deliverables
[What was built]

## Tasks Completed
| Task | Name | Commit | Files |
|------|------|--------|-------|

## Decisions Made
[Decisions with rationale]

## Deviations from Plan
[Auto-fixed issues or "None"]

## Next Phase Readiness
[Blockers, concerns for future]
```

---

### 4.3 STATE.md Structure

```markdown
# Project State

## Project Reference
See: .planning/PROJECT.md

**Core value:** [One-liner]
**Current focus:** [Phase name]

## Current Position
Phase: [X] of [Y] ([Phase name])
Plan: [A] of [B]
Status: [Ready to plan | Planning | Executing | Complete]
Last activity: [YYYY-MM-DD] — [What happened]

Progress: [░░░░░░░░░░] 0%

## Performance Metrics
**Velocity:**
- Total plans completed: [N]
- Average duration: [X] min

## Accumulated Context

### Decisions
[Recent decisions affecting current work]

### Pending Todos
[From /gsd:add-todo]

### Blockers/Concerns
[Issues affecting future work]

## Session Continuity
Last session: [YYYY-MM-DD HH:MM]
Stopped at: [Description]
Resume file: [Path or "None"]
```

---

### 4.4 VERIFICATION.md Structure

```markdown
---
phase: XX-name
verified: YYYY-MM-DDTHH:MM:SSZ
status: passed | gaps_found | human_needed
score: N/M must-haves verified
gaps: []  # If gaps_found
human_verification: []  # If human_needed
---

# Phase {X}: {Name} Verification Report

**Phase Goal:** [from ROADMAP.md]
**Status:** [status]

## Goal Achievement

### Observable Truths
| # | Truth | Status | Evidence |
|---|-------|--------|----------|

### Required Artifacts
| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|

### Key Link Verification
| From | To | Via | Status |

### Gaps Summary
[What's missing and why]
```

---

## 5. KEY PATTERNS & CONCEPTS

### 5.1 Context Engineering

**Quality Degradation Curve:**
| Context Usage | Quality | State |
|---------------|---------|-------|
| 0-30% | PEAK | Thorough, comprehensive |
| 30-50% | GOOD | Confident, solid |
| 50-70% | DEGRADING | Efficiency mode |
| 70%+ | POOR | Rushed, minimal |

**Rule:** Plans should complete within ~50% context.

**Split Triggers:**
- >3 tasks per plan
- Multiple subsystems
- >5 files per task
- Checkpoint + implementation in same plan

### 5.2 Wave-Based Execution

**Wave Assignment:**
```
if plan.depends_on is empty:
  plan.wave = 1
else:
  plan.wave = max(waves[dep] for dep in plan.depends_on) + 1
```

**Execution:**
- All plans in wave run in parallel (fresh subagents)
- Wait for wave completion before next
- Task tool blocks until all complete
- No polling, no background agents

### 5.3 Checkpoint Flow

```
Executor → Checkpoint → Returns state
                ↓
Orchestrator ← Presents to user
                ↓
User responds → Fresh continuation agent spawned
                ↓
Continuation agent resumes from state
```

**Why fresh agent?** Resume relies on serialization that breaks with parallel tool calls. Fresh agents with explicit state are more reliable.

### 5.4 Deviation Handling

**Automatic (Rules 1-3):**
- Bugs: Fix immediately, document
- Missing critical: Add immediately, document
- Blockers: Fix to unblock, document

**Manual (Rule 4):**
- Architectural changes: STOP, return checkpoint, await user decision

### 5.5 Goal-Backward Verification

**Forward Planning:** "What should we build?"
**Goal-Backward:** "What must be TRUE for the goal to be achieved?"

1. Observable truths (user perspective)
2. Required artifacts (specific files)
3. Required wiring (connections)
4. Key links (critical points)

**Verifier checks actual code, not SUMMARY claims.**

---

## 6. CONFIGURATION

### 6.1 config.json

```json
{
  "mode": "yolo|interactive",
  "depth": "quick|standard|comprehensive",
  "parallelization": true,
  "commit_docs": true,
  "model_profile": "quality|balanced|budget",
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true
  }
}
```

### 6.2 Model Profiles

| Agent | quality | balanced | budget |
|-------|---------|----------|--------|
| gsd-project-researcher | opus | sonnet | haiku |
| gsd-roadmapper | opus | sonnet | sonnet |
| gsd-planner | opus | sonnet | sonnet |
| gsd-executor | opus | sonnet | sonnet |
| gsd-verifier | sonnet | sonnet | haiku |

### 6.3 Depth Calibration

| Depth | Typical Phases | Plans/Phase |
|-------|----------------|-------------|
| Quick | 3-5 | 1-3 |
| Standard | 5-8 | 3-5 |
| Comprehensive | 8-12 | 5-10 |

---

## 7. COMMANDS REFERENCE

### Core Workflow
| Command | Purpose |
|---------|---------|
| `/gsd:new-project` | Initialize: questions → research → requirements → roadmap |
| `/gsd:discuss-phase N` | Capture implementation decisions |
| `/gsd:plan-phase N` | Research + plan + verify plans |
| `/gsd:execute-phase N` | Execute plans in parallel waves |
| `/gsd:verify-work N` | Manual acceptance testing |
| `/gsd:complete-milestone` | Archive milestone, tag release |
| `/gsd:new-milestone` | Start next version |

### Phase Management
| Command | Purpose |
|---------|---------|
| `/gsd:add-phase` | Append phase to roadmap |
| `/gsd:insert-phase N` | Insert urgent work between phases |
| `/gsd:remove-phase N` | Remove future phase |
| `/gsd:list-phase-assumptions N` | See Claude's approach |
| `/gsd:plan-milestone-gaps` | Create phases for audit gaps |

### Navigation
| Command | Purpose |
|---------|---------|
| `/gsd:progress` | Current position, what's next |
| `/gsd:help` | All commands and usage |
| `/gsd:settings` | Configure workflow preferences |

### Utilities
| Command | Purpose |
|---------|---------|
| `/gsd:quick` | Ad-hoc task with GSD guarantees |
| `/gsd:debug` | Systematic debugging |
| `/gsd:add-todo` | Capture idea for later |
| `/gsd:pause-work` | Create handoff when stopping |
| `/gsd:resume-work` | Restore from last session |
| `/gsd:map-codebase` | Analyze existing codebase |

---

## 8. IMPLEMENTATION NOTES FOR ERIRPG

### 8.1 What GSD Does Well

1. **Context Engineering**: Clear 50% budget, split triggers, degradation awareness
2. **Goal-Backward Verification**: Must-haves derived from outcomes, not tasks
3. **Wave-Based Execution**: Parallel plans, fresh subagents, no context bleed
4. **Checkpoint Flow**: Structured state, fresh continuation, clear handoff
5. **Deviation Rules**: Clear hierarchy (1-3 auto, 4 manual)
6. **Three-Level Verification**: Exists → Substantive → Wired
7. **Stub Detection**: Concrete patterns for finding incomplete code

### 8.2 Key Differences from EriRPG

| Aspect | GSD | EriRPG |
|--------|-----|--------|
| Knowledge | Research on-demand | Pre-indexed graph |
| State | STATE.md (file) | CLI + JSON state |
| Phases | Derived from requirements | Spec-driven |
| Verification | Codebase scanning | Test execution |
| Recovery | .continue-here files | Run state in JSON |

### 8.3 Patterns to Consider Adopting

1. **must_haves structure** in specs for verification
2. **Three-level verification** for completion checks
3. **Wave assignment algorithm** for parallel execution
4. **Checkpoint return format** for subagent handoffs
5. **Deviation rules hierarchy** for autonomous operation
6. **SUMMARY.md frontmatter** for dependency tracking
7. **Goal-backward methodology** for requirement derivation

---

## 9. APPENDIX: XML TASK FORMATS

### Standard Task
```xml
<task type="auto">
  <name>Task N: Action-oriented name</name>
  <files>src/path/file.ts</files>
  <action>Specific implementation with WHY</action>
  <verify>Command or check</verify>
  <done>Acceptance criteria</done>
</task>
```

### Checkpoint: Human Verify
```xml
<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Description</what-built>
  <how-to-verify>
    1. Steps
    2. For
    3. User
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>
```

### Checkpoint: Decision
```xml
<task type="checkpoint:decision" gate="blocking">
  <decision>What needs deciding</decision>
  <context>Why this matters</context>
  <options>
    <option id="a">
      <name>Option A</name>
      <pros>Benefits</pros>
      <cons>Tradeoffs</cons>
    </option>
  </options>
  <resume-signal>Select: a, b, or ...</resume-signal>
</task>
```

### TDD Task
```xml
<task type="auto" tdd="true">
  <name>Feature Name (TDD)</name>
  <files>src/feature.ts, src/feature.test.ts</files>
  <behavior>
    Expected behavior specification
    Cases: input -> expected output
  </behavior>
  <implementation>How to implement once tests pass</implementation>
</task>
```

---

*Blueprint generated from GSD v1.x source analysis*
