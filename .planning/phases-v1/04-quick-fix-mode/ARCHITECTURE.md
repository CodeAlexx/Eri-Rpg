# Phase 04: Architecture

## Quick Fix Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      quick start                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Create snapshot │
                  │  of target file  │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Save state to   │
                  │  quick_fix.json  │
                  └─────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    EDITING PHASE                             │
│                                                              │
│   PreToolUse Hook:                                          │
│   ├─ Edit target file? → ALLOW                              │
│   └─ Edit other file?  → BLOCK                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌─────────────────┐       ┌─────────────────┐
     │   quick-done    │       │  quick-cancel   │
     │                 │       │                 │
     │  • Check file   │       │  • Restore from │
     │    modified     │       │    snapshot     │
     │  • Git commit   │       │  • Clear state  │
     │  • Clear state  │       │                 │
     └─────────────────┘       └─────────────────┘
```

## State File

```json
// .eri-rpg/quick_fix.json
{
  "active": true,
  "file": "src/config.py",
  "description": "Update database timeout",
  "started_at": "2026-01-26T10:30:00",
  "snapshot_path": ".eri-rpg/snapshots/abc123.snap",
  "original_hash": "sha256:..."
}
```

## Hook Integration

```python
# In pretooluse.py

def check_quick_fix(project_path, target_file):
    state = load_quick_fix_state(project_path)
    
    if not state.get("active"):
        return False, "No active quick fix"
    
    if normalize(target_file) == normalize(state["file"]):
        return True, "Quick fix allows this file"
    
    return False, f"Quick fix only allows {state['file']}"
```

## Commands

| Command | Action |
|---------|--------|
| `quick <proj> <file> <desc>` | Start session |
| `quick-done <proj>` | Commit and end |
| `quick-cancel <proj>` | Restore and end |
| `quick-status <proj>` | Show current state |
