---
name: coder:clone-behavior
description: Clone a program by extracting behaviors and reimplementing from scratch
argument-hint: "<source-path> <new-project-name> [--language rust] [--framework candle]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to analyze source and generate plan:**
```bash
python3 -m erirpg.commands.clone_behavior <source-path> <new-project-name> [options] --json
```

Options:
- `--language <lang>` - Target language (default: same as source)
- `--framework <framework>` - Target framework
- `--skip-tests` - Don't extract test contracts
- `--dry-run` - Show plan without executing
- `--modules <list>` - Only clone specific modules (comma-separated)
- `--exclude <list>` - Skip specific modules (comma-separated)

Returns JSON with:
- `source_analysis`: Language, framework, path
- `target_analysis`: Target language/framework, cross_language flag
- `modules`: List of modules to clone with file/line counts
- `plan`: Full 5-phase execution plan
- `estimates`: Behavior files, implementation phases, verification checks

---

<command-name>coder:clone-behavior</command-name>

<objective>
Clone an entire program by extracting WHAT it does (behavior), not HOW it's coded.
Then reimplement from scratch - same functionality, completely different code.

This is the ultimate use of everything EriRPG built:
- Blueprint system (scan)
- Behavior extraction (understand)
- Add-feature with reference (implement)
- Behavior verification (validate)

All chained into one fully automatic command.
</objective>

<workflow>
## The 5 Phases

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        /coder:clone-behavior                              │
│                                                                          │
│  SOURCE ──────────────────────────────────────────────────────► TARGET   │
│  ~/onetrainer                                                  eritrainer │
│  Python/PyTorch                                                Rust/Candle│
│                                                                          │
│  Phase 1: SCAN ────────────────────────────────────────────────────────  │
│  │ /coder:map-codebase                                                   │
│  │ /coder:blueprint add ... --extract-behavior --extract-tests           │
│  └──► BEHAVIOR.md for every module                                       │
│                                                                          │
│  Phase 2: PLAN ────────────────────────────────────────────────────────  │
│  │ /coder:new-project <target> --from-behaviors <source>                 │
│  └──► ROADMAP.md with phases matching source modules                     │
│                                                                          │
│  Phase 3: IMPLEMENT ───────────────────────────────────────────────────  │
│  │ For each module:                                                      │
│  │   /coder:plan-phase N                                                 │
│  │   /coder:execute-phase N                                              │
│  │   Uses BEHAVIOR.md as requirements (NOT source code)                  │
│  └──► Working implementation in target language                          │
│                                                                          │
│  Phase 4: VERIFY ──────────────────────────────────────────────────────  │
│  │ For each module:                                                      │
│  │   /coder:verify-behavior <target>/<module>                            │
│  │   Checks: Interface, State Machine, Tests, Resources, Ownership       │
│  └──► Verification report (✅ pass, ❌ fail, ⚠️ manual)                    │
│                                                                          │
│  Phase 5: COMPLETE ────────────────────────────────────────────────────  │
│  │ All behaviors verified                                                │
│  │ /coder:complete-milestone v1.0                                        │
│  └──► Different code, same functionality                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## What Makes This Different

Traditional porting:
```
Source Code ──copy/translate──► Target Code
            (carries implementation baggage)
```

Behavior cloning:
```
Source Code ──extract behavior──► BEHAVIOR.md ──implement──► Target Code
                                 (portable spec)     (native implementation)
```

The target code is written fresh, following target language idioms,
using target frameworks natively. Only the BEHAVIOR is preserved.
</workflow>

<process>

## Phase 1: SCAN - Extract All Behaviors

### Step 1.1: Map Source Codebase
```bash
cd <source-path>
```

Spawn Task agent for codebase mapping:
```
Task(
  description="Map source codebase",
  prompt="Run /coder:map-codebase on this directory. Create .planning/codebase/ with full analysis.",
  subagent_type="eri-codebase-mapper",
  model="sonnet"
)
```

### Step 1.2: Extract Behaviors for Each Module

For each module from CLI result `modules.list`:

```
Task(
  description="Extract behavior: {module}",
  prompt="Run /coder:blueprint add {source_name} {module} '{module} module' --extract-tests
         Then run behavior-extractor agent to fill in the BEHAVIOR.md with:
         - Purpose, Inputs, Outputs
         - Interface Contract
         - Test Contracts (Given/When/Then)
         - Global State Impact
         - Resource Budget
         - Ownership Model
         - State Machine",
  subagent_type="eri-behavior-extractor",
  model="sonnet"
)
```

