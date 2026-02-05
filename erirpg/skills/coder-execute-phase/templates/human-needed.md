# Human Verification Template

Use this template when verification status is `human_needed`.

```markdown
## ✓ Automated Checks Passed — Human Verification Required

{N} items need manual testing:

### Human Verification Checklist

{Extract from VERIFICATION.md human_verification section}

- [ ] {item 1} — {how to test}
- [ ] {item 2} — {how to test}
- [ ] {item 3} — {how to test}

---

After testing, respond:
- **"approved"** → I'll complete the phase
- **Describe issues** → I'll route to gap closure
```

**Wait for user response before proceeding.**

**Replace:**
- `{N}` — Count of human verification items
- Checklist from VERIFICATION.md human_verification section
