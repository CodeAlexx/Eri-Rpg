# Claude Code Integration

EriRPG integrates with Claude Code through hooks that enforce its workflow during AI-assisted coding sessions.

## Overview

Three hooks are provided:

| Hook | Purpose | When Called |
|------|---------|-------------|
| PreToolUse | Block unauthorized edits | Before Edit/Write/MultiEdit |
| PreCompact | Save state before compaction | Before context is compacted |
| SessionStart | Remind about incomplete runs | At session start |

## Installation

### 1. Set Environment Variable

```bash
export ERIRPG_ROOT=/path/to/eri-rpg
```

Add to your shell profile for persistence.

### 2. Configure Claude Code Hooks

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/pretooluse.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/precompact.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/sessionstart.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## Hook Behaviors

### PreToolUse Hook

**Purpose**: Enforce preflight requirement before file edits.

**Behavior**:
1. Checks for quick fix mode (allows single-file edits)
2. Checks for active run with preflight completed
3. Verifies target file is in preflight list
4. Returns `allow` or `block` decision

**Example block message**:
```
ERI-RPG ENFORCEMENT: No active run.
File: src/utils.py

Start an EriRPG run first:
  from erirpg.agent import Agent
  agent = Agent.from_goal('task', project_path='/path/to/project')
  agent.preflight(['src/utils.py'], 'modify')

Or use quick fix for single-file edits:
  eri-rpg quick project src/utils.py "description"
```

### PreCompact Hook

**Purpose**: Save run state before Claude Code compacts context.

**Behavior**:
1. Finds active run in current project
2. Creates `resume.md` file with state summary
3. Outputs system message to preserve in compacted context

**Output example**:
```
EriRPG Run Active: abc123
  Goal: Add user authentication...
  Progress: 2/5 steps

Resume with: /eri:execute or /eri:status
```

### SessionStart Hook

**Purpose**: Remind about incomplete work at session start.

**Behavior**:
1. Checks for incomplete runs
2. Checks for active quick fixes
3. Checks for resume.md from previous compaction
4. Outputs reminder message

**Output example**:
```
EriRPG: 3 incomplete run(s) in myproject
  - abc123: Add authentication... (2/5 steps)
  - def456: Fix validation... (1/3 steps)
  ... and 1 more
Resume: /eri:execute
```

## Plugin Commands

Optional slash commands can be installed for Claude Code:

### Setup

```bash
# Copy plugin to Claude commands directory
ln -sf ~/eri-rpg-plugin/commands ~/.claude/commands/eri
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/eri:execute` | Full spec-driven workflow |
| `/eri:quick` | Single-file quick fix |
| `/eri:status` | Show current state |
| `/eri:learn` | Read-only learning |
| `/eri:rollback` | Restore previous version |
| `/eri:cleanup` | Manage stale runs |

### Usage

In Claude Code:
```
/eri:execute Add input validation to all forms
/eri:quick src/utils.py "Fix typo in docstring"
/eri:status
```

## Workflow: Quick Fix

The simplest integration - single file edits:

1. Claude says: "I'll fix the typo in utils.py"
2. Claude runs: `eri-rpg quick myproject src/utils.py "Fix typo"`
3. Hook allows the edit
4. Claude makes the edit
5. Claude runs: `eri-rpg quick-done myproject`
6. Change is committed

## Workflow: Full Agent

For complex multi-file changes:

1. Claude creates agent:
   ```python
   from erirpg.agent import Agent
   agent = Agent.from_goal("Add authentication", project_path="...")
   ```

2. Before each edit:
   ```python
   report = agent.preflight(["src/auth.py", "src/users.py"], "modify")
   ```

3. Edits are allowed by hook

4. After edits:
   ```python
   agent.complete_step(files_touched=["src/auth.py", "src/users.py"])
   ```

5. Verification runs automatically

## Debugging

### Check hook logs

```bash
tail -f /tmp/erirpg-hook.log
tail -f /tmp/erirpg-precompact.log
tail -f /tmp/erirpg-sessionstart.log
```

### Test hook manually

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/test.py"},"cwd":"/tmp"}' | \
  python3 $ERIRPG_ROOT/erirpg/hooks/pretooluse.py
```

### Common Issues

**Hook fails to run**:
- Check `ERIRPG_ROOT` is set
- Verify Python can import erirpg
- Check script path is correct

**Always blocked**:
- Clear stale preflight: `rm .eri-rpg/preflight_state.json`
- Start quick fix or use agent with preflight

**Module import error**:
- Known issue: `hooks.py` shadows `hooks/` directory
- Use direct script path, not `-m` module import

## Disabling Hooks

To temporarily disable enforcement:

1. Remove hooks from `~/.claude/settings.json`
2. Or delete the `.eri-rpg` directory in project
3. Or write files to `/tmp/` (always allowed)
