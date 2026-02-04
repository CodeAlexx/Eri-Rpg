# Eri-Coder Command Reference

## What is Eri-Coder?

**Eri-coder is for building new applications from scratch using natural language.**

You describe what you want, Claude handles all the coding. No programming knowledge required.

### When to Use Eri-Coder

- Starting a brand new project from zero
- "Vibe coding" - describing features in plain English
- Building complete applications end-to-end
- Adding major features to existing projects
- When you want Claude to handle research, planning, and implementation

### The Workflow

1. **Describe** your app in plain English
2. **Answer** questions about requirements
3. **Approve** the roadmap
4. **Watch** Claude build it phase by phase
5. **Verify** each phase works
6. **Run** your completed app

---

## Commands (Alphabetical)

### /coder:add-feature

**Purpose:** Add a new feature to an existing codebase (brownfield development).

**Usage:**
```
# Standard mode - new feature
/coder:add-feature "<description>"
/coder:add-feature "User authentication with email/password"

# Reference mode - port from another program
/coder:add-feature <target> <feature> "<description>" --reference <source>/<section>
/coder:add-feature eritrainer sana "Sana model training" --reference onetrainer/models/sana
```

**When to use:**
- Adding functionality to a working project
- Porting features from one codebase to another
- When you don't want to restructure the whole app
- After running `/coder:map-codebase` to understand existing code

**Reference mode:**
- Loads source behavior spec (what it does, not how)
- Scans target for interface requirements
- Checks ownership and side effect compatibility
- Creates feature spec with implementation plan

**Why needed:** Lets you add features that respect existing architecture. For porting, extracts behavior so you implement in target's native style.

---

### /coder:add-phase

**Purpose:** Append a new phase to the end of the current milestone roadmap.

**Usage:**
```
/coder:add-phase "<name>" "<goal>"
/coder:add-phase "Analytics" "Track user behavior and generate reports"
```

**When to use:**
- Discovered new requirements after initial planning
- Want to extend v1 scope
- Adding polish phase after core features

**Why needed:** Requirements evolve. This lets you extend the roadmap without disrupting existing phases.

---

### /coder:add-todo

**Purpose:** Capture an idea for later without interrupting current work.

**Usage:**
```
/coder:add-todo "<idea>"
/coder:add-todo "Add dark mode support"
/coder:add-todo "Consider caching for performance"
```

**When to use:**
- Mid-phase and you think of something for later
- Ideas that don't belong in current scope
- Things to consider for v2

**Why needed:** Don't lose good ideas. Captures them to `.planning/todos/` for later review.

---

### /coder:blueprint

**Purpose:** Manage section-level blueprints of complex programs for documentation and feature porting.

**Usage:**
```
# List all blueprints
/coder:blueprint list

# Add a blueprint section
/coder:blueprint add <program> <section> "<description>"
/coder:blueprint add onetrainer models/flux "Flux model training"

# Add with behavior extraction (for porting)
/coder:blueprint add onetrainer models/sana "Sana model" --extract-tests

# Load a blueprint
/coder:blueprint load onetrainer/models/sana

# Load only behavior spec (portable)
/coder:blueprint load onetrainer/models/sana --behavior

# Check blueprint status
/coder:blueprint status onetrainer

# View dependencies
/coder:blueprint deps onetrainer
```

**Flags:**
- `--path <path>` - Source code path to analyze
- `--depends <sections>` - Comma-separated dependencies
- `--extract-behavior` - Create portable -BEHAVIOR.md file
- `--extract-tests` - Also extract test contracts (implies --extract-behavior)
- `--behavior` - Load only behavior spec (with load command)
- `--status <status>` - Set status: complete, in_progress, not_started, outdated

**When to use:**
- Documenting complex programs section by section
- Preparing features for porting to another language
- Creating architectural reference for large codebases

**Why needed:** Blueprints provide structured program documentation. Behavior specs enable cross-language porting by extracting WHAT not HOW.

**See also:** [docs/BLUEPRINT-BEHAVIOR.md](BLUEPRINT-BEHAVIOR.md) for complete reference.

---

### /coder:compare

**Purpose:** Evaluate multiple implementation approaches before committing to one.

**Usage:**
```
/coder:compare "<approach-1>" "<approach-2>"
/coder:compare "JWT auth" "Session auth"
/coder:compare --worktree "React" "Vue"          # Prototype in separate worktrees
/coder:compare --branch feature-a feature-b      # Compare existing branches
```

