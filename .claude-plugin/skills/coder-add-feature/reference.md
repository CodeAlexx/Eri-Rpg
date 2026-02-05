# Add-Feature Reference

Detailed documentation for brownfield feature development.

---

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

---

## Step 2: Load Codebase Context

Read existing codebase documentation:
```bash
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

---

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

---

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

---

## Step 5: Context Discussion

If the feature has UI, API, or complex decisions:

Ask: "Want to discuss implementation details before planning? [y/n]"

If yes, run discussion similar to /coder:discuss-phase:
- For UI features: Layout, interactions, states
- For API features: Endpoints, payloads, errors
- For data features: Schema, validation, storage

Write decisions to `.planning/features/{feature-name}/CONTEXT.md`

---

## Step 6: Research Phase

For non-trivial features, spawn eri-phase-researcher:
```
Task(
  description="Research feature implementation",
  prompt="Research how to implement {feature-name}
         Given:
         - Stack: {from STACK.md}
         - Architecture: {from ARCHITECTURE.md}
         - Conventions: {from CONVENTIONS.md}

         Find:
         - Best approach for this stack
         - Existing patterns to reuse
         - Potential gotchas",
  subagent_type="eri-phase-researcher"
)
```

Write to `.planning/features/{feature-name}/RESEARCH.md`

---

## Step 7: Create Implementation Plan

Spawn eri-planner with full context:
```
Task(
  description="Plan feature implementation",
  prompt="Create plan for feature: {feature-name}

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
         - Avoid creating patterns that conflict with existing code",
  subagent_type="eri-planner"
)
```

Output: `.planning/features/{feature-name}/PLAN-01.md` (and more if needed)

---

## Step 8: Plan Verification

Spawn eri-plan-checker:
```
Task(
  description="Verify feature plan",
  prompt="Verify plan covers:
         - All acceptance criteria from SPEC.md
         - Follows conventions from codebase mapping
         - Integration points are valid
         - No architectural violations",
  subagent_type="eri-plan-checker"
)
```

If issues found, revise plan.

---

## Step 9: Execute

Show user:
1. Feature spec summary
2. Implementation plan overview
3. Files that will be created/modified
4. Estimated scope

Ask: "Ready to implement? [y/n]"

If yes: Execute plan using eri-executor agents.

---

## Step 10: Verification

After execution, verify:
- All acceptance criteria met
- Tests pass (if tests exist)
- Follows conventions

Create `.planning/features/{feature-name}/SUMMARY.md`

Commit all changes.

---

## Reference Porting Workflow

When using `--reference <source>/<section>`:

### Prerequisites
1. Source program has behavior spec: `{source}/{section}-BEHAVIOR.md`
2. Target program has blueprint: `{target}/overview.md`

If missing, create them:
```bash
# Create source behavior spec
python3 -m erirpg.commands.blueprint add onetrainer models/sana "Sana model" --extract-tests --json

# Create target conventions
python3 -m erirpg.commands.blueprint add eritrainer overview "Eritrainer architecture" --json
```

### Auto-Analysis

The add-feature command automatically:

1. **Scans target for interface requirements:**
   - Base traits/interfaces all similar components must implement
   - Wrapper types (ResourceHandle, Arc<Mutex<T>>, etc.)
   - Required decorators or annotations
   - Naming conventions for this type of component

2. **Fills "Target Must Adapt To"** in feature spec

3. **Checks ownership compatibility:**
   - Does source ownership model work in target?
   - Are there 'static lifetimes that need explicit cleanup?
   - Any move semantics that conflict with target patterns?

4. **Checks side effect compatibility:**
   - Does source have global mutations target forbids?
   - Is source thread-safe if target requires it?
   - Any file/network operations that need adaptation?

5. **Detects target architecture:**
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

### Verification After Implementation

```bash
python3 -m erirpg.commands.verify_behavior eritrainer/sana --json
```

Verification table example:
| Behavior Spec | Code Check | Status |
|---------------|------------|--------|
| Input: Dataset | fn new(dataset: &Dataset) | ✅ |
| Output: TrainedModel | -> Result<Model> | ✅ |
| State: Idle→Loading→Ready | Found state enum | ✅ |
| No global mutations | No static mut | ✅ |
| Thread safe | Uses Arc<RwLock> | ✅ |
| Resource: <24GB VRAM | No check possible | ⚠️ Manual |

**Resolution:**
- ❌ Violations → Fix code immediately
- ⚠️ Manual → Document verification

### Philosophy

**BAD**: Copy Python → Rust (doesn't work, different idioms)

**GOOD**: Extract behavior → Check compatibility → Implement in target
- Works for any language pair
- Catches ownership issues early
- Follows target conventions
- Native performance
