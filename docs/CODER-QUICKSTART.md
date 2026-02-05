# Coder Workflow Quickstart

You've got Claude. You want to build something. Here's how to actually get it done without the usual mess.

---

## The Problem

Claude forgets things. You start a project, get halfway through, context fills up, you `/clear`, and suddenly Claude has no idea what you were building or why.

You end up repeating yourself. Explaining the same architecture. Re-reading the same files. Watching Claude make the same mistakes you already corrected.

This fixes that.

## What You Get

A workflow that:
- Remembers your project across sessions
- Plans before coding (so you're not debugging hallucinations)
- Verifies what was built actually works
- Keeps Claude focused on one thing at a time

No magic. Just structure.

---

## Setup (2 minutes)

```bash
# Clone and install
git clone https://github.com/CodeAlexx/Eri-Rpg.git
cd Eri-Rpg
pip install -e .

# Install Claude Code integration
erirpg install

# Check it worked
erirpg install-status
```

That's it. You're ready.

---

## Starting a New Project

### Step 1: Tell Claude what you want

```
/coder:new-project
```

Claude asks questions. Answer them. Be specific or be vague — it'll ask follow-ups until it understands.

What happens:
1. Claude figures out what you're building
2. Breaks it into phases (foundation first, features later)
3. Creates a roadmap you can actually follow

**Creates:** `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`

### Step 2: Discuss the phase (optional but recommended)

```
/coder:discuss-phase 1
```

Before planning, Claude asks you about implementation details. Layout preferences? Error handling style? API conventions? This is where you lock in decisions so Claude doesn't have to guess later.

You pick which areas to discuss. Skip the obvious ones. Dig into the ones that matter.

**Creates:** `.planning/phases/01-xxx/CONTEXT.md`

### Step 3: Plan the phase

```
/coder:plan-phase 1
```

Claude reads your roadmap (and CONTEXT.md if you discussed), researches what's needed, and writes a plan. Not vague ideas — actual tasks with verification criteria.

If it's something complex (auth, external APIs, databases), it spawns a researcher first. You don't have to ask.

**Creates:** `.planning/phases/01-xxx/PLAN.md`

### Step 5: Build it

```
/coder:execute-phase 1
```

Claude follows the plan. Each task gets its own commit. If something needs your input (design decision, API key, visual check), it stops and asks.

When it's done, it verifies the code actually does what the plan said.

**Creates:** Actual code. Plus `.planning/phases/01-xxx/SUMMARY.md`

### Step 6: Repeat

```
/coder:discuss-phase 2  # optional
/coder:plan-phase 2
/coder:execute-phase 2
```

Keep going until your roadmap is done.

---

## Coming Back After a Break

Context gone? No problem.

```
/coder:init
```

Claude reads your project state and picks up where you left off. No re-explaining.

---

## The Core Commands

| Command | What it does |
|---------|--------------|
| `/coder:new-project` | Start fresh. Questions → research → roadmap. |
| `/coder:discuss-phase N` | Lock in decisions before planning. |
| `/coder:plan-phase N` | Plan phase N. Research if needed, then tasks. |
| `/coder:execute-phase N` | Build phase N. Code, commit, verify. |
| `/coder:init` | Recover context after `/clear` or new session. |
| `/coder:status` | Where am I? What's next? |
| `/coder:doctor` | Something broken? This finds and fixes it. |

That's the core loop. Everything else is optional.

---

## Adding to Existing Code

Already have a codebase? Skip `new-project`.

```
/coder:add-feature "user authentication"
```

Claude maps your codebase first (if it hasn't already), then plans the feature to fit your existing patterns. No weird new conventions that clash with what you've got.

---

## When Things Go Wrong

### "Verification found gaps"

The code didn't do what the plan promised. Claude tells you what's missing.

```
/coder:plan-phase N --gaps
/coder:execute-phase N --gaps-only
```

This creates targeted fixes, not a full rewrite.

### "I'm stuck / confused"

```
/coder:doctor
```

Runs 8 health checks. Finds issues. Offers fixes.

### "Context is huge and Claude is slow"

```
/clear
/coder:init
```

Fresh context, but Claude still knows where you are.

---

## How It Actually Works

**STATE.md** tracks where you are. Every command reads it, every command updates it.

**ROADMAP.md** is your plan. Phases with goals. Claude checks things off as they're done.

**PLAN.md** files have the actual tasks. Each task has files to touch, what to do, and how to verify it worked.

**SUMMARY.md** files record what was built. Not what was planned — what actually happened.

Claude doesn't hold all this in context. It reads the files, does the work, writes the results. The files are the memory.

---

## Tips

**Be specific early.** Vague requirements = vague code. If you know you want "JWT auth with refresh tokens", say that. Don't make Claude guess.

**One phase at a time.** Don't try to plan everything upfront. Plan phase 1, build phase 1, then plan phase 2 with what you learned.

**Check the summaries.** After each phase, skim the SUMMARY.md. It's Claude's "here's what I did" — catches drift early.

**Trust the verification.** If it says gaps found, there are gaps. Fix them before moving on or they compound.

---

## That's It

```
/coder:new-project      # start
/coder:discuss-phase 1  # discuss (optional)
/coder:plan-phase 1     # plan
/coder:execute-phase 1  # build
/coder:init             # resume
```

Five commands. The rest is Claude following the plan and you reviewing the output.

Go build something.

---

## All Commands Reference

### Starting & Sessions

| Command | What it does |
|---------|--------------|
| `/coder:new-project` | Start a brand new project from scratch |
| `/coder:init` | Recover context after `/clear` or new session |
| `/coder:status` | Quick check — current phase, progress, next action |
| `/coder:switch-project` | Jump to a different project mid-session |
| `/coder:pause` | Save state when stopping work mid-task |
| `/coder:resume` | Pick up where you paused |

### Planning & Building

| Command | What it does |
|---------|--------------|
| `/coder:discuss-phase N` | Capture decisions before planning a phase |
| `/coder:plan-phase N` | Create executable plans for phase N |
| `/coder:execute-phase N` | Execute all plans in phase N |
| `/coder:verify-work N` | Manual acceptance testing after phase completes |

### Roadmap Management

| Command | What it does |
|---------|--------------|
| `/coder:add-phase` | Append a new phase to the roadmap |
| `/coder:insert-phase` | Insert an urgent phase between existing ones |
| `/coder:remove-phase` | Remove a future phase from the roadmap |
| `/coder:new-milestone` | Start a new version (v2, v3, etc.) |
| `/coder:complete-milestone` | Archive milestone and tag release |

### Working with Existing Code

| Command | What it does |
|---------|--------------|
| `/coder:add-feature` | Add a feature to an existing codebase |
| `/coder:map-codebase` | Analyze codebase structure and patterns |
| `/coder:clone-behavior` | Clone a program by extracting behavior specs |

### Troubleshooting

| Command | What it does |
|---------|--------------|
| `/coder:doctor` | Run health checks, find and fix issues |
| `/coder:debug` | Systematic debugging with triage |
| `/coder:rollback` | Undo execution if something went wrong |

### Quick Tasks

| Command | What it does |
|---------|--------------|
| `/coder:quick "description"` | One-off task with atomic commit |

### Info & History

| Command | What it does |
|---------|--------------|
| `/coder:progress` | Show detailed progress on current phase |
| `/coder:projects` | List all registered projects |
| `/coder:history` | View execution history |
| `/coder:help` | Command reference and examples |
