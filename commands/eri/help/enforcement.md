# EriRPG Enforcement Explained

## What is Enforcement?

Enforcement = hooks that protect your code from accidental/unauthorized edits.

When enabled, you MUST use EriRPG commands to edit files:
- `/eri:quick` for single files
- `/eri:execute` for multi-file work

Direct edits are blocked.

## Two Modes

### Bootstrap Mode (No Enforcement)
- Hooks pass through
- Direct edits allowed
- Good for: New projects, learning, experimentation

### Maintain Mode (Full Enforcement)
- Hooks block unauthorized edits
- Must use EriRPG commands
- Good for: Production code, team projects

## Checking Mode
```bash
eri-rpg mode myproject
```

## Changing Mode
```bash
# Disable enforcement
eri-rpg mode myproject --bootstrap

# Enable enforcement
eri-rpg mode myproject --maintain
```

## How Hooks Work

1. **PreToolUse Hook** - Runs before every Edit/Write
   - Checks for active run or quick fix
   - Checks file is in preflight list
   - Blocks if not authorized

2. **What Gets Blocked**
   - Edit tool without active run
   - Write tool without active run
   - Files not declared in preflight

3. **What's Always Allowed**
   - Reading files
   - Files in `/tmp/`
   - Files in `.eri-rpg/` directory

## Troubleshooting

**"I'm blocked!"**
```bash
# Check status
eri-rpg status myproject

# Quick fix: disable enforcement
eri-rpg mode myproject --bootstrap

# Or start a proper run
/eri:quick myproject file.py "description"
```

## Graduation

When ready to lock down your project:
```bash
eri-rpg graduate myproject
```

This:
1. Indexes the codebase
2. Learns all files
3. Enables maintain mode
4. Enables full enforcement
