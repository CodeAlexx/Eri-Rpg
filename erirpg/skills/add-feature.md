---
name: coder:add-feature
description: Add a feature to an existing codebase (brownfield workflow)
argument-hint: "<feature-name> [description]"
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

**Standard mode - add feature to existing codebase:**
```bash
python3 -m erirpg.commands.add_feature "<feature-description>" --json
```

**Reference mode - port feature from another program:**
```bash
python3 -m erirpg.commands.add_feature <target-program> <feature-name> "<description>" --reference <source>/<section> --json
```

### Standard Mode
For adding new features to a codebase.

### Reference Mode (Feature Porting)
For implementing functionality that exists in another program.

Example:
```bash
python3 -m erirpg.commands.add_feature eritrainer sana "Sana model training" --reference onetrainer/models/sana --json
```

This will:
1. Load `onetrainer/models/sana-BEHAVIOR.md` (what sana does)
2. Load `eritrainer/overview.md` (target conventions)
3. Create feature spec that references both
4. Plan implementation in eritrainer's style

The key insight: **behavior specs are portable**, implementation details are not.

---

<command-name>coder:add-feature</command-name>

<objective>
Add a new feature to an EXISTING codebase using eri-coder workflow.
Designed for brownfield development - modifying projects that already have code.

This is the "mod the codebase with new stuff" workflow.

Differences from /coder:new-project:
- Skips project initialization (already exists)
- Requires codebase mapping first (or does it automatically)
- Plans feature to fit existing architecture
- Follows existing conventions and patterns
</objective>

<context>
Feature name: $ARGUMENTS (first word)
Description: $ARGUMENTS (rest of line)

Prerequisites:
- Must be in an existing project directory
- Codebase should be mapped (will auto-run /coder:map-codebase if not)

Output:
- .planning/features/{feature-name}/
  - SPEC.md - Feature specification
  - CONTEXT.md - Discussion decisions
  - PLAN-*.md - Implementation plans
  - SUMMARY.md - Completion summary
</context>

<process>

## Step 1: Validate Environment

```bash
# Check we're in a project
if [ ! -f "package.json" ] && [ ! -f "Cargo.toml" ] && [ ! -f "pyproject.toml" ] && [ ! -f "go.mod" ]; then
  echo "ERROR: Not in a project root. cd to your project first."
  exit 1
fi

# Check for existing codebase mapping
if [ ! -d ".planning/codebase" ]; then
  echo "NEEDS_MAPPING"
fi
```

If NEEDS_MAPPING, ask user:
> "No codebase mapping found. Run /coder:map-codebase first? [y/n]"

If yes, execute `/coder:map-codebase all` first, then continue.

## Step 2: Load Codebase Context

Read existing codebase documentation:
```bash
# Load codebase context
cat .planning/codebase/STACK.md
cat .planning/codebase/ARCHITECTURE.md
cat .planning/codebase/CONVENTIONS.md
cat .planning/codebase/SUMMARY.md
```

Extract key information:
- What language/framework
- What patterns are used
- Where to integrate new code
- What conventions to follow

## Step 3: Feature Discussion

Create feature directory:
```bash
mkdir -p .planning/features/{feature-name}
```

Use AskUserQuestion for clarification:

1. "What problem does {feature-name} solve?"
2. "What user actions trigger this feature?"
3. "What existing parts of the codebase does this touch?"
4. "Any specific technical approach you want?"
5. "What's out of scope for this feature?"

## Step 4: Write Feature Spec

Create `.planning/features/{feature-name}/SPEC.md`:

```markdown
# Feature: {feature-name}

## Problem Statement
{what problem this solves}

## User Stories
- As a {user}, I want to {action} so that {benefit}

## Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}

## Technical Approach
Based on codebase analysis:
- **Integration Point:** `{path}` - {how to integrate}
- **Pattern to Follow:** {pattern from CONVENTIONS.md}
- **Files to Create/Modify:**
  - `{path}` - {what}

## Out of Scope
- {excluded functionality}

## Dependencies
- Requires: {existing modules}
- Blocked by: {none or blockers}
```

## Step 5: Context Discussion (Optional)

If the feature has UI, API, or complex decisions:

Ask: "Want to discuss implementation details before planning? [y/n]"

If yes, run discussion similar to /coder:discuss-phase:
- For UI features: Layout, interactions, states
- For API features: Endpoints, payloads, errors
- For data features: Schema, validation, storage

