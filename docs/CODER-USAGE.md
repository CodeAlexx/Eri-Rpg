# Eri-Coder: Build Apps Without Writing Code

**Describe what you want. Claude builds it.**

Eri-coder is a vibe coding workflow where you describe your app in plain English and Claude handles all the coding, testing, and deployment.

---

## Real Example: We Built This

Using eri-coder, we built a complete **Rust chat application** in one session:

![Working App](https://raw.githubusercontent.com/CodeAlexx/rust-llm-chat-interface/main/docs/screenshot-app.png)

**Result:**
- 995 lines of Rust code
- egui desktop UI
- SQLite database
- Streaming API integration
- 7 unit tests
- Full documentation

**Time:** Single Claude Code session
**Code written by human:** Zero

See the repo: [rust-llm-chat-interface](https://github.com/CodeAlexx/rust-llm-chat-interface)

---

## How It Works (No Coding Required)

### Step 1: Start a New Project

Open Claude Code and type:

```
/coder:new-project my-app "A task management app with due dates"
```

That's it. Claude runs 8 initialization phases automatically.

### Step 2: Answer Questions

Claude will ask you questions like:
- "What problem does this solve?"
- "Who are the users?"
- "What's explicitly out of scope?"

Just answer in plain English. Be specific about what you want.

### Step 3: Choose Your Mode

Claude will ask: **YOLO or Interactive?**

| Mode | What Happens |
|------|--------------|
| **YOLO** | Claude builds everything without stopping for approval |
| **Interactive** | Claude asks for approval at each step |

For your first project, try YOLO - it's faster.

### Step 4: Watch Claude Research

Claude spawns 4 parallel research agents:

![Research Agents](https://raw.githubusercontent.com/CodeAlexx/rust-llm-chat-interface/main/docs/screenshot-agents.png)

These research:
- **Stack** - Best technologies for your app
- **Features** - What features similar apps have
- **Architecture** - How to structure the code
- **Pitfalls** - Common mistakes to avoid

You don't do anything - just watch.

### Step 5: Select Features

Claude presents features in categories:
- **Must Have** - Core functionality
- **Should Have** - Important but not critical
- **Nice to Have** - Future enhancements

Pick what you want for v1. Say something like:
> "All the must-haves, the first two should-haves, skip the nice-to-haves for now"

### Step 6: Approve the Roadmap

Claude creates a phased roadmap. Review it and say:
> "Looks good, proceed"

### Step 7: Let Claude Build

Claude will:
```
/coder:plan-phase 1    # Create detailed plans
/coder:execute-phase 1 # Write all the code
/coder:verify-work 1   # Test everything
```

Repeat for each phase until done.

### Step 8: Run Your App

Claude tells you how to run it:
```bash
cargo run        # For Rust apps
npm start        # For Node apps
python app.py    # For Python apps
```

---

## The 8 Initialization Phases

When you run `/coder:new-project`, Claude executes:

| Phase | What Happens | Your Input |
|-------|--------------|------------|
| 1. Setup | Creates project folder and git repo | None |
| 2. Brownfield | Checks for existing code | None |
| 3. Questioning | Deep Q&A about requirements | Answer questions |
| 4. PROJECT.md | Documents vision and constraints | Review and approve |
| 5. Preferences | Sets workflow mode | Choose YOLO or Interactive |
| 6. Research | 4 parallel agents gather info | Watch and wait |
| 7. Requirements | Generates feature list with IDs | Select v1 features |
| 8. Roadmap | Creates phased plan | Approve or revise |

**Output:** A `.planning/` folder with all documentation:
```
.planning/
├── PROJECT.md        # Vision and constraints
├── REQUIREMENTS.md   # Feature list with REQ-IDs
├── ROADMAP.md        # Phased implementation plan
├── STATE.md          # Progress tracker
├── config.json       # Workflow preferences
├── research/         # Research findings (greenfield)
│   ├── STACK.md
│   ├── FEATURES.md
│   ├── ARCHITECTURE.md
│   └── PITFALLS.md
├── codebase/         # Codebase analysis (brownfield)
│   ├── STACK.md
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md
│   ├── CONCERNS.md
│   └── SUMMARY.md
├── phases/           # Phase execution artifacts
│   └── 01-setup/
│       ├── 01-01-PLAN.md
│       ├── 01-01-SUMMARY.md
│       └── 01-VERIFICATION.md
├── quick/            # Ad-hoc tasks (/coder:quick)
│   └── 001-fix-bug/
├── debug/            # Debug sessions (/coder:debug)
│   ├── active-session.md
│   └── resolved/
└── todos/            # Captured ideas (/coder:add-todo)
    ├── pending/
    └── completed/
```

---

## Commands You'll Use

### Starting Projects

| Command | When to Use | What to Type |
|---------|-------------|--------------|
| New project (greenfield) | Starting from scratch | `/coder:new-project my-app "Description"` |
| Map existing code | Understanding a codebase | `/coder:map-codebase` |
| Add feature (brownfield) | Adding to existing project | `/coder:add-feature auth "User authentication"` |

### Building Phases

| Command | What to Type |
|---------|--------------|
| Discuss a phase | `/coder:discuss-phase 1` |
| See Claude's approach | `/coder:list-phase-assumptions 1` |
| Plan a phase | `/coder:plan-phase 1` |
| Build a phase | `/coder:execute-phase 1` |
| Test a phase | `/coder:verify-work 1` |

### Managing Work

| Command | What to Type |
|---------|--------------|
| Check progress | `/coder:progress` |
| Stop for today | `/coder:pause "stopping for the day"` |
| Continue tomorrow | `/coder:resume` |
| Finish version | `/coder:complete-milestone v1.0` |
| Start next version | `/coder:new-milestone v2.0` |

### Quick Tasks & Debugging

| Command | What to Type |
|---------|--------------|
| Quick fix (outside phases) | `/coder:quick "Fix the login button"` |
| Debug an issue | `/coder:debug "Login fails after reset"` |
| Capture idea for later | `/coder:add-todo "Add dark mode"` |
| Create gap-fix phases | `/coder:plan-milestone-gaps` |

### Configuration

| Command | What to Type |
|---------|--------------|
| View/change settings | `/coder:settings` |
| Get help | `/coder:help` |

---

## Example Conversation

Here's what a real session looks like:

**You:**
```
/coder:new-project llm-chat "A chat interface for local LLMs"
```

**Claude:** *Creates project, asks questions*

**You:**
> "It's for personal use and dev testing. I want streaming responses, conversation history, and it should work offline with my local LLM server."

**Claude:** *Runs research agents, presents features*

**You:**
> "All the must-haves. Use egui for the UI - I've heard it's good. YOLO mode please."

**Claude:** *Creates roadmap with 4 phases*

**You:**
> "Looks good, build it"

**Claude:** *Executes all phases, tests everything*

**You:**
```
cargo run
```

**Result:** Working chat app.

---

## Tips for Best Results

### Be Specific About What You Want

❌ Bad: "Make a chat app"
✅ Good: "Make a chat app that connects to localhost:8000, streams responses token by token, and saves conversations to SQLite"

### Tell Claude Your Constraints

❌ Bad: "Build it however"
✅ Good: "Use Python with FastAPI, no external databases, must work offline"

### Trust YOLO Mode

For most projects, YOLO mode is faster and produces the same quality. Claude knows when to stop and ask (like for major architecture decisions).

### Don't Interrupt During Research

The 4 parallel research agents take 1-2 minutes. Let them finish - they're gathering important context.

### Verify After Each Phase

Even in YOLO mode, run `/coder:verify-work` after each phase. Catching issues early is easier than fixing them later.

---

## What Claude Creates

After `/coder:new-project`, your folder looks like:

```
my-app/
├── .planning/           # All documentation
│   ├── PROJECT.md       # Vision
│   ├── REQUIREMENTS.md  # Features with IDs
│   ├── ROADMAP.md       # Phases
│   └── research/        # Research docs
├── src/                 # Source code
├── tests/               # Test files
├── Cargo.toml           # Or package.json, pyproject.toml, etc.
└── README.md            # Documentation
```

Everything is tracked in git automatically.

---

## When Things Go Wrong

### Claude Stops and Asks

If Claude encounters a major decision (new database table, switching libraries), it stops and asks. This is intentional - these decisions need your input.

Just tell Claude what you prefer:
> "Use SQLite, not PostgreSQL"

### Tests Fail

Claude will debug and fix. If it can't figure it out, it'll ask you for more context.

### You Change Your Mind

Mid-project changes are fine:
> "Actually, let's add dark mode support to the requirements"

Claude will update the roadmap and continue.

---

## Working with Existing Codebases (Brownfield)

Most real projects aren't greenfield - you're adding to existing code. Eri-coder handles this.

### Map First, Then Modify

Before adding features to an existing project:

```
cd ~/my-existing-project
/coder:map-codebase
```

This creates `.planning/codebase/` with:
- **STACK.md** - Languages, frameworks, dependencies
- **ARCHITECTURE.md** - How the code is organized
- **CONVENTIONS.md** - Coding style to follow
- **CONCERNS.md** - Tech debt and issues
- **SUMMARY.md** - Quick overview

### Add Features

Once mapped, add features that fit the existing architecture:

```
/coder:add-feature payments "Stripe payment processing"
```

Claude will:
1. Read your codebase mapping
2. Plan the feature to match existing patterns
3. Integrate at the right places
4. Follow your conventions

### When to Use What

| Scenario | Command |
|----------|---------|
| Brand new project | `/coder:new-project` |
| Add feature to existing code | `/coder:add-feature` |
| Just understand a codebase | `/coder:map-codebase` |
| Major restructuring | `/coder:new-project` (will detect brownfield) |

### Example: Adding Auth to Existing App

```
# Step 1: Map what's there
cd ~/my-app
/coder:map-codebase

# Step 2: Add the feature
/coder:add-feature auth "User authentication with email/password"

# Claude will:
# - Check ARCHITECTURE.md for where auth should go
# - Follow patterns from CONVENTIONS.md
# - Use the right framework patterns from STACK.md
# - Avoid issues listed in CONCERNS.md
```

---

## Advanced: Adding Phases Later

### Add a Phase
```
/coder:add-phase "API-Integration" "Connect to payment processor"
```

### Insert Urgent Phase
```
/coder:insert-phase 2 "Hotfix" "Fix security issue"
```

### Remove Future Phase
```
/coder:remove-phase 5
```

---

## Moving to Maintenance Mode

Once your app is built and stable, switch to EriRPG tracking mode:

```
/eri:index .           # Index the codebase
/eri:start             # Start a session
/eri:recall auth       # Recall what Claude learned
```

Now use `/eri:*` commands for bug fixes and small changes.

---

## FAQ

**Q: Do I need to know how to code?**
A: No. You describe what you want, Claude writes all the code.

**Q: Can I see what Claude is writing?**
A: Yes, everything is visible in real-time. You can stop and ask questions anytime.

**Q: What languages does this support?**
A: Any language Claude knows - Python, JavaScript, Rust, Go, etc.

**Q: How long does it take?**
A: Small apps (few hundred lines): 15-30 minutes. Medium apps (1000+ lines): 1-2 hours.

**Q: What if I want to modify the code later?**
A: The code is yours. Edit it directly or ask Claude to make changes.

**Q: Does this cost money?**
A: Claude Code has usage costs. Or use a local LLM for free (see Local Model Support below).

---

## Local Model Support (Free)

Use a local LLM instead of Claude API:

1. Start a local server:
```bash
llama-server -m model.gguf --port 8000
```

2. Launch Claude Code with local backend:
```bash
ANTHROPIC_BASE_URL=http://localhost:8000 claude
```

Now all generation is free and offline.

---

## Complete Command Reference

### Core Workflow
| Command | Purpose |
|---------|---------|
| `/coder:new-project` | Initialize new project (8-phase setup) |
| `/coder:discuss-phase N` | Capture implementation decisions |
| `/coder:plan-phase N` | Create executable plans |
| `/coder:execute-phase N` | Execute plans in parallel waves |
| `/coder:verify-work N` | Manual acceptance testing |
| `/coder:complete-milestone` | Archive and tag release |
| `/coder:new-milestone` | Start next version |

### Phase Management
| Command | Purpose |
|---------|---------|
| `/coder:add-phase` | Append phase to roadmap |
| `/coder:insert-phase N` | Insert urgent work |
| `/coder:remove-phase N` | Remove future phase |
| `/coder:list-phase-assumptions N` | See Claude's approach |
| `/coder:plan-milestone-gaps` | Create phases for failures |

### Navigation & Status
| Command | Purpose |
|---------|---------|
| `/coder:progress` | Current position and metrics |
| `/coder:help` | Command reference |
| `/coder:settings` | Configure preferences |

### Utilities
| Command | Purpose |
|---------|---------|
| `/coder:quick "task"` | Ad-hoc task with guarantees |
| `/coder:debug "issue"` | Systematic debugging |
| `/coder:add-todo "idea"` | Capture for later |
| `/coder:pause "reason"` | Create handoff state |
| `/coder:resume` | Restore from pause |
| `/coder:map-codebase` | Analyze existing code |
| `/coder:add-feature "name"` | Add to existing project |

---

## Summary

1. `/coder:new-project my-app "description"` - Start
2. Answer questions about what you want
3. Choose YOLO mode for automatic building
4. Watch Claude research, plan, and build
5. `/coder:verify-work` after each phase
6. Run your app

**That's it.** No coding required.
