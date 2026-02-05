# Clone-Behavior Reference

Detailed documentation for the 5-phase clone workflow.

---

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

---

## Phase 1: SCAN

### Step 1.1: Map Source Codebase

```bash
cd <source-path>
```

Spawn codebase mapper:
```
Task(
  description="Map source codebase",
  prompt="Run /coder:map-codebase on this directory. Create .planning/codebase/ with full analysis.",
  subagent_type="eri-codebase-mapper",
  model="sonnet"
)
```

### Step 1.2: Extract Behaviors

For each module from CLI `modules.list`:

```
Task(
  description="Extract behavior: {module}",
  prompt="Run /coder:blueprint add {source_name} {module} '{module} module' --extract-tests
         Then run behavior-extractor agent to fill BEHAVIOR.md with:
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

**Parallel:** Spawn up to 4 agents simultaneously.

### Step 1.3: Verify Completeness

```bash
ls .planning/blueprints/{source_name}/*-BEHAVIOR.md | wc -l
```

Should match `modules.count` from CLI.

---

## Phase 2: PLAN

### Step 2.1: Initialize Target

```bash
mkdir -p <target-path>
cd <target-path>
```

### Step 2.2: Copy Behaviors

```bash
mkdir -p .planning/blueprints/{target_name}
cp -r <source-path>/.planning/blueprints/{source_name}/*-BEHAVIOR.md .planning/blueprints/{target_name}/
```

### Step 2.3: Create PROJECT.md

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

### Step 2.4: Create REQUIREMENTS.md

Extract from each BEHAVIOR.md:

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
```

### Step 2.5: Create ROADMAP.md

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

## Phase 3: IMPLEMENT

For each phase in ROADMAP.md:

### Step 3.1: Plan Phase

```
/coder:plan-phase {N}
```

The planner MUST:
- Read BEHAVIOR.md for this module
- NOT read source code implementation
- Plan in target language idioms
- Include test contracts as verification criteria

### Step 3.2: Execute Phase

```
/coder:execute-phase {N}
```

The executor MUST:
- Implement from BEHAVIOR.md requirements
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

## Phase 4: VERIFY

### Step 4.1: Run Verification

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

**If ❌ violations:**
1. Read the specific violation
2. Fix the implementation
3. Re-run verification
4. Do NOT proceed until resolved

**If ⚠️ manual checks:**
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

## Phase 5: COMPLETE

### Step 5.1: Verification Summary

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

```
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

---

## Examples

### Python → Rust ML Training
```
/coder:clone-behavior ~/onetrainer eritrainer --language rust --framework candle
```

### Partial Clone
```
/coder:clone-behavior ~/comfyui eri-nodes --language rust --modules custom_nodes,execution
```

### Dry Run First
```
/coder:clone-behavior ~/myapp myapp-v2 --dry-run
```

### Same Language Rewrite
```
/coder:clone-behavior ~/legacy-app modern-app
```
Rewrite with modern patterns, clean architecture. Behaviors ensure functionality preserved.

---

## Key Principles

- **Never reference source implementation during IMPLEMENT phase**
- **Only use BEHAVIOR.md as requirements**
- **Target code should be idiomatic** for target language
- **All test contracts must have corresponding tests**
- **Resource budgets are guidelines, not strict requirements**
