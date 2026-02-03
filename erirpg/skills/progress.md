# /coder:progress - Show Current Position

Display current project status, progress metrics, and recommended next action.

## CLI Integration

**First, call the CLI to get progress metrics:**
```bash
erirpg coder-progress [--detailed] [--phase N]
```

This returns JSON with:
- `total_phases`, `completed_phases`, `phase_percent`
- `total_plans`, `completed_plans`, `plan_percent`
- `total_reqs`, `completed_reqs`, `req_percent`
- `current_phase`, `current_phase_plans`, `current_phase_completed`
- `status`: Current project status

Use these metrics to render the progress display below.

---

## Usage

```
/coder:progress              # Summary view
/coder:progress --detailed   # Full breakdown
/coder:progress --phase N    # Focus on specific phase
```

## Execution Steps

### Step 1: Load Project State

Read required files:
- `.planning/STATE.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`

### Step 2: Calculate Metrics

**Phase Progress:**
```python
total_phases = count(ROADMAP.md phases)
completed_phases = count(phases with status: complete)
current_phase = first(phases with status: in-progress or ready)
phase_percent = (completed_phases / total_phases) * 100
```

**Plan Progress (current phase):**
```python
phase_dir = .planning/phases/{current_phase}/
total_plans = count(*-PLAN.md files)
completed_plans = count(*-SUMMARY.md files)
plan_percent = (completed_plans / total_plans) * 100
```

**Requirement Coverage:**
```python
total_reqs = count(v1 requirements in REQUIREMENTS.md)
completed_reqs = count(requirements marked [x] Complete)
req_percent = (completed_reqs / total_reqs) * 100
```

### Step 3: Generate Progress Display

**Summary View (default):**
```markdown
# Project Progress

**Project:** [name from PROJECT.md]
**Status:** [idle | planning | executing | verifying | paused | blocked]

## Current Position

**Phase:** [N] of [total] — [phase name]
**Plan:** [M] of [phase_total]
**Overall:** [███████░░░] 70%

## Quick Stats

| Metric | Progress | Count |
|--------|----------|-------|
| Phases | [████████░░] 80% | 4/5 |
| Plans | [██████░░░░] 60% | 3/5 |
| Requirements | [███████░░░] 70% | 14/20 |

## What's Next

**Immediate:** [Next action with command]
**Blockers:** [None or list]

---
Last updated: [timestamp from STATE.md]
```

**Detailed View (--detailed):**
```markdown
# Project Progress: [name]

## Phase Breakdown

| # | Phase | Plans | Status | Duration |
|---|-------|-------|--------|----------|
| 1 | Setup | 2/2 | ✅ Complete | 45 min |
| 2 | Auth | 3/3 | ✅ Complete | 1h 20min |
| 3 | Core Features | 2/4 | 🔄 In Progress | 55 min |
| 4 | Polish | 0/3 | ⏳ Pending | - |
| 5 | Deploy | 0/2 | ⏳ Pending | - |

## Current Phase: [3] Core Features

**Goal:** [phase goal from ROADMAP.md]

### Plans Status
| Plan | Name | Status | Commit |
|------|------|--------|--------|
| 3-01 | Database Models | ✅ Complete | abc123 |
| 3-02 | API Endpoints | ✅ Complete | def456 |
| 3-03 | Frontend Components | 🔄 Executing | - |
| 3-04 | Integration | ⏳ Pending | - |

### Requirements Covered
- [x] REQ-007: User can create items
- [x] REQ-008: User can edit items
- [ ] REQ-009: User can delete items
- [ ] REQ-010: Items persist across sessions

## Velocity Metrics

**Average plan duration:** [X] minutes
**Estimated remaining:** [Y] minutes
**Session time:** [Z] minutes

## Accumulated Context

### Recent Decisions
[From STATE.md Decisions section]

### Pending Todos
[From STATE.md Pending Todos section]

### Blockers/Concerns
[From STATE.md Blockers section]

## Session History

| Date | Phases | Plans | Notes |
|------|--------|-------|-------|
| 2026-01-30 | 1-2 | 5 | Initial setup |
| 2026-01-29 | 3 | 2 | Core features started |

---

**Commands:**
- Continue: `/coder:execute-phase 3`
- Verify: `/coder:verify-work 3`
- Pause: `/coder:pause "reason"`
```

**Phase Focus (--phase N):**
```markdown
# Phase [N]: [Name]

**Goal:** [phase goal]
**Status:** [status]
**Started:** [date]
**Duration:** [time spent]

## Success Criteria
- [x] [criterion 1]
- [ ] [criterion 2]
- [ ] [criterion 3]

## Requirements Mapped
| REQ-ID | Description | Status |
|--------|-------------|--------|
| REQ-007 | User can create | ✅ |
| REQ-008 | User can edit | 🔄 |

## Plans
[Detailed plan breakdown for this phase]

## Key Files Modified
[List of files created/modified in this phase]

## Decisions Made
[Phase-specific decisions]
```

### Step 4: Recommend Next Action

Based on current state:

| State | Next Action |
|-------|-------------|
| No phases planned | `/coder:plan-phase 1` |
| Phase has no plans | `/coder:plan-phase N` |
| Plans pending execution | `/coder:execute-phase N` |
| Phase complete, not verified | `/coder:verify-work N` |
| All phases complete | `/coder:complete-milestone` |
| Paused | `/coder:resume` |
| Blocked | Address blocker, then resume |

Display:
```markdown
## Recommended Next Action

```
/coder:execute-phase 3
```

This will continue executing Phase 3 plans starting from Plan 3-03.
```

## Progress Bar Generation

Visual progress using block characters:
```
0%   [░░░░░░░░░░]
10%  [█░░░░░░░░░]
20%  [██░░░░░░░░]
30%  [███░░░░░░░]
40%  [████░░░░░░]
50%  [█████░░░░░]
60%  [██████░░░░]
70%  [███████░░░]
80%  [████████░░]
90%  [█████████░]
100% [██████████]
```

## Integration Points

- Reads from: STATE.md, ROADMAP.md, REQUIREMENTS.md
- Reads phase dirs: .planning/phases/*/
- Updates: Nothing (read-only command)