**When to use:**
- Major architectural decisions
- Choosing between libraries or frameworks
- When both options seem equally valid
- Before committing to irreversible choices

**Why needed:** Big decisions deserve research. Spawns parallel agents to analyze each approach, generates comparison matrix, provides recommendation with rationale.

---

### /coder:complete-milestone

**Purpose:** Archive current milestone, tag release, prepare for next version.

**Usage:**
```
/coder:complete-milestone <version>
/coder:complete-milestone v1.0
/coder:complete-milestone v1.0 --tag --changelog
```

**When to use:**
- All phases in current milestone are verified
- Ready to ship a version
- Moving on to next milestone

**Why needed:** Clean separation between versions. Archives `.planning/phases/` to `.planning/archive/v1.0/`, creates git tag, generates changelog.

---

### /coder:cost

**Purpose:** Estimate token usage and API cost before expensive operations.

**Usage:**
```
/coder:cost                     # Estimate remaining project cost
/coder:cost --phase 3           # Estimate specific phase
/coder:cost --plan 2-03         # Estimate specific plan
/coder:cost --compare           # Compare model costs
```

**When to use:**
- Before large phases to budget
- Deciding between Opus/Sonnet/Local
- Planning API spend

**Why needed:** Shows estimated tokens and cost per model tier (Opus ~$0.015/1K, Sonnet ~$0.003/1K, Local ~$0). Helps make informed cost decisions.

---

### /coder:debug

**Purpose:** Systematic debugging using scientific method.

**Usage:**
```
/coder:debug "<symptom>"
/coder:debug "Login fails after password reset"
/coder:debug "API returns 500 on POST /users"
```

**When to use:**
- Bug that isn't immediately obvious
- Issues that span multiple files
- When you've tried obvious fixes

**Why needed:** Uses hypothesis-test-observe loop. Spawns `eri-debugger` agent that investigates systematically, documents findings, and fixes root cause.

---

### /coder:diff

**Purpose:** Show changes since a checkpoint, phase, or commit.

**Usage:**
```
/coder:diff                     # Changes since last checkpoint
/coder:diff --phase 2           # Changes in phase 2
/coder:diff --commit abc123     # Changes since commit
/coder:diff --stat              # Summary only
```

**When to use:**
- Review what was changed before committing
- Understand scope of a phase
- Audit changes before pushing

**Why needed:** Quick visibility into what Claude has done. Shows files changed, lines added/removed, and summary.

---

### /coder:discuss-phase

**Purpose:** Capture implementation decisions for a phase before planning.

**Usage:**
```
/coder:discuss-phase <N>
/coder:discuss-phase 2
```

**Philosophy:** User = visionary, Claude = builder. You know how it should look/feel. Claude handles technical implementation.

**Features:**
- **Scope guardrail** - Prevents scope creep, captures deferred ideas for later
- **Gray area identification** - Phase-specific decisions, not generic questions
- **User selection** - Pick which areas to discuss (multiSelect)
- **4-question batches** - Natural conversation with check-ins
- **Claude's Discretion** - Captures "you decide" responses
- **Deferred Ideas** - Scope creep suggestions saved for future phases

**When to use:**
- Before `/coder:plan-phase`
- When phase has ambiguous requirements
- To capture constraints and preferences

**Output:** Creates `.planning/phases/XX/CONTEXT.md` with:
- Phase boundary (scope anchor)
- Implementation decisions
- Claude's discretion areas
- Deferred ideas

**Why needed:** Surfaces decisions before planning. CONTEXT.md feeds into planner and researcher agents so they honor your locked decisions.

---

### /coder:execute-phase

**Purpose:** Execute all plans for a phase using wave-based parallelization.

**Usage:**
```
/coder:execute-phase <N>
/coder:execute-phase 1
/coder:execute-phase 2 --plan 3    # Start from specific plan
```

**When to use:**
- After `/coder:plan-phase` completes
- To build the actual code
- In YOLO mode, runs automatically

**Why needed:** The actual code writing happens here. Executes plans in dependency order, commits after each plan, handles deviations, triggers verification.

---

### /coder:handoff

**Purpose:** Generate comprehensive context documentation for humans or AI.

**Usage:**
```
/coder:handoff                     # Full project handoff
/coder:handoff --for human         # Optimized for human reader
/coder:handoff --for ai            # Optimized for AI continuation
/coder:handoff --brief             # Summary only
```

**When to use:**
- Transitioning project to another developer
- Handing off to different AI session
- Extended pause (weeks/months)
- Onboarding team members

