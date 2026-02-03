# /coder:plan-milestone-gaps - Create Phases for Audit Gaps

After verification failures, create new phases to address identified gaps.

## CLI Integration

**First, call the CLI to find gaps:**
```bash
erirpg coder-gaps
```

This returns JSON with:
- `gaps`: Array of gap objects with phase, status, score, gaps_content
- `count`: Number of gaps found

Use this data to create targeted gap phases.

---

## Usage

```
/coder:plan-milestone-gaps                 # From all verification gaps
/coder:plan-milestone-gaps --phase 3       # From specific phase gaps
/coder:plan-milestone-gaps --dry-run       # Preview without creating
```

## Purpose

When `/coder:verify-work` or milestone audit finds gaps:
- Missing functionality
- Failed integrations
- Incomplete features
- Broken connections

This command creates targeted phases to close those gaps.

## Execution Steps

### Step 1: Collect Gap Data

Scan for verification failures:

```python
# Sources of gaps
gap_sources = [
    ".planning/phases/*/VERIFICATION.md",  # Phase verifications
    ".planning/phases/*/UAT.md",            # User acceptance tests
    ".planning/AUDIT.md",                   # Milestone audit
]

gaps = []
for source in gap_sources:
    if source.status in ["gaps_found", "failed"]:
        gaps.extend(source.gaps)
```

### Step 2: Present Gaps Summary

```markdown
# Gap Analysis

## Gaps Found

### From Phase 3 Verification
| # | Truth | Status | Issue |
|---|-------|--------|-------|
| 1 | User can see existing messages | ❌ Failed | No API call in Chat.tsx |
| 2 | Messages persist | ❌ Failed | Database not connected |

### From Phase 4 UAT
| # | Test | Status | Issue |
|---|------|--------|-------|
| 1 | Send message | ❌ Failed | Submit handler not wired |
| 2 | Delete message | ❌ Failed | Delete endpoint returns 404 |

### From Milestone Audit
| # | Integration | Status | Issue |
|---|-------------|--------|-------|
| 1 | Auth → Chat | ❌ Failed | User context not passed |

## Gap Categories

| Category | Count | Severity |
|----------|-------|----------|
| Missing wiring | 3 | High |
| Incomplete implementation | 2 | Medium |
| Integration failures | 1 | High |

**Total gaps:** 6
**Estimated effort:** 2-3 phases
```

### Step 3: Generate Gap Phases

Group related gaps into coherent phases:

```markdown
## Proposed Gap Phases

### Gap Phase A: Message System Wiring

**Goal:** Complete message display and persistence

**Addresses:**
- Gap 1: Chat.tsx API integration
- Gap 2: Database connection

**Proposed work:**
1. Add useEffect with fetch to Chat.tsx
2. Connect chat API to database
3. Verify messages display correctly

**Estimated:** 1 plan, 2-3 tasks

---

### Gap Phase B: Message Actions

**Goal:** Complete message CRUD operations

**Addresses:**
- Gap 3: Submit handler
- Gap 4: Delete endpoint

**Proposed work:**
1. Wire submit button to API
2. Fix delete endpoint routing
3. Add error handling

**Estimated:** 1 plan, 2-3 tasks

---

### Gap Phase C: Auth Integration

**Goal:** Pass authenticated user context to chat

**Addresses:**
- Gap 5: Auth → Chat integration

**Proposed work:**
1. Pass user context through middleware
2. Update chat components to use user
3. Verify user info displays in messages

**Estimated:** 1 plan, 2 tasks

---

## Summary

| Phase | Name | Gaps Addressed | Est. Plans |
|-------|------|----------------|------------|
| A | Message System Wiring | 2 | 1 |
| B | Message Actions | 2 | 1 |
| C | Auth Integration | 1 | 1 |

**Total:** 3 gap phases, ~5 gaps addressed

Create these phases? (yes/no/edit)
```

### Step 4: Create Gap Phases

On confirmation:

1. **Update ROADMAP.md** - Insert gap phases:
```markdown
## Phase 6: Gap - Message System Wiring (inserted)

**Goal:** Complete message display and persistence

**Addresses Gaps:**
- Phase 3 Verification: Gap 1, Gap 2

**Success Criteria:**
- Chat.tsx calls /api/messages on load
- Messages display from database
- New messages persist correctly

**Requirements Mapped:**
- REQ-012: Message display (gap closure)
```

2. **Create phase directories:**
```
.planning/phases/
└── 06-gap-message-wiring/
    └── (ready for planning)
```

3. **Update STATE.md:**
```markdown
## Gap Phases Added
- Phase 6: Message Wiring (from Phase 3 gaps)
- Phase 7: Message Actions (from Phase 4 UAT)
- Phase 8: Auth Integration (from Audit)

**Next action:** /coder:plan-phase 6
```

4. **Link back to verification:**
```markdown
# In original VERIFICATION.md
## Gap Resolution
Gaps addressed by Phase 6 (Gap - Message System Wiring)
```

### Step 5: Execution Path

```markdown
## Next Steps

Gap phases created. Execute in order:

1. `/coder:plan-phase 6` - Plan message wiring
2. `/coder:execute-phase 6` - Execute
3. `/coder:verify-work 6` - Verify gaps closed

Then continue with phases 7, 8.

After all gap phases complete:
- Re-run `/coder:verify-work` on original failing phases
- Continue to `/coder:complete-milestone` when all pass
```

## Dry Run Mode

`/coder:plan-milestone-gaps --dry-run`:
```markdown
# Gap Phases Preview (Dry Run)

**No changes will be made.**

## Would Create

### Phase 6: Gap - Message System Wiring
- 2 gaps addressed
- 1 plan estimated

### Phase 7: Gap - Message Actions
- 2 gaps addressed
- 1 plan estimated

---

Run without --dry-run to create phases.
```

## Phase-Specific Mode

`/coder:plan-milestone-gaps --phase 3`:
```markdown
# Gap Phases for Phase 3 Only

Only addressing gaps from Phase 3 verification.

## Gaps from Phase 3
[List only Phase 3 gaps]

## Proposed Phase
[Single phase for Phase 3 gaps]
```

## Gap Grouping Logic

Gaps are grouped by:

1. **Technical domain** - Auth gaps together, UI gaps together
2. **File overlap** - Gaps affecting same files grouped
3. **Dependency** - Dependent gaps in same phase
4. **Effort** - Keep phases small (1-2 plans each)

```python
def group_gaps(gaps):
    groups = []
    for gap in gaps:
        matched = False
        for group in groups:
            if overlaps(gap, group) and len(group) < 3:
                group.append(gap)
                matched = True
                break
        if not matched:
            groups.append([gap])
    return groups
```

## Integration with Workflow

```
verify-work N
    │
    ▼ (gaps found)
    │
plan-milestone-gaps
    │
    ▼ (creates gap phases)
    │
plan-phase → execute-phase → verify-work
    │
    ▼ (gaps closed)
    │
complete-milestone
```
