# EriRPG Command Reference

## What is EriRPG?

**EriRPG is for maintaining and working with existing codebases.**

It tracks what Claude learns, enforces code quality, and provides structured workflows for bug fixes and feature additions to projects that already exist.

### When to Use EriRPG

- Working on an existing project with code already written
- Bug fixes and small changes
- Maintenance work
- Learning and exploring a codebase
- When you need Claude to remember what it learned
- Enforced quality gates and verification

### The Philosophy

1. **Track knowledge**: Claude remembers what it learns about your code
2. **Enforce quality**: No edits without proper workflow
3. **Verify everything**: Tests must pass, changes must be validated
4. **Learn continuously**: Patterns and gotchas captured for reuse

### Key Difference from Eri-Coder

| EriRPG | Eri-Coder |
|--------|-----------|
| Existing codebases | New projects from scratch |
| Maintenance & fixes | Vibe coding & building |
| Single-file to small changes | Multi-phase app development |
| Knowledge tracking | Research & planning |
| Strict enforcement | Flexible workflow |

---

## Commands (Alphabetical)

### /eri:cleanup

**Purpose:** Remove stale runs and state from `.eri-rpg/` directory.

**Usage:**
```
/eri:cleanup <project>              # List stale runs
/eri:cleanup <project> --prune      # Delete stale runs
```

**When to use:**
- EriRPG seems stuck or confused
- Old runs blocking new work
- Want to start fresh without losing knowledge

**Why needed:** Runs accumulate over time. Clean up incomplete or abandoned runs to keep state manageable.

---

### /eri:commit

**Purpose:** Commit changes with EriRPG context and proper attribution.

**Usage:**
```
/eri:commit "<message>"
/eri:commit "fix: resolve login timeout issue"
```

**When to use:**
- After completing an eri:execute run
- To commit tracked changes
- When verification passed

**Why needed:** Creates commit with proper format, links to run ID, adds verification status. Better than manual git commit.

---

### /eri:debug

**Purpose:** Triage-first debugging with systematic investigation.

**Usage:**
```
/eri:debug "<symptom>"
/eri:debug "API returns 500 on user creation"
```

**When to use:**
- Bug that needs investigation
- Issue spans multiple files
- Need systematic approach

**Why needed:** Structured debugging: reproduce, hypothesize, test, observe. Documents findings. Tracks what was tried.

---

### /eri:decide

**Purpose:** Log a decision with full rationale for future reference.

**Usage:**
```
/eri:decide "<decision>" "<rationale>"
/eri:decide "Use SQLite" "Simpler than PostgreSQL for single-user app"
```

**When to use:**
- Making architectural choices
- Choosing between approaches
- Any decision future-you needs to understand

**Why needed:** Decisions get forgotten. This creates permanent record in `.eri-rpg/decisions.json` with timestamp, context, and rationale.

---

### /eri:defer

**Purpose:** Capture an idea for later without interrupting current work.

**Usage:**
```
/eri:defer "<idea>"
/eri:defer "Add caching layer for API responses"
```

**When to use:**
- Good idea that's out of scope
- Feature for later version
- Don't want to forget

**Why needed:** Captures to backlog without derailing current task. Review deferred items later.

---

### /eri:discuss

**Purpose:** Start or continue a goal clarification discussion.

**Usage:**
```
/eri:discuss "<topic>"
/eri:discuss "How should we handle authentication?"
```

**When to use:**
- Before implementing unclear feature
- Need to align on approach
- Exploring options

**Why needed:** Structured discussion that captures decisions and outcomes. Better than informal chat.

---

### /eri:done

**Purpose:** Mark current work as complete and close the run.

**Usage:**
```
/eri:done
/eri:done --skip-verify    # Skip verification (not recommended)
```

**When to use:**
- After all steps complete
- Verification passed
- Ready to move on

**Why needed:** Properly closes run, triggers auto-learning, updates state. Don't just walk away.