**Parallel execution:** Spawn up to 4 behavior extraction agents simultaneously.

### Step 1.3: Verify Extraction Completeness

Check all BEHAVIOR.md files were created:
```bash
ls .planning/blueprints/{source_name}/*-BEHAVIOR.md | wc -l
```

Should match `modules.count` from CLI.

---

## Phase 2: PLAN - Create Behavior-Based Roadmap

### Step 2.1: Initialize Target Project

```bash
mkdir -p <target-path>
cd <target-path>
```

### Step 2.2: Create Project with Behavior References

This is a special mode of new-project that uses behaviors instead of research:

1. Copy behaviors to target:
```bash
mkdir -p .planning/blueprints/{target_name}
cp -r <source-path>/.planning/blueprints/{source_name}/*-BEHAVIOR.md .planning/blueprints/{target_name}/
```

2. Create PROJECT.md:
```markdown
# {target_name}

## Vision
Behavior-compatible clone of {source_name}, implemented in {target_language}/{target_framework}.

## Source Reference
- Original: {source_path}
- Language: {source_language} → {target_language}
- Framework: {source_framework} → {target_framework}

## Constraints
- Must pass all behavior verifications
- Must match all test contracts
- Must respect resource budgets
- Implementation must be idiomatic {target_language}

## Key Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
| Clone approach | Behavior extraction | {today} |
| Target language | {target_language} | {today} |
```

3. Create REQUIREMENTS.md from behaviors:

For each BEHAVIOR.md, extract requirements:
```markdown
# Requirements

## Behavior Parity Requirements
| REQ-ID | Module | Requirement | Priority |
|--------|--------|-------------|----------|
| BHV-001 | {module1} | Interface contract matches | Must |
| BHV-002 | {module1} | State machine preserved | Must |
| BHV-003 | {module1} | Test contracts pass | Must |
| BHV-004 | {module1} | Resource budget met | Should |
| BHV-005 | {module1} | Ownership model compatible | Must |
...
```

4. Create ROADMAP.md:

Spawn eri-roadmapper:
```
Task(
  description="Create behavior-based roadmap",
  prompt="Create ROADMAP.md with one phase per source module.
         Each phase goal: 'Implement {module} with behavior parity'
         Requirements: BHV-XXX entries for that module
         Success criteria: /coder:verify-behavior passes",
  subagent_type="eri-roadmapper"
)
```

---

## Phase 3: IMPLEMENT - Build From Behaviors

For each phase (module) in ROADMAP.md:

### Step 3.1: Plan Phase
```
/coder:plan-phase {N}
```

The planner MUST:
- Read the BEHAVIOR.md for this module
- NOT read source code implementation
- Plan implementation in target language idioms
- Include all test contracts as verification criteria

### Step 3.2: Execute Phase
```
/coder:execute-phase {N}
```

The executor MUST:
- Implement based on BEHAVIOR.md requirements
- Use target language/framework patterns
- Create tests matching test contracts
- Document any deviations

### Step 3.3: Phase Verification
```
/coder:verify-work {N}
```

Quick check before behavior verification.

**Implementation principle:** The code should look like it was written by someone who:
- Never saw the source code
- Only had the behavior specification
- Is expert in the target language

---

## Phase 4: VERIFY - Behavior Diff

For each module:

### Step 4.1: Run Behavior Verification
```bash
python3 -m erirpg.commands.verify_behavior {target}/{module} --json
```

### Step 4.2: Check Results

| Check | What It Verifies |
|-------|------------------|
| **Interface** | Input/output types match spec |
| **State Machine** | All states exist, transitions valid |
| **Test Contracts** | Each Given/When/Then has passing test |
| **Global State** | No forbidden mutations |
| **Ownership** | Borrow/move matches spec |
| **Resources** | Within budget (manual check flagged) |

### Step 4.3: Handle Failures

If ❌ violations:
1. Read the specific violation
2. Fix the implementation
3. Re-run verification
4. Do NOT proceed until all ❌ resolved

If ⚠️ manual checks:
1. Document what was manually verified
2. Add to VERIFICATION.md with evidence

### Step 4.4: Track Progress

Update clone-state.json:
```json
{
  "progress": {
    "verify": {
      "status": "in_progress",
      "modules": [
        {"name": "module1", "status": "pass", "checks": 5, "passed": 5},
        {"name": "module2", "status": "fail", "checks": 5, "passed": 3}
      ]
    }
  }
}
```