**Why needed:** Creates `HANDOFF.md` (human-readable) and `HANDOFF-AI.md` (structured for AI). Includes architecture, decisions, current state, and resume instructions.

---

### /coder:init

**Purpose:** Session context recovery after /clear or at session start.

**Usage:**
```
/coder:init
```

**What it does:**
1. Checks global state (`~/.eri-rpg/state.json`) for active project
2. Reads `.planning/STATE.md` for current position
3. Detects incomplete work (paused, interrupted execution)
4. Shows project status with progress bar
5. Suggests next command

**When to use:**
- After `/clear` command
- At session start
- After context compaction
- When resuming work

**Why needed:** Claude loses context after /clear. This recovers project state and shows where you left off.

---

### /coder:meta-edit

**Purpose:** Safe self-modification of coder commands with snapshots and verification.

**Usage:**
```
/coder:meta-edit <command>
/coder:meta-edit execute-phase
/coder:meta-edit status init
/coder:meta-edit rollback plan-phase
```

**Phases:**
1. **Analyze** - Understand what command does, create snapshot
2. **Plan** - State intent, list risks, get approval
3. **Execute** - Make approved changes
4. **Verify** - Validate file structure, auto-rollback on failure

**When to use:**
- Modifying coder skill files
- Fixing broken commands
- Adding features to existing commands

**Why needed:** Prevents breaking commands with ad-hoc edits. Creates snapshots, requires approval, auto-rollbacks on verification failure.

---

### /coder:projects

**Purpose:** List all registered projects with status.

**Usage:**
```
/coder:projects
```

**Shows:**
- Project name and path
- Current phase and status
- Last activity
- Active project indicator

**When to use:**
- See all your projects
- Find project to switch to
- Check what's active

---

### /coder:help

**Purpose:** Show command reference and usage examples.

**Usage:**
```
/coder:help                     # All commands
/coder:help <command>           # Specific command help
/coder:help execute-phase       # Details on execute-phase
```

**When to use:**
- New to eri-coder
- Forgot command syntax
- Need examples

**Why needed:** Quick reference without leaving the terminal.

---

### /coder:history

**Purpose:** Show execution timeline, decisions, and metrics over time.

**Usage:**
```
/coder:history                  # Full history
/coder:history --phase 2        # Phase-specific
/coder:history --decisions      # Only decisions
/coder:history --failures       # Only failures
```

**When to use:**
- Understanding what happened in a session
- Reviewing decisions made
- Debugging recurring issues

**Why needed:** Timeline of all operations, decision points, successes and failures. Useful for post-mortems and learning.

---

### /coder:insert-phase

**Purpose:** Insert an urgent phase between existing phases.

**Usage:**
```
/coder:insert-phase <position> "<name>" "<goal>"
/coder:insert-phase 2 "Security-Hotfix" "Fix authentication vulnerability"
```

**When to use:**
- Critical issue discovered mid-project
- Urgent feature request
- Dependency needs to be addressed before continuing

**Why needed:** Sometimes you can't wait until the end. Inserts phase at specified position, renumbers subsequent phases.

---

### /coder:learn

**Purpose:** Extract reusable patterns from successful project implementations.

**Usage:**
```
/coder:learn <pattern-name>
/coder:learn auth-system
/coder:learn api-structure
```

**When to use:**
- After completing a feature you'll reuse
- Building your pattern library
- Before templating a project

**Why needed:** Captures what worked to `~/.eri-rpg/patterns/`. Apply to future projects. Includes code snippets, decisions made, and pitfalls avoided.

---

### /coder:list-phase-assumptions

**Purpose:** See what Claude assumes about implementing a phase.

**Usage:**
```
/coder:list-phase-assumptions <N>
/coder:list-phase-assumptions 2
```

**When to use:**
- Before planning to catch wrong assumptions
- When phase seems off-track
- To align on approach before execution

**Why needed:** Claude makes assumptions. This surfaces them so you can correct before code is written, not after.

---

### /coder:map-codebase

**Purpose:** Analyze existing codebase before making changes.

**Usage:**
```
/coder:map-codebase             # Full analysis
/coder:map-codebase --quick     # Fast summary only
```

**When to use:**
- Before adding features to existing project
- Understanding unfamiliar codebase
- Before major refactoring

**Why needed:** Creates `.planning/codebase/` with STACK.md, ARCHITECTURE.md, CONVENTIONS.md, CONCERNS.md. Claude uses this to match existing patterns.

---

### /coder:merge

**Purpose:** Combine multiple small plans into one larger plan.