Write decisions to `.planning/features/{feature-name}/CONTEXT.md`

## Step 6: Research Phase (if needed)

For non-trivial features, spawn eri-phase-researcher:
```
Research how to implement {feature-name}
Given:
- Stack: {from STACK.md}
- Architecture: {from ARCHITECTURE.md}
- Conventions: {from CONVENTIONS.md}

Find:
- Best approach for this stack
- Existing patterns to reuse
- Potential gotchas
```

Write to `.planning/features/{feature-name}/RESEARCH.md`

## Step 7: Create Implementation Plan

Spawn eri-planner with full context:
```
Create plan for feature: {feature-name}

Feature Context:
- Spec: @.planning/features/{feature-name}/SPEC.md
- Context: @.planning/features/{feature-name}/CONTEXT.md (if exists)
- Research: @.planning/features/{feature-name}/RESEARCH.md (if exists)

Codebase Context (MUST READ):
- @.planning/codebase/SUMMARY.md - Quick reference
- @.planning/codebase/STACK.md - Tech stack to match
- @.planning/codebase/ARCHITECTURE.md - Where to integrate
- @.planning/codebase/CONVENTIONS.md - Patterns to follow
- @.planning/codebase/CONCERNS.md - Issues to avoid

Requirements:
- Follow existing patterns from CONVENTIONS.md
- Integrate at points identified in ARCHITECTURE.md
- Use existing utilities where applicable
- Avoid creating patterns that conflict with existing code
```

Output: `.planning/features/{feature-name}/PLAN-01.md` (and more if needed)

## Step 8: Plan Verification

Spawn eri-plan-checker:
```
Verify plan covers:
- All acceptance criteria from SPEC.md
- Follows conventions from codebase mapping
- Integration points are valid
- No architectural violations
```

If issues found, revise plan.

## Step 9: Ready for Execution

Show user:
1. Feature spec summary
2. Implementation plan overview
3. Files that will be created/modified
4. Estimated scope

Ask: "Ready to implement? [y/n]"

If yes: Execute plan using eri-executor agents

## Step 10: Verification

After execution, verify:
- All acceptance criteria met
- Tests pass (if tests exist)
- Follows conventions

Create `.planning/features/{feature-name}/SUMMARY.md`

Commit all changes.

</process>

<agent-instructions>
This command orchestrates brownfield feature development.

Key principles:
1. ALWAYS respect existing codebase patterns
2. NEVER create new patterns when existing ones work
3. Read CONVENTIONS.md before writing ANY code
4. Integrate at the RIGHT place (check ARCHITECTURE.md)
5. Update existing tests if modifying tested code

Model selection:
- eri-codebase-mapper: sonnet (if auto-mapping needed)
- eri-phase-researcher: sonnet
- eri-planner: sonnet or opus (based on config)
- eri-executor: sonnet
- eri-verifier: sonnet or haiku
</agent-instructions>

<completion>
Show:
1. Feature implementation summary
2. Files created/modified
3. Tests added/updated
4. Any concerns or follow-up needed

Next steps:
- "Run tests: `{test command from STACK.md}`"
- "To add another feature: `/coder:add-feature <name>`"
- "To commit: `git commit -m 'feat: add {feature-name}'`"
</completion>

