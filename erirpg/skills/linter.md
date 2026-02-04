---
name: coder:linter
description: Validate workflow health contracts (skill completion + coupling checks)
argument-hint: "[--verbose]"
allowed-tools:
  - Bash
  - Read
---

# Coder Linter

Run the coder workflow linter and surface actionable fixes.

## Step 1: Run CLI Linter

```bash
python3 -m erirpg.cli coder-linter $ARGUMENTS
```

This returns JSON with:
- `ok`: overall pass/fail
- `failed`: number of failing skills
- `failed_skills`: each failing skill + missing requirements

## Step 2: Report Results

- If `ok` is `true`, confirm workflow contracts are healthy.
- If `ok` is `false`, list each failing skill and missing checks.

## Step 3: Suggest Fixes

Map each missing item to next action:
- Missing `<completion> section` -> add `<completion>...</completion>` block
- Missing `STATE.md update` -> add explicit state update step
- Missing `switch command` -> add `python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true`
- Missing `/clear box` -> add explicit `/clear`, `/coder:init`, and next-command box

When failures exist, recommend:
1. Fix the listed skill files
2. Re-run `/coder:linter`
3. Then run `/coder:doctor`
