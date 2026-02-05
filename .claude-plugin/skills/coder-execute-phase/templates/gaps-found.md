# Gaps Found Template

Use this template when verification status is `gaps_found`.

**CRITICAL: Do NOT proceed to completion. Do NOT call coder-end-plan.**

```markdown
## ⚠ Verification Found Gaps

**Score:** {N}/{M} must-haves verified
**Report:** {phase_dir}/VERIFICATION.md

### What's Missing

{Extract gap summaries from VERIFICATION.md}

| Must-Have | Status | Issue |
|-----------|--------|-------|
| {item} | ❌ | {why it failed} |
| {item} | ❌ | {why it failed} |

---

## ▶ Fix the Gaps

`/coder:plan-phase {N} --gaps`

Then re-execute: `/coder:execute-phase {N} --gaps-only`

<sub>`/clear` first → fresh context</sub>
```

**Replace:**
- `{N}/{M}` — Verified count / total must-haves
- `{phase_dir}` — Path to phase directory
- Gap table from VERIFICATION.md gaps section
