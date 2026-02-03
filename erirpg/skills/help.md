# /coder:help - Command Reference

Display help for eri-coder commands and workflows.

## CLI Integration

**Call the CLI for structured command reference:**
```bash
erirpg coder-help [topic]
```

This returns JSON with:
- `commands`: Categorized command list (core, phase, navigation, utility)
- `topic`: Requested topic
- `matching`: Commands matching topic (if specified)

Use this data to render help content.

---

## Usage

```
/coder:help                    # Overview of all commands
/coder:help {command}          # Detailed help for specific command
/coder:help workflow           # Explain the workflow
/coder:help concepts           # Key concepts explained
```

## Command Categories

### Core Workflow Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/coder:new-project` | Initialize new project | Starting from scratch |
| `/coder:discuss-phase N` | Capture implementation decisions | Before planning a phase |
| `/coder:plan-phase N` | Create executable plans | After discussion or directly |
| `/coder:execute-phase N` | Execute all phase plans | After planning complete |
| `/coder:verify-work N` | Manual acceptance testing | After execution complete |
| `/coder:complete-milestone` | Archive and tag release | All phases verified |
| `/coder:new-milestone` | Start next version | After milestone complete |

### Phase Management Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/coder:add-phase "name" "goal"` | Append phase to roadmap | Need additional work |
| `/coder:insert-phase N "name"` | Insert before phase N | Urgent work needed |
| `/coder:remove-phase N` | Remove future phase | Scope reduction |
| `/coder:list-phase-assumptions N` | See Claude's approach | Before planning |
| `/coder:plan-milestone-gaps` | Create phases for gaps | After verification failures |

### Navigation Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/coder:progress` | Current status and metrics | Anytime |
| `/coder:help` | This help | Anytime |
| `/coder:settings` | Configure preferences | Setup or changes needed |

### Utility Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/coder:quick "task"` | Ad-hoc task with guarantees | Small fixes outside phases |
| `/coder:debug "issue"` | Systematic debugging | Investigating problems |
| `/coder:add-todo "idea"` | Capture for later | Ideas during work |
| `/coder:pause "reason"` | Create handoff state | Stopping work |
| `/coder:resume` | Restore from pause | Continuing work |
| `/coder:map-codebase` | Analyze existing code | Brownfield projects |
| `/coder:add-feature "name"` | Add feature to existing | Brownfield fast-path |

## Typical Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                     NEW PROJECT                              │
├─────────────────────────────────────────────────────────────┤
│  /coder:new-project my-app "Description"                    │
│      │                                                       │
│      ├─► Questions about requirements                        │
│      ├─► Research (optional, 4 parallel agents)             │
│      ├─► Define requirements with REQ-IDs                   │
│      └─► Create phased roadmap                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FOR EACH PHASE                             │
├─────────────────────────────────────────────────────────────┤
│  /coder:discuss-phase N     (optional, capture decisions)   │
│      │                                                       │
│      ▼                                                       │
│  /coder:plan-phase N        (create executable plans)       │
│      │                                                       │
│      ▼                                                       │
│  /coder:execute-phase N     (build in parallel waves)       │
│      │                                                       │
│      ▼                                                       │
│  /coder:verify-work N       (manual testing)                │
│      │                                                       │
│      └─► Pass: Next phase │ Fail: Fix and retry            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  COMPLETE MILESTONE                          │
├─────────────────────────────────────────────────────────────┤
│  /coder:complete-milestone                                   │
│      │                                                       │
│      ├─► Archive all artifacts                              │
│      ├─► Create git tag                                     │
│      └─► Ready for /coder:new-milestone                     │
└─────────────────────────────────────────────────────────────┘
```

## Brownfield Workflow

For existing codebases:

```
/coder:map-codebase              # Analyze existing code
    │
    ▼
/coder:add-feature "auth"        # Fast-path for single feature
    OR
/coder:new-project --brownfield  # Full workflow with context
```

## Key Concepts

### Phases
- **What:** A deliverable unit of work with clear success criteria
- **Contains:** 2-5 plans, each with 2-3 tasks
- **Goal:** User-visible outcome, not technical tasks
- **Example:** "User Authentication" not "Create auth files"

### Plans
- **What:** Executable work unit for a subagent
- **Contains:** 2-3 tasks that fit in ~50% context
- **Waves:** Plans grouped by dependencies for parallel execution
- **Output:** PLAN.md (input) → SUMMARY.md (result)

### Verification
- **Three levels:** Exists → Substantive → Wired
- **Must-haves:** Observable truths, not task completion
- **Gaps:** Failed verifications become new plans

### Checkpoints
- **Types:** human-verify, decision, human-action
- **Flow:** Agent pauses → User responds → Fresh agent continues
- **State:** Preserved in structured format for handoff

### Wave Execution
- **What:** Parallel execution of independent plans
- **How:** Wave 1 runs, then Wave 2, etc.
- **Benefit:** Faster execution without context bleed

## Getting Help

### For a specific command:
```
/coder:help new-project
```

### For workflow overview:
```
/coder:help workflow
```

### For troubleshooting:
```
/coder:debug "describe issue"
```

### For current status:
```
/coder:progress
```

## Quick Reference Card

```
NEW PROJECT          /coder:new-project name "description"
ADD FEATURE          /coder:add-feature name "description"
MAP CODEBASE         /coder:map-codebase

PLAN PHASE           /coder:plan-phase N
EXECUTE PHASE        /coder:execute-phase N
VERIFY PHASE         /coder:verify-work N

QUICK FIX            /coder:quick "description"
DEBUG ISSUE          /coder:debug "symptoms"

PAUSE WORK           /coder:pause "reason"
RESUME WORK          /coder:resume

CHECK PROGRESS       /coder:progress
CHANGE SETTINGS      /coder:settings
```