<integration>
This command uses:
- /coder:map-codebase - Auto-runs if codebase not mapped
- .planning/codebase/* - Reads codebase context
- .planning/blueprints/* - Reads behavior specs (when using --reference)
- eri-planner - Creates implementation plans
- eri-executor - Executes plans
- eri-verifier - Verifies completion

This command is preferred over /coder:new-project when:
- Adding features to existing projects
- Project already has code and structure
- You want to match existing patterns
</integration>

## Reference Porting Workflow

When using `--reference <source>/<section>`:

### Prerequisites
1. Source program has a behavior spec: `{source}/{section}-BEHAVIOR.md`
2. Target program has a blueprint: `{target}/overview.md`

If missing, create them:
```bash
# Create source behavior spec with full extraction
python3 -m erirpg.commands.blueprint add onetrainer models/sana "Sana model" --extract-tests --json
# Then run behavior extractor agent to fill it in

# Create target conventions
python3 -m erirpg.commands.blueprint add eritrainer overview "Eritrainer architecture" --json
# Then run codebase mapper agent to fill it in
```

### Before Implementation

The add-feature command automatically:

1. **Scans target for interface requirements**:
   - Base traits/interfaces all similar components must implement
   - Wrapper types (ResourceHandle, Arc<Mutex<T>>, etc.)
   - Required decorators or annotations
   - Naming conventions for this type of component

2. **Fills "Target Must Adapt To"** in feature spec:
   ```markdown
   ### Target Must Adapt To
   - **Base traits:** ModelTrait, Forward
   - **Input wrapper:** Tensor<f32>
   - **Output wrapper:** Result<Tensor<f32>, ModelError>
   - **Decorators:** #[derive(Debug, Clone)]
   ```

3. **Checks ownership compatibility**:
   - Does source ownership model work in target?
   - Are there 'static lifetimes that need explicit cleanup?
   - Any move semantics that conflict with target patterns?

4. **Checks side effect compatibility**:
   - Does source have global mutations target forbids?
   - Is source thread-safe if target requires it?
   - Any file/network operations that need adaptation?

5. **Detects target architecture**:
   - Hexagonal, layered, MVC, clean, modular
   - Maps behavior to domain layer first
   - Creates adapters for framework-specific code

### What Gets Analyzed

**Source Behavior** (`-BEHAVIOR.md`):
- Interface Contract (signatures, types, errors)
- Global State Impact (env, files, threads, network)
- Ownership Model (borrow, move, clone, lifetimes)
- Resource Budget (memory, time, constraints)
- State Machine (states, transitions, actions)
- Test Contracts (Given/When/Then assertions)

**Target Conventions** (`overview.md`):
- Architecture pattern and layer structure
- Interface requirements (traits, wrappers)
- Error handling patterns
- Memory model constraints
- Threading/async model

### After Implementation

1. **Run behavior verification**:
   ```bash
   python3 -m erirpg.commands.verify_behavior eritrainer/sana --json
   ```

2. **Check verification table**:
   | Behavior Spec | Code Check | Status |
   |---------------|------------|--------|
   | Input: Dataset | fn new(dataset: &Dataset) | ✅ |
   | Output: TrainedModel | -> Result<Model> | ✅ |
   | State: Idle→Loading→Ready | Found state enum | ✅ |
   | No global mutations | No static mut | ✅ |
   | Thread safe | Uses Arc<RwLock> | ✅ |
   | Ownership: dataset borrowed | &Dataset (not owned) | ✅ |
   | Test: empty dataset raises | #[test] test_empty | ✅ |
   | Resource: <24GB VRAM | No check possible | ⚠️ Manual |

3. **Resolve before marking done**:
   - ❌ Violations → Fix code immediately
   - ⚠️ Manual → Document verification

### Feature Spec Created

The feature spec now includes:
- **Interface Contract**: Source signatures + target adaptations
- **Global State Impact**: Side effects and compatibility check
- **Ownership Model**: Data ownership + Rust translation hints
- **Resource Budget**: Memory, time, constraints
- **Compatibility Issues**: ❌ blockers and ⚠️ warnings
- **Verification Checklist**: All spec items to verify

### The Philosophy

**BAD**: Copy Python → Rust
- Doesn't work
- Different idioms
- Different error handling
- Different patterns

**GOOD**: Extract behavior → Check compatibility → Implement in target
- Works for any language pair
- Catches ownership issues early
- Catches side effect violations
- Follows target conventions
- Native performance
- Maintainable code

### Example Workflow

1. **Extract behavior from source**:
   ```bash
   python3 -m erirpg.commands.blueprint add onetrainer models/sana "Sana" --extract-tests --json
   # Run behavior extractor agent
   ```

2. **Create target conventions**:
   ```bash
   python3 -m erirpg.commands.blueprint add eritrainer overview "Eritrainer" --json
   # Run codebase mapper agent
   ```

3. **Add feature with reference**:
   ```bash
   python3 -m erirpg.commands.add_feature eritrainer sana "Sana model" --reference onetrainer/models/sana --json
   ```
   - Auto-scans target interfaces
   - Auto-checks compatibility
   - Creates feature spec with all sections

4. **Review compatibility**:
   - Check for ❌ ownership issues
   - Check for ❌ side effect violations
   - Check for ⚠️ warnings to address

5. **Implement in target's style**:
   - Use behavior spec to know WHAT to build
   - Use target conventions to know HOW to build it
   - Map to domain layer first, adapters second

6. **Verify implementation**:
   ```bash
   python3 -m erirpg.commands.verify_behavior eritrainer/sana --json
   ```
   - All ❌ must be resolved
   - All ⚠️ must be manually verified