**Usage:**
```
/coder:merge <plan-1> <plan-2>
/coder:merge 2-01 2-02 2-03    # Merge three plans
```

**When to use:**
- Plans are too granular
- Want to reduce checkpoint overhead
- Related work that should commit together

**Why needed:** Sometimes `/coder:split` goes too far, or initial planning created too many small plans. Merge combines them with context budget checks.

---

### /coder:metrics

**Purpose:** Track time, tokens, cost, and success rates across the project.

**Usage:**
```
/coder:metrics                  # Current project metrics
/coder:metrics --phase 2        # Phase-specific
/coder:metrics --compare        # Compare phases
/coder:metrics --export csv     # Export data
```

**When to use:**
- Review project efficiency
- Compare phase complexity
- Track spending over time

**Why needed:** Dashboard showing token usage, cost breakdown, time per phase, verification pass rates. Helps optimize workflow and budget.

---

### /coder:new-milestone

**Purpose:** Start a new version/milestone on an existing project.

**Usage:**
```
/coder:new-milestone <version>
/coder:new-milestone v2.0
/coder:new-milestone v1.1 --from-todos   # Use captured todos
```

**When to use:**
- After completing v1, starting v2
- Major new feature set
- Different release cycle

**Why needed:** Preserves v1 artifacts in archive, creates fresh ROADMAP.md for new milestone, optionally imports deferred todos.

---

### /coder:new-project

**Purpose:** Initialize new project with full 8-phase setup workflow.

**Usage:**
```
/coder:new-project <name> "<description>"
/coder:new-project my-app "A task management app with due dates"
```

**When to use:**
- Starting a brand new application
- Building something from scratch
- You have an idea and want Claude to build it

**Why needed:** The main entry point. Runs 8 phases: Setup, Brownfield Detection, Questioning, PROJECT.md, Preferences, Research, Requirements, Roadmap. Outputs complete `.planning/` directory.

---

### /coder:pause

**Purpose:** Create handoff state when stopping work mid-session.

**Usage:**
```
/coder:pause "<reason>"
/coder:pause "stopping for the day"
/coder:pause "need user input on design"
```

**When to use:**
- End of work session
- Waiting on external input
- Context getting long

**Why needed:** Saves current position, uncommitted context, and next steps to STATE.md. Use `/coder:resume` to continue.

---

### /coder:plan-milestone-gaps

**Purpose:** Create new phases to address verification failures.

**Usage:**
```
/coder:plan-milestone-gaps
```

**When to use:**
- After verification reveals gaps
- Features marked "incomplete" need follow-up
- Audit identified missing requirements

**Why needed:** Reads `.planning/phases/*/VERIFICATION.md`, finds unmet requirements, generates phases to close gaps.

---

### /coder:plan-phase

**Purpose:** Create executable plans with verification criteria for a phase.

**Usage:**
```
/coder:plan-phase <N>
/coder:plan-phase 1
/coder:plan-phase 2 --detailed    # More granular plans
```

**When to use:**
- After roadmap is approved
- Before executing a phase
- After `/coder:discuss-phase` (optional)

**Why needed:** Breaks phase goal into executable plans (01-01-PLAN.md, 01-02-PLAN.md, etc.). Each plan has specific tasks, verification criteria, and success conditions.

---

### /coder:progress

**Purpose:** Show current position, completion percentage, and next steps.

**Usage:**
```
/coder:progress
/coder:progress --detailed
```

**When to use:**
- Where am I in the project?
- What's the next command to run?
- How much is left?

**Why needed:** Quick status: current phase, current plan, completion %, recent activity, suggested next command.

---

### /coder:quick

**Purpose:** Execute ad-hoc task outside the normal phase workflow.

**Usage:**
```
/coder:quick "<task>"
/coder:quick "Fix the login button styling"
/coder:quick "Add loading spinner to dashboard"
```

**When to use:**
- Small fixes that don't fit phases
- Quick changes requested by user
- Bug fixes during development

**Why needed:** Not everything fits the phase structure. Quick tasks get snapshot protection, verification, and proper commits without full planning overhead.

---

### /coder:remove-phase

**Purpose:** Remove a future phase from the roadmap.

**Usage:**
```
/coder:remove-phase <N>
/coder:remove-phase 5
```

**When to use:**
- Scope reduction
- Feature no longer needed
- Combining phases

**Why needed:** Requirements change. Remove phases that are no longer needed. Only works on unstarted phases.

---

### /coder:replay

