---
description: "Personal todo list - add, view, complete tasks"
user_invocable: true
---

<todo-command>

# /eri:todo - Personal Task Tracking

Quick personal todo list that persists across sessions.

## Quick Actions

**List todos:**
```bash
python3 -m erirpg.cli todo
```

**Add a todo:**
```bash
python3 -m erirpg.cli todo <text>
python3 -m erirpg.cli todo fix the auth bug
python3 -m erirpg.cli todo -p myproject add unit tests
python3 -m erirpg.cli todo --priority high urgent hotfix
```

**Complete a todo:**
```bash
python3 -m erirpg.cli todo-done <id>
```

**Remove a todo:**
```bash
python3 -m erirpg.cli todo-rm <id>
```

## Priority Levels

- 🔴 `--priority urgent` - Do now
- 🟠 `--priority high` - Do today
- ⚪ `--priority normal` - Default
- 🔵 `--priority low` - Whenever

## Options

- `-p, --project <name>` - Associate with project
- `--priority <level>` - Set priority
- `-t, --tag <tag>` - Add tags (can repeat)
- `--all` - Show completed too

## Examples

```bash
# Add simple todo
eri-rpg todo remember to update docs

# Add with project and priority
eri-rpg todo -p eri-rpg --priority high fix the test failures

# Add with tags
eri-rpg todo -t bug -t backend investigate memory leak

# List all including completed
eri-rpg todo --all

# Mark done
eri-rpg todo-done 3

# Clear completed
eri-rpg todo-clear
```

## Storage

Todos are stored in `~/.eri-rpg/todos.json` and persist across all sessions and projects.

</todo-command>
