# Troubleshooting: "I'm Blocked by EriRPG"

## Quick Fixes

### 1. Check What's Blocking
```bash
eri-rpg status myproject
```

### 2. Clear Stale State
```bash
# Remove preflight state
rm .eri-rpg/preflight_state.json

# Remove quick fix state
rm .eri-rpg/quick_fix_state.json

# Or reset everything
eri-rpg reset myproject
```

### 3. Disable Enforcement Temporarily
```bash
eri-rpg mode myproject --bootstrap
```
This disables hooks. Re-enable with `--maintain` when ready.

---

## Common Causes

### "No active run"
You tried to edit without starting a run.

**Fix:** Start a run first:
```bash
/eri:quick myproject file.py "description"
# or
/eri:execute "your goal"
```

### "File not in preflight"
You're editing a file that wasn't declared.

**Fix:** Either:
- Add file to preflight: `eri-rpg preflight myproject file.py`
- Use quick fix for single file: `/eri:quick myproject file.py "desc"`
- Reset and start over: `eri-rpg reset myproject`

### "Stale preflight state"
Previous session crashed, left state behind.

**Fix:**
```bash
rm .eri-rpg/preflight_state.json
```

### "Run is incomplete"
There's an old run blocking new work.

**Fix:**
```bash
eri-rpg cleanup myproject --prune
# or manually
rm .eri-rpg/runs/*.json
```

---

## Nuclear Option

If nothing works:
```bash
# 1. Disable enforcement
eri-rpg mode myproject --bootstrap

# 2. Clear all state
rm -rf .eri-rpg/runs/
rm -f .eri-rpg/preflight_state.json
rm -f .eri-rpg/quick_fix_state.json

# 3. Re-enable when ready
eri-rpg mode myproject --maintain
```

---

## Prevention

- Always use `/eri:quick` or `/eri:execute` for edits
- Run `eri-rpg done` when finished
- Run `eri-rpg handoff` before ending sessions