**Purpose:** Re-run a phase with different parameters or lessons learned.

**Usage:**
```
/coder:replay <N>
/coder:replay 2                        # Replay entire phase
/coder:replay 2 --plan 3               # Replay from plan 3
/coder:replay 2 --fix-issues-only      # Only fix failed verifications
```

**When to use:**
- Phase failed verification
- Want to try different approach
- Applying lessons from first attempt

**Why needed:** Sometimes execution doesn't work the first time. Replay lets you try again with accumulated context and fixed issues.

---

### /coder:resume

**Purpose:** Restore session from last pause point.

**Usage:**
```
/coder:resume
```

**When to use:**
- Starting new session after pause
- Context compaction happened
- Continuing work from yesterday

**Why needed:** Reads STATE.md, loads context, shows where you left off, suggests next command.

---

### /coder:rollback

**Purpose:** Undo phase or plan execution using git history.

**Usage:**
```
/coder:rollback                     # Undo last plan
/coder:rollback --plan 2-03         # Undo specific plan
/coder:rollback --phase 2           # Undo entire phase
/coder:rollback --dry-run           # Preview only
```

**When to use:**
- Execution went wrong
- Want to try different approach
- Need to undo recent changes

**Why needed:** Safe undo using git revert. Creates backup branch, reverts commits, updates STATE.md. Preserves history.

---

### /coder:settings

**Purpose:** View and modify workflow preferences.

**Usage:**
```
/coder:settings                     # View current
/coder:settings mode yolo           # Set mode
/coder:settings depth comprehensive # Set depth
```

**When to use:**
- Change YOLO/interactive mode mid-project
- Adjust research depth
- Modify model preferences

**Why needed:** Preferences evolve. Change settings without restarting project.

---

### /coder:split

**Purpose:** Break a large plan into smaller, more manageable plans.

**Usage:**
```
/coder:split <plan-id>
/coder:split 2-03
/coder:split 2-03 --into 3     # Split into 3 plans
```

**When to use:**
- Plan is too complex
- Want more granular checkpoints
- Single plan keeps failing

**Why needed:** Large plans are risky. Split into smaller atomic units for better verification and rollback granularity.

---

### /coder:status

**Purpose:** Quick status check - current phase, progress, next action.

**Usage:**
```
/coder:status
```

**Shows:**
- Current project and status
- Phase progress (N/total)
- Visual progress bar
- Last action
- Recommended next command

**When to use:**
- Quick "where am I?" check
- After returning to a project
- Before deciding what to do next

**Why needed:** Faster than `/coder:progress --detailed`. Shows just enough to orient and suggest next action.

---

### /coder:template

**Purpose:** Save project structure as reusable template.

**Usage:**
```
/coder:template <name>
/coder:template saas-starter
/coder:template --from-patterns auth-api-ui    # Combine patterns
```

**When to use:**
- Built something you'll reuse
- Creating starter kit
- Standardizing project structure

**Why needed:** Captures entire project structure, planning artifacts, and conventions to `~/.eri-rpg/templates/`. Use as starting point for future projects.

---

### /coder:verify-work

**Purpose:** Manual user acceptance testing for completed phase.

**Usage:**
```
/coder:verify-work <N>
/coder:verify-work 2
```

**When to use:**
- After `/coder:execute-phase` completes
- Before moving to next phase
- Final quality check

**Why needed:** Three-level verification: Exists (files created), Substantive (not stubs), Wired (integrated and working). Spawns parallel verification agents. Reports pass/fail with details.

---

### /coder:verify-behavior

**Purpose:** Verify implementation matches behavior spec (behavior diff).

**Usage:**
```
/coder:verify-behavior <program>/<feature>
/coder:verify-behavior eritrainer/sana
```

**What it checks:**
- Input/output types match spec
- State machine preserved
- No forbidden side effects
- Ownership model compatible
- Test contracts have tests
- Resource constraints documented

**Status values:**
- ✅ Pass - code matches spec
- ❌ Fail - must fix before done
- ⚠️ Manual - needs human verification
- ⏳ Pending - not yet analyzed

**When to use:**
- After implementing a feature from behavior spec
- After refactoring ported feature
- Before marking feature complete

**Why needed:** Ensures implementation actually matches the behavior spec. Blocks completion on violations. See [docs/BLUEPRINT-BEHAVIOR.md](BLUEPRINT-BEHAVIOR.md).

---

### /coder:clone-behavior

**Purpose:** Clone an entire program by extracting behaviors and reimplementing from scratch.

