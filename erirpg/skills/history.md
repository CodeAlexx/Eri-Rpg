# /coder:history - Execution History

Show execution history with decisions, metrics, and outcomes.

## CLI Integration

**First, call the CLI to get execution history:**
```bash
# Get recent history (default 20 entries)
erirpg coder-history

# Limit entries
erirpg coder-history --limit 50
```

This returns JSON with:
- `history`: Array of events with `type`, `timestamp`, `description`, `status`
- `count`: Number of entries returned

Types include: `phase` (from metrics), `commit` (from git)

Use this data to render the history display.

---

## Usage

```
/coder:history                     # Full project history
/coder:history --phase 2           # History for phase 2
/coder:history --decisions         # Only decisions
/coder:history --failures          # Only failures/rollbacks
/coder:history --today             # Today's activity
/coder:history --export            # Export to markdown
```

## Execution Steps

### Step 1: Gather History Data

```python
def gather_history(project):
    history = {
        "git_log": parse_git_log(),
        "state_history": parse_state_changes(),
        "summaries": load_all_summaries(),
        "decisions": extract_decisions(),
        "metrics": load_metrics(),
        "failures": extract_failures(),
        "rollbacks": extract_rollbacks()
    }
    return history
```

### Step 2: Present Timeline

```markdown
## Project History: my-app

**Created:** 2026-01-28
**Duration:** 3 days
**Phases:** 4/5 complete
**Total commits:** 47

### Timeline

#### 2026-01-30 (Today)
| Time | Event | Details |
|------|-------|---------|
| 14:30 | Phase 3 verified | All tests pass |
| 14:00 | Execute Phase 3 | 3 plans, 8 tasks |
| 13:30 | Rollback Plan 03-02 | Validation too strict |
| 12:00 | Plan Phase 3 | Created 3 plans |
| 10:00 | Phase 2 complete | Milestone check |

#### 2026-01-29
| Time | Event | Details |
|------|-------|---------|
| 16:00 | Phase 2 verified | UAT passed |
| 14:00 | Execute Phase 2 | 4 plans, 12 tasks |
| 11:00 | Decision: JWT auth | Chose over sessions |
| 10:00 | Plan Phase 2 | Created 4 plans |
| 09:00 | Research complete | 4 agents finished |

#### 2026-01-28
| Time | Event | Details |
|------|-------|---------|
| 15:00 | Roadmap created | 5 phases planned |
| 14:00 | Requirements defined | 24 features |
| 12:00 | Research started | 4 parallel agents |
| 10:00 | Project initialized | Greenfield |
```

### Step 3: Decision History

```markdown
## Decisions Made

### Architectural Decisions
| # | Decision | Choice | Alternatives | Phase |
|---|----------|--------|--------------|-------|
| 1 | Framework | Next.js | Remix, Astro | Init |
| 2 | Database | PostgreSQL | MongoDB, SQLite | Init |
| 3 | Auth strategy | JWT | Sessions | Phase 2 |
| 4 | State management | Zustand | Redux, Jotai | Phase 3 |

### Decision Details

#### D3: Auth Strategy (Phase 2)
**Date:** 2026-01-29 11:00
**Decision:** Use JWT tokens for authentication
**Alternatives considered:**
- Server-side sessions with Redis

**Rationale:**
- Simpler infrastructure (no Redis needed)
- Better scalability for stateless API
- Lower latency (no session lookup)

**Trade-offs accepted:**
- Harder to invalidate tokens
- Larger cookie size

**Recorded in:** `.planning/phases/02-auth/02-01-SUMMARY.md`
```

### Step 4: Failure/Rollback History

```markdown
## Failures & Rollbacks

### Rollbacks
| Date | Phase/Plan | Reason | Resolution |
|------|------------|--------|------------|
| 01-30 | 03-02 | Validation too strict | Replayed with fixes |

### Verification Failures
| Date | Phase | Gaps | Resolution |
|------|-------|------|------------|
| 01-29 | 2 | Token refresh missing | Fixed in 02-03 |

### Debug Sessions
| Date | Issue | Root Cause | Duration |
|------|-------|------------|----------|
| 01-29 | Login fails | Hash mismatch | 15 min |

### Lessons Learned
1. **Validation:** Always test with edge case data
2. **Auth:** Include token refresh from start
3. **Testing:** Add integration tests earlier
```

### Step 5: Metrics History

```markdown
## Execution Metrics

### Overall
| Metric | Value |
|--------|-------|
| Total time | 12h 30m |
| Total tokens | 285,000 |
| Total cost | $2.28 |
| Plans executed | 14 |
| Tasks completed | 42 |
| Files created | 67 |
| Lines of code | 3,450 |

### By Phase
| Phase | Duration | Tokens | Cost | Plans | Tasks |
|-------|----------|--------|------|-------|-------|
| Init | 45m | 50,000 | $0.40 | - | - |
| Phase 1 | 1h 30m | 30,000 | $0.24 | 2 | 6 |
| Phase 2 | 3h | 60,000 | $0.48 | 4 | 12 |
| Phase 3 | 2h 15m | 45,000 | $0.36 | 3 | 9 |
| Phase 4 | 1h 30m | 25,000 | $0.20 | 2 | 6 |

### Trends
```
Tokens per phase:
Phase 1: ████████░░ 30K
Phase 2: ████████████████ 60K
Phase 3: ████████████░░░░ 45K
Phase 4: ██████░░░░ 25K

Time per phase:
Phase 1: ████░░░░░░ 1.5h
Phase 2: ██████████ 3h
Phase 3: ███████░░░ 2.25h
Phase 4: ████░░░░░░ 1.5h
```
```

### Step 6: Git Activity

```markdown
## Git History

### Commits by Type
| Type | Count | % |
|------|-------|---|
| feat | 28 | 60% |
| test | 10 | 21% |
| fix | 5 | 11% |
| refactor | 3 | 6% |
| docs | 1 | 2% |

### Commits by Phase
| Phase | Commits | Files Changed |
|-------|---------|---------------|
| Phase 1 | 8 | 15 |
| Phase 2 | 18 | 28 |
| Phase 3 | 14 | 22 |
| Phase 4 | 7 | 12 |

### Recent Commits
```
xyz789 14:30 feat(03-03): Add shopping cart
uvw456 14:15 test(03-03): Cart unit tests
rst123 14:00 feat(03-02): Product catalog
...
```
```

## Filter Modes

### --decisions
Only show decisions made:
```markdown
## Decision History
[Only decision section]
```

### --failures
Only show failures and rollbacks:
```markdown
## Failure History
[Only failure/rollback section]
```

### --today
Only today's activity:
```markdown
## Today's Activity (2026-01-30)
[Only today's timeline]
```

### --phase N
Only specific phase:
```markdown
## Phase 2 History
[Only Phase 2 events]
```

## Export Format

```
/coder:history --export
```

Creates `.planning/HISTORY.md`:
```markdown
# Project History: my-app

Generated: 2026-01-30T15:00:00Z

## Summary
[Project summary]

## Timeline
[Full timeline]

## Decisions
[All decisions]

## Metrics
[All metrics]

## Lessons Learned
[Accumulated lessons]
```

## Integration Points

- Reads: Git log, STATE.md, all SUMMARY.md files
- Reads: .planning/metrics.json
- Reads: Debug session history
- Exports: HISTORY.md
- Displays: Formatted timeline, metrics, decisions
