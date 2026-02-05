# ERI Workflow Quickstart

You've got code. You need to change it. Here's how to do that without Claude forgetting what it just read.

---

## The Problem

You ask Claude to fix something. It reads 10 files to understand the code. Makes the fix. You `/clear` because context is full. Now you need another fix — and Claude has to re-read those same 10 files again.

Multiply that by a day of work. You're burning tokens re-reading code Claude already understood.

ERI fixes that. Claude reads once, remembers forever.

---

## What You Get

- **Memory that persists** — Claude stores what it learns about your code
- **Quick fixes without ceremony** — Single-file edits with automatic rollback
- **Structured runs for bigger changes** — When you need more than a quick fix
- **No re-reading** — Claude recalls knowledge instead of re-reading files

---

## Setup (2 minutes)

```bash
# Clone and install
git clone https://github.com/CodeAlexx/Eri-Rpg.git
cd Eri-Rpg
pip install -e .

# Install Claude Code integration
erirpg install

# Register your project
erirpg add myproject /path/to/your/code

# Index it (so Claude can recall later)
erirpg index myproject
```

Done. Your project is registered and indexed.

---

## Quick Fixes (Most Common)

Need to change one file? Don't overthink it.

```
/eri:quick src/auth.py "fix the token expiry check"
```

What happens:
1. Claude snapshots the file (so you can undo)
2. Makes the edit
3. You check it
4. Done — or rollback if it's wrong

That's it. No planning docs, no ceremony. Just fix and move on.

---

## When You Need More Than a Quick Fix

Multi-file change? New feature? Use a proper run.

### Step 1: Start the session

```
/eri:start
```

Claude loads your project context. Knows what's indexed, what patterns exist.

### Step 2: Tell it what you want

```
/eri:execute "add rate limiting to the API endpoints"
```

Claude:
1. Creates a spec (what needs to happen)
2. Plans the steps
3. Executes each step with verification
4. Commits when done

### Step 3: Check progress anytime

```
/eri:status
```

Shows where you are, what's done, what's next.

---

## The Memory System

This is the magic part.

### Claude learns as it reads

```
/eri:learn src/auth.py
```

Claude reads the file, extracts the important bits (what it does, how it works, key patterns), and stores that.

Next time? It doesn't re-read. It recalls.

### Recall instead of re-read

```
/eri:recall src/auth.py
```

Claude gets its stored knowledge back instantly. No token cost for re-reading.

### See what Claude knows

```
/eri:knowledge
```

Lists everything Claude has learned about your project.

---

## The Commands

### Everyday Commands

| Command | What it does |
|---------|--------------|
| `/eri:quick file "desc"` | Single-file fix with snapshot |
| `/eri:start` | Begin a coding session |
| `/eri:execute "goal"` | Multi-step change with verification |
| `/eri:status` | Where am I? What's next? |
| `/eri:resume` | Pick up where you left off |

### Memory Commands

| Command | What it does |
|---------|--------------|
| `/eri:learn file` | Store knowledge about a file |
| `/eri:recall file` | Get stored knowledge back |
| `/eri:knowledge` | List all stored knowledge |
| `/eri:index` | Re-index the whole project |

### Debugging

| Command | What it does |
|---------|--------------|
| `/eri:debug "problem"` | Triage-first debugging |
| `/eri:find "query"` | Find modules matching a query |

---

## Coming Back After a Break

```
/eri:resume
```

Claude reads your session state, recalls relevant knowledge, and continues.

Or if you want a fresh start on the same project:

```
/eri:start
```

---

## How It Works

**Registry** — Your projects are registered with ERI. It knows where they are and what language they use.

**Index** — When you index, Claude builds a dependency graph. Knows what calls what, what imports what.

**Knowledge** — When Claude reads a file, it can store what it learned. This persists across sessions.

**Runs** — For bigger changes, a "run" tracks what you're doing: the goal, the steps, what's done.

The files live in `~/.eri-rpg/` (global) and `.eri-rpg/` (per-project).

---

## Quick Fix vs Full Run

**Use quick fix when:**
- One file
- Simple change
- You know exactly what to do

**Use a full run when:**
- Multiple files
- Need to think through the approach
- Want verification and commits

Most day-to-day work is quick fixes. Save the full runs for features.

---

## Tips

**Index after big changes.** If you restructured things, re-index so Claude's knowledge stays current.

**Learn the files you touch often.** Authentication, config, core models — learn these once, recall forever.

**Use recall liberally.** Before asking Claude to change something, `/eri:recall` the relevant files. Context is cheaper than re-reading.

**Trust the snapshots.** Quick fix went wrong? The snapshot is there. Don't be afraid to try things.

---

## That's It

```
/eri:quick file "fix"     # one-off fixes
/eri:start                # begin session
/eri:execute "goal"       # bigger changes
/eri:recall file          # remember, don't re-read
```

Four patterns. Everything else is variations.

Go fix something.
