# Phase 06: Architecture

## Hook System

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code                              │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ SessionStart│      │ PreToolUse  │      │ PreCompact  │
│    Hook     │      │    Hook     │      │    Hook     │
└─────────────┘      └─────────────┘      └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Check for   │      │ Check edit  │      │ Save run    │
│ incomplete  │      │ permission  │      │ state       │
│ runs        │      │             │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    Reminder            Allow/Block           State saved
    message             decision              confirmation
```

## Hook Configuration

```json
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": {
          "tool_name": "Edit|Write|MultiEdit"
        },
        "hooks": [
          {
            "type": "command",
            "command": "python3 $ERIRPG_ROOT/erirpg/hooks/pretooluse.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $ERIRPG_ROOT/erirpg/hooks/precompact.py"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $ERIRPG_ROOT/erirpg/hooks/sessionstart.py"
          }
        ]
      }
    ]
  }
}
```

## PreToolUse Decision Flow

```
Input: tool_name, tool_input (file_path)
              │
              ▼
     ┌─────────────────┐
     │ Parse file_path │
     │ from tool_input │
     └─────────────────┘
              │
              ▼
     ┌─────────────────┐
     │ Detect project  │
     │ from file path  │
     └─────────────────┘
              │
              ▼
     ┌─────────────────┐         ┌─────────────────┐
     │ Quick fix       │───Yes──►│ File matches?   │
     │ active?         │         └─────────────────┘
     └─────────────────┘              │
              │ No               Yes ─┼─► ALLOW
              ▼                  No ──┼─► BLOCK
     ┌─────────────────┐              │
     │ Preflight state │──────────────┘
     │ exists?         │
     └─────────────────┘
              │
         Yes ─┼─► File in targets? ─Yes─► ALLOW
         No ──┼─► BLOCK                   │
              │                      No ──┼─► BLOCK
              ▼
         BLOCK with
         instructions
```

## Installation Structure

```
~/.claude/
├── settings.json        # Hook configuration
└── commands/
    └── eri/
        ├── execute.md   # /eri:execute
        ├── start.md     # /eri:start
        ├── guard.md     # /eri:guard
        └── status.md    # /eri:status

$ERIRPG_ROOT/
└── erirpg/
    └── hooks/
        ├── pretooluse.py
        ├── precompact.py
        └── sessionstart.py
```
