# /coder:init - Session Context Recovery

Recover session context after /clear or at session start.

## CLI Integration

**First, call the CLI to get active project:**
```bash
python3 -m erirpg.commands.coder_init --json
```

This returns:
- `active_project`: Name and path of the active project (may differ from cwd)
- `context.files`: Paths to context files that exist
- `instructions`: What to read and do next

## Process

### Step 1: Call CLI

```bash
python3 -m erirpg.commands.coder_init --json
```

Parse the JSON response.

### Step 2: Read Context Files

From `context.files`, read each file that exists:
- CLAUDE.md - Project instructions
- STATE.md - Current phase and progress
- ROADMAP.md - Phase roadmap
- RESUME.md - Resume point (if paused)

**Important**: Use the paths from CLI response, NOT relative paths.
The active project may be in a different directory than cwd.

### Step 3: Present to User

If active project found:
```
Session recovered:
- Project: {name}
- Path: {path}
- Phase: {from STATE.md if exists}
- Status: {from STATE.md if exists}

{Note if cwd differs from active project}

Ready to continue. What's next?
```

If no active project:
```
No active project found.
Current directory: {cwd}

Options:
- /coder:new-project to start a new project
- /eri:switch <project> to activate an existing project
```

### Step 4: Wait

Do NOT execute any actions until user provides instructions.

## When to Run

- After /clear command
- At session start
- After context compaction
- When user types /coder:init