---

### /eri:env

**Purpose:** Show project environment (test, lint, build commands).

**Usage:**
```
/eri:env <project>
```

**When to use:**
- New to a project
- Need to know how to run tests
- Checking build configuration

**Why needed:** Shows detected commands: test runner, linter, build tool. Reads from package.json, pyproject.toml, Cargo.toml, etc.

---

### /eri:execute

**Purpose:** Execute or resume an EriRPG run with verification and auto-learning.

**Usage:**
```
/eri:execute "<goal>"
/eri:execute "Add password reset functionality"
/eri:execute "Fix the login timeout bug"
```

**When to use:**
- Any code change to existing project
- Multi-file modifications
- When you want tracking and verification

**Why needed:** The main entry point for code changes. Creates run, plans steps, executes with verification, auto-learns on completion.

---

### /eri:find

**Purpose:** Find modules matching a query across the codebase.

**Usage:**
```
/eri:find <project> "<query>"
/eri:find myapp "authentication"
/eri:find myapp "database connection"
```

**When to use:**
- Looking for specific functionality
- Don't know which file to edit
- Exploring codebase

**Why needed:** Searches indexed knowledge and codebase. Returns relevant files with context about what each does.

---

### /eri:fix

**Purpose:** Report and track a bug found during workflow.

**Usage:**
```
/eri:fix "<bug description>"
/eri:fix "Login button doesn't respond on mobile"
```

**When to use:**
- Found bug while working on something else
- Need to track issue for later
- Quick bug report

**Why needed:** Creates tracked bug report without interrupting current work. Links to context where bug was found.

---

### /eri:gaps

**Purpose:** Show gaps from verification failures that need addressing.

**Usage:**
```
/eri:gaps <project>
```

**When to use:**
- After verification failed
- Planning what to fix next
- Review outstanding issues

**Why needed:** Lists all unresolved verification failures with details about what's missing.

---

### /eri:guard

**Purpose:** Intercept all file edits with hard enforcement.

**Usage:**
```
/eri:guard
```

**When to use:**
- Automatically active after /eri:start
- Ensures no edits bypass EriRPG

**Why needed:** Prevents direct file edits outside EriRPG tracking. Claude cannot use Edit/Write tools without active run.

---

### /eri:help

**Purpose:** Get help on any EriRPG topic.

**Usage:**
```
/eri:help                       # General help
/eri:help <topic>               # Specific topic
/eri:help execute               # Help with execute command
/eri:help tiers                 # Explain tier system
```

**When to use:**
- Learning EriRPG
- Stuck on something
- Need clarification

**Why needed:** Quick reference and explanations without leaving terminal.

---

### /eri:impact

**Purpose:** Analyze impact of changing a module before editing.

**Usage:**
```
/eri:impact <project> <file>
/eri:impact myapp src/auth/login.ts
```

**When to use:**
- Before modifying important file
- Checking what depends on this code
- Risk assessment

**Why needed:** Shows what other files depend on this one, test coverage, and potential blast radius of changes.

---

### /eri:index

**Purpose:** Index or reindex project codebase for knowledge graph.

**Usage:**
```
/eri:index <project>
/eri:index myapp                # Initial index
/eri:index myapp --rebuild      # Full reindex
```

**When to use:**
- First time setting up EriRPG on project
- After major changes
- Knowledge seems stale

**Why needed:** Builds knowledge graph of codebase. Required for /eri:recall, /eri:find to work.

---

### /eri:init

**Purpose:** Initialize a new EriRPG project configuration.

**Usage:**
```
/eri:init <project>
/eri:init myapp
```

**When to use:**
- First time using EriRPG on a project
- Setting up tracking
- Before /eri:index

**Why needed:** Creates `.eri-rpg/` directory structure, detects project type, sets up configuration.

---

### /eri:knowledge

