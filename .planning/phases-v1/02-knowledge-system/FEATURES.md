# Phase 02: Features

## Learning Storage

### Learn Command
```bash
eri-rpg learn myproject src/utils.py
```
Interactive prompt for:
- Summary (one line)
- Purpose (what problem it solves)
- Key functions (name → description)
- Gotchas (things to watch out for)
- Dependencies

### Batch Learning
```bash
eri-rpg learn myproject src/ --batch
```
Learn all files in directory (not fully implemented).

### Auto-Learning
When completing a step, automatically learn touched files:
```python
agent.complete_step(files_touched=["src/utils.py"])
# Triggers auto-learn of utils.py
```

## Recall

### Basic Recall
```bash
eri-rpg recall myproject src/utils.py
```
Shows stored learning with staleness warning if file changed.

### Context Format
```python
context = format_for_context(learning)
# Returns markdown-formatted learning for LLM context
```

## Staleness Detection

### How It Works
1. Store file hash when learning
2. On recall, compare current hash
3. If different, mark as stale
4. Show warning but still return learning

### Staleness Check
```python
if is_stale(learning, project_path):
    print("⚠️ File changed since last learned")
```

## Rollback

### Code Rollback
```bash
eri-rpg rollback myproject src/utils.py --code
```
Restores file content from snapshot taken during preflight.

### Learning Rollback
```bash
eri-rpg rollback myproject src/utils.py --learning
```
Restores previous version of learning (from version history).

### List Snapshots
```bash
eri-rpg rollback myproject src/utils.py
```
Shows available snapshots with timestamps.
