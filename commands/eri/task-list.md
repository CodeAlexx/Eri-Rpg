---
description: "View project tasks from TASKS.md - list, filter, or open in viewer"
user_invocable: true
---

<task-list-command>

# /eri:task-list - Project Task Viewer

View and manage tasks from the project's TASKS.md file.

## Arguments
- `$ARGUMENTS` - Optional filter: "pending", "completed", "all", or search term

## Quick Actions

**List all tasks:**
```bash
cat <project>/.eri-rpg/TASKS.md
```

**Show in viewer (if available):**
```bash
# Try glow for pretty markdown
glow <project>/.eri-rpg/TASKS.md 2>/dev/null || cat <project>/.eri-rpg/TASKS.md
```

## Execution

1. **Find active project:**
   - Check cwd for `.eri-rpg/` directory
   - Or use `~/.eri-rpg/state.json` active_project

2. **Read TASKS.md:**
   ```bash
   cat <project_path>/.eri-rpg/TASKS.md
   ```

3. **Filter if requested:**
   - `pending` - Show only unchecked `- [ ]` items
   - `completed` - Show only checked `- [x]` items
   - `all` - Show everything (default)
   - Other text - Search for matching tasks

4. **Display:**
   - Use markdown formatting
   - Group by section (Completed, Pending, Bugs/Issues)

## Output Format

```markdown
# Tasks: <project>

## Pending (3)
- [ ] Task one
- [ ] Task two
- [ ] Task three

## Completed (5)
- [x] Done task one
- [x] Done task two
...

## Bugs/Issues (1)
- [ ] **BUG: description**
```

## Examples

```bash
# Show all tasks
/eri:task-list

# Show only pending
/eri:task-list pending

# Show only completed
/eri:task-list completed

# Search for specific task
/eri:task-list auth
```

</task-list-command>
