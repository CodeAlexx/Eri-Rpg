# SKILL.md Migration TODO

Migrate large skills to new Claude Code SKILL.md format with supporting files.

## Completed

- [x] `execute-phase.md` (432→141 lines) — 2026-02-05
- [x] `plan-phase.md` (436→166 lines) — 2026-02-05
- [x] `doctor.md` (743→141 lines) — 2026-02-05
- [x] `clone-behavior.md` (529→120 lines) — 2026-02-05
- [x] `add-feature.md` (510→115 lines) — 2026-02-05

**Status:** Needs testing before continuing

---

## Priority Candidates

| Skill | Lines | Benefit | Notes |
|-------|-------|---------|-------|
| `discuss-phase.md` | 407 | User interaction, question batches | |

## Maybe

| Skill | Lines | Benefit |
|-------|-------|---------|
| `handoff.md` | 502 | Doc generation, templates |
| `plan-milestone-gaps.md` | 366 | Analysis, dynamic context |
| `debug.md` | 338 | Structured debugging steps |
| `quick.md` | 317 | Ad-hoc task workflow |

## Skip (too small or reference-only)

- `template.md` (349) — meta template
- `learn.md` (345) — reference patterns
- `compare.md` (324) — single-purpose
- Others <320 lines

---

## Test Plan for First 2

### execute-phase

```bash
# 1. Start a test project or use existing
/coder:init

# 2. Plan a phase
/coder:plan-phase 1

# 3. Execute using new SKILL.md
/coder:execute-phase 1

# Verify:
# - Dynamic context injection works (!`command`)
# - Templates render correctly
# - Verification step runs
# - Completion box shows
```

### plan-phase

```bash
# 1. New phase or re-plan
/coder:plan-phase 2

# Verify:
# - Research depth detection works
# - Researcher spawns for Level 2-3
# - Confidence gate stops on LOW
# - Plans created with must_haves
# - Completion box shows
```

---

## Notes

- Original `.md` files preserved for rollback
- New format uses `!`command`` for dynamic context
- `disable-model-invocation: true` prevents auto-trigger
- Supporting files loaded on demand (reference.md, templates/)