**Purpose:** Show all stored knowledge for a project.

**Usage:**
```
/eri:knowledge <project>
/eri:knowledge myapp
```

**When to use:**
- See what Claude remembers
- Review learned patterns
- Check knowledge coverage

**Why needed:** Lists all indexed files, learned patterns, gotchas, and stored knowledge.

---

### /eri:learn

**Purpose:** Store knowledge about a module after reading it.

**Usage:**
```
/eri:learn <project> <file>
/eri:learn myapp src/auth/login.ts
```

**When to use:**
- After understanding a file
- Want to remember what this does
- Building knowledge base

**Why needed:** Stores structured knowledge: purpose, dependencies, patterns, gotchas. Retrieved with /eri:recall.

---

### /eri:mode

**Purpose:** Show or change project mode and tier.

**Usage:**
```
/eri:mode <project>                    # Show current
/eri:mode <project> --tier 2           # Change tier
/eri:mode <project> --strict           # Enable strict mode
```

**When to use:**
- Check current enforcement level
- Adjust strictness
- Change project tier

**Why needed:** Controls how strict EriRPG enforcement is. Higher tiers = more verification required.

---

### /eri:pattern

**Purpose:** Store a reusable pattern or gotcha learned during work.

**Usage:**
```
/eri:pattern <project> "<pattern>" "<description>"
/eri:pattern myapp "api-error-handling" "Always wrap in try-catch with specific error types"
```

**When to use:**
- Discovered pattern that should be reused
- Found gotcha others should know
- Codifying best practices

**Why needed:** Patterns stored for future reference. Shown when working on related code.

---

### /eri:persona

**Purpose:** Set active persona for specialized behavior.

**Usage:**
```
/eri:persona <persona>
/eri:persona security
/eri:persona performance
```

**When to use:**
- Need specialized focus
- Security review
- Performance optimization

**Why needed:** Activates persona (security, performance, architect, etc.) that changes Claude's priorities and checks.

---

### /eri:phase

**Purpose:** Show current workflow phase.

**Usage:**
```
/eri:phase <project>
```

**When to use:**
- Check where you are in workflow
- After resuming session

**Why needed:** Shows current phase: planning, executing, verifying, complete.

---

### /eri:plan

**Purpose:** Manage execution plans for runs.

**Usage:**
```
/eri:plan <project>                    # Show current plan
/eri:plan <project> --create "<goal>"  # Create new plan
```

**When to use:**
- Review planned steps
- Create plan before execute
- Modify existing plan

**Why needed:** See and manage the step-by-step plan for current or upcoming work.

---

### /eri:progress

**Purpose:** Show progress on current work.

**Usage:**
```
/eri:progress <project>
```

**When to use:**
- Check how far along you are
- See remaining steps
- Status update

**Why needed:** Shows: X of Y steps complete, current step, time elapsed, estimated remaining.

---

### /eri:push

**Purpose:** Push changes after verification passes.

**Usage:**
```
/eri:push <project>
```

**When to use:**
- After commit
- Verification passed
- Ready to share changes

**Why needed:** Pushes to remote with verification status. Blocks push if verification failed.

---

### /eri:quick

**Purpose:** Start a quick fix on a single file with snapshot protection.

**Usage:**
```
/eri:quick <project> <file> "<description>"
/eri:quick myapp src/utils.ts "Fix date formatting bug"
```

**When to use:**
- Single file edit
- Simple fix
- Don't need full run overhead

**Why needed:** Lightweight alternative to full /eri:execute. Creates snapshot for rollback, but less tracking.

---

### /eri:recall

**Purpose:** Retrieve stored knowledge about a module.

**Usage:**
```
/eri:recall <project> <file>
/eri:recall myapp src/auth/login.ts
/eri:recall myapp auth    # Fuzzy match
```

**When to use:**
- Before editing a file
- Need context about module
- Refresh memory after break

