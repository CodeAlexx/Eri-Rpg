# /eri:settings - EriRPG Settings

Configure EriRPG features and UI elements.

## Usage

```bash
/eri:settings                    # Show current settings
/eri:settings statusline         # Configure status line elements
/eri:settings statusline toggle phase    # Toggle phase display
/eri:settings workflow           # Show workflow settings
/eri:settings workflow auto-commit [on|off]  # Toggle auto-commit
/eri:settings workflow auto-push [on|off]    # Toggle auto-push
```

## Arguments
- `$ARGUMENTS` - Subcommand and options

## Execution

1. **No arguments**: Show all current settings
2. **statusline**: Show/configure status line elements
3. **statusline toggle [element]**: Enable/disable specific element
4. **workflow**: Show/configure workflow behavior
5. **workflow auto-commit [on|off]**: Enable/disable auto-commit after task completion

## Settings Files

**Global settings**: `~/.eri-rpg/settings.json`
```json
{
  "statusline": {
    "enabled": true,
    "elements": {
      "phase": true,
      "context": true,
      "task": true,
      "time": false
    }
  }
}
```

**Project settings**: `.eri-rpg/config.json`
```json
{
  "workflow": {
    "auto_commit": true,
    "auto_push": false
  }
}
```

## Workflow Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_commit` | `true` | Auto-commit after completing tasks (prevents losing work) |
| `auto_push` | `false` | Auto-push after commits (disabled for safety) |

## Status Line Elements

| Element | Example | Description |
|---------|---------|-------------|
| `phase` | `Phase 3/6` | Current workflow phase |
| `context` | `45% ctx` | Context window usage |
| `task` | `backend` | Active task/phase name |
| `time` | `12m` | Session duration |