**Usage:**
```
/coder:clone-behavior <source-path> <new-project-name> [options]

# Examples
/coder:clone-behavior ~/onetrainer eritrainer --language rust
/coder:clone-behavior ~/comfyui eri-comfy --language rust --framework candle
/coder:clone-behavior ~/myapp myapp-v2 --dry-run
```

**Options:**
- `--language <lang>` - Target language (default: same as source)
- `--framework <framework>` - Target framework
- `--skip-tests` - Don't extract test contracts
- `--dry-run` - Show plan without executing
- `--modules <list>` - Only clone specific modules (comma-separated)
- `--exclude <list>` - Skip specific modules (comma-separated)

**The 5-Phase Pipeline:**

| Phase | What Happens |
|-------|--------------|
| **1. SCAN** | Extract BEHAVIOR.md for every module in source |
| **2. PLAN** | Create roadmap from behaviors (not source code) |
| **3. IMPLEMENT** | Build each module using behavior as requirements |
| **4. VERIFY** | Behavior diff - does target match source behavior? |
| **5. COMPLETE** | All behaviors verified, tag release |

**What it chains:**
- `/coder:map-codebase` - Understand source architecture
- `/coder:blueprint add --extract-tests` - Extract all behaviors
- `/coder:new-project --from-behaviors` - Create behavior-based roadmap
- `/coder:execute-phase` - Implement each module
- `/coder:verify-behavior` - Verify parity for each module

**When to use:**
- Porting a project to another language (Python → Rust)
- Complete rewrite with guaranteed feature parity
- Modernizing legacy code without losing functionality
- Creating a clean-room implementation

**Why it's different:**
```
Traditional: Source Code ──copy/translate──► Target Code
                         (carries implementation baggage)

Clone-behavior: Source Code ──extract──► BEHAVIOR.md ──implement──► Target Code
                                        (portable spec)    (native implementation)
```

Target code is written fresh, following target idioms. Only the BEHAVIOR is preserved.

**See also:** [docs/BLUEPRINT-BEHAVIOR.md](BLUEPRINT-BEHAVIOR.md) for behavior spec format.

---

## Quick Reference Table

| Command | Purpose |
|---------|---------|
| `add-feature` | Add feature to existing codebase (or port with --reference) |
| `add-phase` | Append phase to roadmap |
| `add-todo` | Capture idea for later |
| `blueprint` | Manage program blueprints and behavior specs |
| `clone-behavior` | Clone entire program with behavior parity |
| `compare` | Evaluate approaches before choosing |
| `complete-milestone` | Archive and tag release |
| `cost` | Estimate tokens and API cost |
| `debug` | Systematic bug investigation |
| `diff` | Show changes since checkpoint |
| `discuss-phase` | Capture decisions before planning |
| `execute-phase` | Build code for a phase |
| `handoff` | Generate context for handoff |
| `help` | Command reference |
| `history` | Execution timeline |
| `init` | Session context recovery |
| `insert-phase` | Insert urgent phase |
| `learn` | Extract reusable patterns |
| `list-phase-assumptions` | See Claude's assumptions |
| `map-codebase` | Analyze existing code |
| `merge` | Combine multiple plans |
| `meta-edit` | Safe self-modification of commands |
| `metrics` | Track project metrics |
| `new-milestone` | Start new version |
| `new-project` | Initialize new project (main entry) |
| `pause` | Save state and stop |
| `plan-milestone-gaps` | Create phases for failures |
| `plan-phase` | Create executable plans |
| `progress` | Show current position |
| `projects` | List all registered projects |
| `quick` | Ad-hoc task outside phases |
| `remove-phase` | Remove future phase |
| `replay` | Re-run with changes |
| `resume` | Restore from pause |
| `rollback` | Undo execution |
| `settings` | View/change preferences |
| `split` | Break plan into smaller ones |
| `status` | Quick status check |
| `template` | Save as reusable template |
| `verify-behavior` | Verify code matches behavior spec |
| `verify-work` | Test completed phase |

---

## Typical Session Flow

```
# Day 1: Start project
/coder:new-project my-app "A task management app"
# Answer questions, approve roadmap

# Day 1-2: Build phase 1
/coder:plan-phase 1
/coder:execute-phase 1
/coder:verify-work 1

# Continue phases...
/coder:plan-phase 2
/coder:execute-phase 2
/coder:verify-work 2

# End of session
/coder:pause "done for today"

# Next day
/coder:resume
/coder:progress
# Continue...

# When done
/coder:complete-milestone v1.0
```