---

## Phase 5: COMPLETE - Finalize Clone

### Step 5.1: Final Verification Summary

Generate CLONE-VERIFICATION.md:
```markdown
# Clone Verification Report

## Source
- Project: {source_name}
- Language: {source_language}
- Modules: {module_count}

## Target
- Project: {target_name}
- Language: {target_language}
- Framework: {target_framework}

## Verification Results

| Module | Interface | State | Tests | Global | Ownership | Resources |
|--------|-----------|-------|-------|--------|-----------|-----------|
| mod1   | ✅        | ✅    | ✅    | ✅     | ✅        | ⚠️ Manual  |
| mod2   | ✅        | ✅    | ✅    | ✅     | ✅        | ✅        |

## Summary
- Total modules: {N}
- Fully verified: {N}
- Manual checks: {N}
- Failed: 0

## Conclusion
✅ Clone complete with behavior parity.
Different code, same functionality.
```

### Step 5.2: Tag Release
```bash
/coder:complete-milestone v1.0
```

### Step 5.3: Final Commit
```bash
git add .
git commit -m "feat: complete behavior clone of {source_name}

Cloned from: {source_path}
Source language: {source_language}
Target language: {target_language}

Modules cloned: {module_count}
All behavior verifications: PASS

Co-Authored-By: Claude <noreply@anthropic.com>"
```

</process>

<examples>

## Example 1: Python → Rust ML Training

```
/coder:clone-behavior ~/onetrainer eritrainer --language rust --framework candle
```

Source: OneTrainer (Python/PyTorch)
Target: EriTrainer (Rust/Candle)

Modules detected:
- models/flux (2,340 lines)
- models/sana (1,890 lines)
- training/pipeline (3,210 lines)
- data/loader (1,450 lines)

Each gets a BEHAVIOR.md extracted, then reimplemented in Rust.

## Example 2: Partial Clone

```
/coder:clone-behavior ~/comfyui eri-nodes --language rust --modules custom_nodes,execution
```

Only clone specific modules, ignore the rest.

## Example 3: Dry Run First

```
/coder:clone-behavior ~/myapp myapp-v2 --dry-run
```

See the full plan before committing to execution.

## Example 4: Same Language Rewrite

```
/coder:clone-behavior ~/legacy-app modern-app
```

Rewrite Python → Python but with modern patterns, clean architecture.
Behaviors ensure functionality preserved while code is completely new.

</examples>

<agent-instructions>

## Execution Strategy

1. **Call CLI first** to get analysis and plan
2. **Show user the plan** before executing
3. **Execute phases sequentially** (can't implement before scan)
4. **Parallelize within phases** (multiple behavior extractions, multiple implementations)
5. **Track progress** in clone-state.json
6. **Stop on verification failures** - fix before continuing

## Key Principles

- **Never reference source implementation during IMPLEMENT phase**
- **Only use BEHAVIOR.md as requirements**
- **Target code should be idiomatic** for target language
- **All test contracts must have corresponding tests**
- **Resource budgets are guidelines, not strict requirements**

## Model Selection

- **SCAN phase:** sonnet (good at extraction)
- **PLAN phase:** sonnet (good at planning)
- **IMPLEMENT phase:** opus for complex modules, sonnet for simple
- **VERIFY phase:** sonnet (good at comparison)

## Error Recovery

If a phase fails:
1. Check clone-state.json for current position
2. Fix the issue
3. Resume from failed step (not from beginning)

```bash
# Check progress
python3 -m erirpg.commands.clone_behavior progress --json
```

</agent-instructions>

<completion>
## On Completion

### 1. Verify Committed

```bash
git status --short
```

### 2. Update STATE.md

```markdown
## Last Action
Completed clone-behavior: {source_name} → {target_name}
- Modules cloned: {count}
- Behaviors verified: {count}/{count}

## Next Step
Run application and compare with source
```

### 3. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 4. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ CLONE COMPLETE: {source_name} → {target_name}               ║
╠════════════════════════════════════════════════════════════════╣
║  Source: {source_path} ({source_language})                     ║
║  Target: {target_name} ({target_language})                     ║
║  Modules: {count} cloned, {count} verified                     ║
║  Result: Different code, same functionality                    ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Validate the clone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Run tests: {test_command}
2. Run app: {run_command}
3. Compare outputs with source (manual)
4. Type:  /clear
5. Then:  /coder:init
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
</completion>
