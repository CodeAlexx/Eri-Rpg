---
name: coder:status
description: Quick status check - current phase, progress, next action
argument-hint: ""
allowed-tools:
  - Bash
  - Read
---

## CLI Integration

**Call the CLI to get status:**
```bash
python3 -m erirpg.cli coder-phase-list --json
```

---

## Usage

```
/coder:status          # Quick status
```

For detailed breakdown, use `/coder:progress --detailed`.

## Execution Steps

### Step 1: Get Phase Status

```bash
python3 -m erirpg.cli coder-phase-list --json
```

### Step 2: Read STATE.md

```bash
cat .planning/STATE.md 2>/dev/null
```

### Step 3: Display Quick Status

Format output as:

```
╔══════════════════════════════════════════════════╗
║  PROJECT: {name}                                 ║
║  STATUS: {idle|executing|verifying|paused}       ║
╠══════════════════════════════════════════════════╣
║  Phase {N}/{total}: {phase name}                 ║
║  Progress: [████████░░] {percent}%               ║
║                                                  ║
║  Last: {last action from STATE.md}               ║
╚══════════════════════════════════════════════════╝

▶ NEXT: {recommended command}
```

### Step 4: Determine Next Action

| State | Command |
|-------|---------|
| Phase not planned | `/coder:plan-phase N` |
| Phase planned, not executed | `/coder:execute-phase N` |
| Phase executed, not verified | `/coder:verify-work N` |
| Phase verified | `/coder:plan-phase N+1` |
| All complete | `/coder:complete-milestone` |
| Paused | `/coder:init` to resume |

## Notes

- This is a quick check - no file writes
- For full metrics use `/coder:progress --detailed`
- For session recovery use `/coder:init`