**Why needed:** Returns stored knowledge: what file does, dependencies, patterns, gotchas. Saves re-reading entire file.

---

### /eri:research

**Purpose:** Run research phase before planning implementation.

**Usage:**
```
/eri:research <project> "<topic>"
/eri:research myapp "best practices for rate limiting"
```

**When to use:**
- Before implementing new feature
- Need to research approaches
- Gathering information

**Why needed:** Spawns research agents to gather information before planning. Outputs research summary.

---

### /eri:reset

**Purpose:** Reset EriRPG state to idle.

**Usage:**
```
/eri:reset <project>
/eri:reset myapp --hard    # Also clear runs
```

**When to use:**
- State is corrupted
- Want fresh start
- Stuck and can't proceed

**Why needed:** Clears current run state. --hard also clears run history.

---

### /eri:resume

**Purpose:** Resume work from previous session.

**Usage:**
```
/eri:resume <project>
```

**When to use:**
- Starting new session
- After context compaction
- Continuing yesterday's work

**Why needed:** Loads previous state, shows where you left off, continues from that point.

---

### /eri:rethink

**Purpose:** Reconsider current approach and explore alternatives.

**Usage:**
```
/eri:rethink <project>
```

**When to use:**
- Current approach isn't working
- Want to try different strategy
- Stuck on implementation

**Why needed:** Steps back, reviews what was tried, suggests alternative approaches.

---

### /eri:roadmap

**Purpose:** View and manage project roadmap.

**Usage:**
```
/eri:roadmap <project>                     # View roadmap
/eri:roadmap <project> "<phase>" --add     # Add phase
```

**When to use:**
- Planning larger changes
- Multi-phase work
- Project overview

**Why needed:** High-level view of planned work phases. Less detailed than eri-coder but useful for maintenance projects.

---

### /eri:session

**Purpose:** Show or update current session state.

**Usage:**
```
/eri:session <project>
/eri:session <project> --save              # Save state
```

**When to use:**
- Check session status
- Before ending work
- Debug session issues

**Why needed:** Shows active run, current step, session duration, state health.

---

### /eri:settings

**Purpose:** View or modify EriRPG settings.

**Usage:**
```
/eri:settings                              # View all
/eri:settings --edit                       # Edit settings
```

**When to use:**
- Check configuration
- Change preferences
- Adjust verification settings

**Why needed:** Global and project settings: enforcement level, auto-learn, verification commands.

---

### /eri:show

**Purpose:** Show project structure and metadata.

**Usage:**
```
/eri:show <project>
```

**When to use:**
- Overview of project
- Check project type detected
- See configuration

**Why needed:** Shows: project type, language, framework, key files, configuration.

---

### /eri:spec

**Purpose:** Manage feature specifications.

**Usage:**
```
/eri:spec list <project>                   # List specs
/eri:spec new <project> "<name>"           # Create spec
/eri:spec show <project> <spec-id>         # Show spec
```

**When to use:**
- Defining new feature
- Reviewing requirements
- Before implementation

**Why needed:** Structured specifications that link to implementation. Track what's built vs. what's specified.

---

### /eri:start

**Purpose:** Start every coding session - enforces EriRPG for all changes.

**Usage:**
```
/eri:start
```

**When to use:**
- Beginning of every session
- After context reset
- To enable enforcement

**Why needed:** Activates EriRPG enforcement. Claude cannot make direct edits without going through /eri:execute.

---

### /eri:status

**Purpose:** Show current run status and provide resume command.

**Usage:**
```
/eri:status <project>
```

**When to use:**
- Quick check of where things are
- See if run is active
- Get resume command

**Why needed:** Concise status: run ID, step X/Y, last activity, suggested next action.

---

### /eri:switch

**Purpose:** Switch to another project mid-session.

**Usage:**
```
/eri:switch <project>
```

**When to use:**
- Working on multiple projects
- Need to context switch
- Changing focus

