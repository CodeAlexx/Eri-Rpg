# /eri:settings - EriRPG Settings

Configure EriRPG features and UI elements.

## Usage

```bash
/eri:settings                    # Show current settings
/eri:settings statusline         # Configure status line elements
/eri:settings statusline toggle phase    # Toggle phase display
/eri:settings statusline toggle context  # Toggle context % display
/eri:settings statusline toggle task     # Toggle task display
/eri:settings statusline toggle time     # Toggle session time
```

## Arguments
- `$ARGUMENTS` - Subcommand and options

## Execution

1. **No arguments**: Show all current settings
2. **statusline**: Show/configure status line elements
3. **statusline toggle [element]**: Enable/disable specific element

## Settings File

Settings stored in: `~/.eri-rpg/settings.json`

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

## Status Line Elements

| Element | Example | Description |
|---------|---------|-------------|
| `phase` | `Phase 3/6` | Current workflow phase |
| `context` | `45% ctx` | Context window usage |
| `task` | `backend` | Active task/phase name |
| `time` | `12m` | Session duration |
