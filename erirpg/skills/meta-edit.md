# /coder:meta-edit - Safe Self-Modification

Safe modification of coder commands. No more breaking files with ad hoc edits.

**This command follows EMPOWERMENT.md:**
- Challenge before implementing
- Require intent
- Flag what could break
- Show your work at every phase

## CLI Integration

```bash
# Check status of any command
python3 -m erirpg.commands.meta_edit status <command> --json

# Phase 1: Analyze (ALWAYS start here)
python3 -m erirpg.commands.meta_edit analyze <command> --json

# Phase 2: Plan (requires --intent)
python3 -m erirpg.commands.meta_edit plan <command> --intent "<what to change>" --json

# Phase 3: Execute (after user approval)
python3 -m erirpg.commands.meta_edit execute <command> --json

# Phase 4: Verify (required after edit)
python3 -m erirpg.commands.meta_edit verify <command> --json

# Emergency rollback
python3 -m erirpg.commands.meta_edit rollback <command> --json
```

---

## Usage

```
/coder:meta-edit <command>              # Start modification workflow
/coder:meta-edit status <command>       # Check current state
/coder:meta-edit rollback <command>     # Emergency restore
```

## The Workflow

### Phase 1: ANALYZE (before any changes)

**MANDATORY FIRST STEP.** Do not skip.

```bash
python3 -m erirpg.commands.meta_edit analyze <command> --json
```

This will:
- Read the target command file completely
- Document what it does NOW (not what you think it does)
- List all dependencies (what calls this, what this calls)
- Create snapshot: `<file>.snapshot.<timestamp>`
- Output: `~/.claude/.coder/meta-edit/<command>/ANALYSIS.md`

**After running**, read the ANALYSIS.md and understand:
- What the command currently does
- What depends on it
- Where the snapshot is

### Phase 2: PLAN (requires user approval)

```bash
python3 -m erirpg.commands.meta_edit plan <command> --intent "<what user wants>" --json
```

This will:
- State the change intent
- List what could break
- Define verification steps
- Output: `~/.claude/.coder/meta-edit/<command>/PLAN.md`

**CRITICAL: After running plan, you MUST:**
1. Read the current file
2. Show user EXACT proposed changes (diff format)
3. List risks from PLAN.md
4. **WAIT FOR EXPLICIT USER APPROVAL**

Do NOT proceed to execute without approval.

### Phase 3: EXECUTE (only after approval)

```bash
python3 -m erirpg.commands.meta_edit execute <command> --json
```

This marks that execution is approved. The CLI returns:
- `file_to_edit`: The file you may now edit
- `snapshot`: Where to rollback if needed
- `instructions`: What to do next

**After running execute:**
1. Make the approved edits to the file
2. Do NOT delete the snapshot
3. Immediately run verify

### Phase 4: VERIFY (required, not optional)

```bash
python3 -m erirpg.commands.meta_edit verify <command> --json
```

This will:
- Check file is valid markdown
- Check code blocks are balanced
- Check file has expected structure
- **AUTO-ROLLBACK if any check fails**
- Output: `~/.claude/.coder/meta-edit/<command>/VERIFY.md`

If verification passes:
- Tell user changes are safe
- Keep snapshot until user confirms

If verification fails:
- File is automatically restored from snapshot
- Report what failed

## Storage Location

```
~/.claude/.coder/meta-edit/<command-name>/
├── ANALYSIS.md              # What the command does
├── PLAN.md                  # Proposed changes
├── VERIFY.md                # Verification results
└── <file>.snapshot.<ts>     # Backup (NEVER auto-delete)
```

## Rules for Claude

1. **NEVER edit `~/.claude/commands/coder/*` without going through this workflow**
2. **NEVER delete snapshots until user explicitly confirms working**
3. **If you don't know what a command does, ANALYZE it first**
4. **Show your work at every phase**
5. **Wait for approval after plan phase - do not auto-proceed**

## Example Session

User: "Add session recovery to /coder:init"

Claude:
```bash
# Step 1: Analyze
python3 -m erirpg.commands.meta_edit analyze init --json
```

[Read ANALYSIS.md, understand current state]

```bash
# Step 2: Plan
python3 -m erirpg.commands.meta_edit plan init --intent "Add session recovery that detects active project from erirpg global state" --json
```

[Read current file, show proposed diff to user]

"Here's what I plan to change:
- Add new section for session recovery
- Call erirpg session-detect CLI first
- Risks: None detected, no commands depend on init

Approve these changes? [y/n]"

[Wait for user approval]

User: "y"

```bash
# Step 3: Execute
python3 -m erirpg.commands.meta_edit execute init --json
```

[Make the actual edits]

```bash
# Step 4: Verify
python3 -m erirpg.commands.meta_edit verify init --json
```

"✅ Verification passed. Changes are safe."

## Emergency Rollback

If something goes wrong at any point:

```bash
python3 -m erirpg.commands.meta_edit rollback <command> --json
```

This restores from the latest snapshot.

## Why This Exists

Because Claude broke `/coder:resume` with an ad hoc edit that replaced a working 235-line file with a broken 49-line version. This workflow prevents that by:

1. **Analyzing before touching** - Understand what exists
2. **Creating snapshots** - Always have a restore point
3. **Requiring approval** - User sees changes before they happen
4. **Verifying after** - Catch problems immediately
5. **Auto-rollback** - If verification fails, restore automatically

No more "let me just quickly fix this" disasters.