**Why needed:** Saves current project state, loads new project context, maintains separation.

---

### /eri:test

**Purpose:** Run project tests.

**Usage:**
```
/eri:test <project>
/eri:test <project> --file <path>          # Specific file
/eri:test <project> --watch                # Watch mode
```

**When to use:**
- Verify changes work
- Before committing
- During development

**Why needed:** Runs detected test command, shows results, tracks test history.

---

### /eri:todo

**Purpose:** Personal todo list - add, view, complete tasks.

**Usage:**
```
/eri:todo                                  # List todos
/eri:todo add "<item>"                     # Add item
/eri:todo done <id>                        # Complete item
```

**When to use:**
- Track small tasks
- Remember things to do
- Personal checklist

**Why needed:** Simple todo list persisted across sessions. Not tied to specific project.

---

### /eri:update

**Purpose:** Update session status files.

**Usage:**
```
/eri:update <project>
```

**When to use:**
- Status files seem stale
- After manual changes
- Sync state

**Why needed:** Refreshes status files from actual state. Fixes drift between files and reality.

---

### /eri:verify

**Purpose:** Verify plan covers all spec requirements.

**Usage:**
```
/eri:verify <project>
```

**When to use:**
- After creating plan
- Before execution
- Check coverage

**Why needed:** Ensures planned steps cover all requirements from spec. Catches gaps before coding.

---

## Quick Reference Table

| Command | Purpose |
|---------|---------|
| `cleanup` | Remove stale runs |
| `commit` | Commit with context |
| `debug` | Systematic debugging |
| `decide` | Log decision with rationale |
| `defer` | Capture idea for later |
| `discuss` | Goal clarification |
| `done` | Mark work complete |
| `env` | Show project environment |
| `execute` | Main entry - run with verification |
| `find` | Find modules by query |
| `fix` | Report bug during workflow |
| `gaps` | Show verification failures |
| `guard` | Enforce edit protection |
| `help` | Get help |
| `impact` | Analyze change impact |
| `index` | Index codebase |
| `init` | Initialize project |
| `knowledge` | Show all stored knowledge |
| `learn` | Store knowledge about module |
| `mode` | Show/change tier |
| `pattern` | Store reusable pattern |
| `persona` | Set active persona |
| `phase` | Show current phase |
| `plan` | Manage execution plans |
| `progress` | Show progress |
| `push` | Push after verification |
| `quick` | Quick single-file fix |
| `recall` | Retrieve stored knowledge |
| `research` | Research before planning |
| `reset` | Reset state |
| `resume` | Resume from previous session |
| `rethink` | Reconsider approach |
| `roadmap` | View/manage roadmap |
| `session` | Show session state |
| `settings` | View/modify settings |
| `show` | Show project structure |
| `spec` | Manage specifications |
| `start` | Enable enforcement (session start) |
| `status` | Show run status |
| `switch` | Switch projects |
| `test` | Run tests |
| `todo` | Personal todo list |
| `update` | Update status files |
| `verify` | Verify plan coverage |

---

## Typical Session Flow

```
# Start session
/eri:start

# Check what you remember about a file
/eri:recall myapp src/auth/login.ts

# Make changes with full tracking
/eri:execute "Add rate limiting to login endpoint"
# ... Claude executes steps, verifies ...

# Or for quick fix
/eri:quick myapp src/utils.ts "Fix date format"

# Commit and push
/eri:commit "feat: add rate limiting to login"
/eri:push myapp

# Mark done
/eri:done
```

---

## EriRPG vs Eri-Coder Decision Guide

**Use EriRPG (/eri:\*) when:**
- Project already has code
- Making bug fixes
- Small to medium changes
- Need strict enforcement
- Building knowledge over time

**Use Eri-Coder (/coder:\*) when:**
- Starting from scratch
- Building new application
- Multi-phase development
- Vibe coding with natural language
- Major new features
