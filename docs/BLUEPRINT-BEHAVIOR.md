# Blueprint & Behavior System

Complete reference for documenting programs and porting features across languages.

## Overview

The Blueprint & Behavior system solves a critical problem: **How do you port features between codebases with different languages, patterns, and conventions?**

The answer: Extract **WHAT** a feature does (behavior), not **HOW** it's coded. Then implement the behavior in the target's native style.

```
┌─────────────────┐                    ┌─────────────────┐
│  Source Code    │                    │  Target Code    │
│  (Python/PyTorch)│                   │  (Rust/Candle)  │
└────────┬────────┘                    └────────▲────────┘
         │                                      │
         │ extract behavior                     │ implement behavior
         ▼                                      │
    ┌─────────────────────────────────────────────┐
    │           BEHAVIOR.md (Portable)            │
    │  - Interface Contract                       │
    │  - Global State Impact                      │
    │  - Ownership Model                          │
    │  - Resource Budget                          │
    │  - State Machine                            │
    │  - Test Contracts                           │
    └─────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Document Source Feature

```
/coder:blueprint add onetrainer models/sana "Sana model training" --extract-tests
```

Claude will:
- Create `.planning/blueprints/onetrainer/models/sana.md` - Implementation blueprint
- Create `.planning/blueprints/onetrainer/models/sana-BEHAVIOR.md` - Portable behavior spec
- Analyze the source code and fill in the behavior spec

### 2. Port Feature to Target

```
/coder:add-feature eritrainer sana "Sana model training" --reference onetrainer/models/sana
```

Claude will:
- Load the source behavior spec
- Scan target for interface requirements
- Check ownership and side effect compatibility
- Create feature spec with implementation plan
- Flag any ❌ blockers or ⚠️ warnings

### 3. Implement and Verify

After implementation:
```
/coder:verify-behavior eritrainer/sana
```

Claude will:
- Check code against behavior spec
- Generate verification table
- Flag any violations that must be fixed

---

## Commands Reference

### /coder:blueprint

Manage section-level blueprints of complex programs.

#### Usage

| Command | What You Type |
|---------|---------------|
| List all blueprints | `/coder:blueprint list` |
| Create new blueprint | `/coder:blueprint add onetrainer models/sana "Sana model"` |
| Load blueprint | `/coder:blueprint load onetrainer/models/sana` |
| Check status | `/coder:blueprint status onetrainer` |
| Update blueprint | `/coder:blueprint update onetrainer/models/sana` |
| View dependencies | `/coder:blueprint deps onetrainer` |

#### Flags

| Flag | What It Does |
|------|--------------|
| `--path <path>` | Point to source code location |
| `--depends <sections>` | Mark dependencies (comma-separated) |
| `--extract-behavior` | Create -BEHAVIOR.md file |
| `--extract-tests` | Also extract test contracts |
| `--behavior` | Load only the behavior spec |
| `--status <status>` | Set: complete, in_progress, not_started, outdated |

#### Examples

```
# Create program overview
/coder:blueprint add onetrainer overview "High-level architecture"

# Create section with dependencies
/coder:blueprint add onetrainer training-pipeline "Core training loop" --depends overview

# Create section with full behavior extraction
/coder:blueprint add onetrainer models/flux "Flux model" --extract-tests

# Load behavior only (for porting)
/coder:blueprint load onetrainer/models/flux --behavior

# Check what's documented
/coder:blueprint status onetrainer

# View dependency graph
/coder:blueprint deps onetrainer
```

---

### /coder:add-feature

Add a feature to an existing codebase.

#### Standard Mode - Add New Feature

```
/coder:add-feature "Add user authentication"
```

Claude will run the full feature workflow: discussion → spec → research → plan → implement → verify.

#### Reference Mode - Port from Another Program

```
/coder:add-feature eritrainer sana "Sana model training" --reference onetrainer/models/sana
```

Claude will:
1. **Load source behavior spec** (what it does)
2. **Load target conventions** (how target works)
3. **Scan target for interface requirements**:
   - Base traits/interfaces
   - Wrapper types (Arc, Result, etc.)
   - Required decorators
   - Naming conventions
4. **Check compatibility**:
   - Ownership model compatibility
   - Side effect compatibility
5. **Create feature spec** with:
   - Interface Contract
   - Global State Impact
   - Ownership Model
   - Resource Budget
   - Compatibility issues (❌/⚠️)
   - Implementation plan

---

### /coder:verify-behavior

Verify implementation matches behavior spec.

#### Usage

```
/coder:verify-behavior eritrainer/sana
```

#### What Gets Checked

| Category | What's Verified |
|----------|-----------------|
| **Inputs** | Parameter types match spec |
| **Outputs** | Return types match spec |
| **Interface** | Base traits implemented |
| **State Machine** | All states exist, transitions valid |
| **Test Contracts** | Each Given/When/Then has test |
| **Global State** | No forbidden mutations |
| **Ownership** | Borrow/move matches spec |
| **Resources** | (Manual verification flagged) |

#### Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ | Pass - code matches spec | None |
| ❌ | Fail - violation found | Must fix |
| ⚠️ | Manual - cannot auto-check | You verify |
| ⏳ | Pending - not yet analyzed | Wait |

#### Blocking Behavior

If Claude says "blocking: true":
- There are ❌ violations
- Do NOT mark feature complete
- Fix violations first, re-run verify

---

## BEHAVIOR.md Format

The complete portable behavior specification format with 12 sections.

### Header

```yaml
---
program: onetrainer
section: models/sana
type: behavior-spec
portable: true
has_tests: true
created: 2026-01-31
updated: 2026-01-31
---
```

### The 12 Sections

#### 1. Purpose
What this feature accomplishes (user perspective, one paragraph).

#### 2. Inputs
Required inputs, optional inputs, configuration options with types and constraints.

#### 3. Outputs
Primary output, side effects, artifacts produced.

#### 4. Behavior
Step-by-step what happens from user's perspective (not code flow).

#### 5. Test Contracts
Given/When/Then extracted from source tests:

| Given | When | Then |
|-------|------|------|
| Empty dataset | train() called | Raises EmptyDataError |
| Valid config | training completes | Output exists, loss decreased |

#### 6. Interface Contract
Source signatures + target adaptations:

```markdown
### Source Signatures
- Input type: torch.Tensor (image), str (caption)
- Output type: torch.Tensor (loss)
- Error handling: raises Exception with message

### Target Must Adapt To
- Base trait: ModelTrait
- Input wrapper: Tensor<f32>
- Output wrapper: Result<Tensor<f32>, ModelError>
```

#### 7. Dependencies
Hard dependencies, soft dependencies, environment requirements.

#### 8. Global State Impact

```markdown
### Environment Variables
- Reads: CUDA_VISIBLE_DEVICES, HF_HOME
- Writes: None

### File System
- Creates: output_dir/*, checkpoints/*
- Locks: model file during loading

### Thread Safety
- NOT thread-safe - single training instance only
```

#### 9. Resource Budget

| Resource | Requirement |
|----------|-------------|
| Peak VRAM | 22GB for batch_size=1 |
| System RAM | 32GB recommended |
| Init time | <30s (model loading) |
| Per step | ~500ms on RTX 4090 |

#### 10. Ownership Model

| Data | Ownership | Lifetime | Notes |
|------|-----------|----------|-------|
| dataset | Borrow | Session | Read-only iteration |
| config | Move | Consumed | Merged into state |
| model_weights | Owned | 'static | Explicit unload() |

**Rust Translation Hints:**
- dataset: `&Dataset` or `impl Iterator<Item = Sample>`
- model_weights: `Arc<RwLock<Weights>>` if shared access needed

#### 11. State Machine

```
Idle → Loading → Ready → Training → Checkpointing → Done
                  ↓
                Error → Idle (reset)
```

With valid actions per state.

#### 12. Edge Cases
Error conditions, recovery procedures, limits.

---

## Workflows

### Workflow 1: Document Existing Program

```
# 1. Create overview
/coder:blueprint add myprogram overview "Architecture"

# 2. Claude fills it in by analyzing the code

# 3. Add section blueprints
/coder:blueprint add myprogram api "REST API layer" --depends overview

# 4. Check status
/coder:blueprint status myprogram
```

### Workflow 2: Extract Behavior for Porting

```
# 1. Create blueprint with behavior extraction
/coder:blueprint add source-program feature "Feature X" --extract-tests

# 2. Claude analyzes source and fills in the 12 sections

# 3. Verify extraction quality
/coder:blueprint load source-program/feature --behavior
```

### Workflow 3: Port Feature to New Codebase

Prerequisites:
- Source has: `source-program/feature-BEHAVIOR.md`
- Target has: `target-program/overview.md` (for conventions)

```
# 1. Add feature with reference
/coder:add-feature target-program my-feature "Feature X" --reference source-program/feature

# 2. Claude checks compatibility, reports issues:
#    ❌ Blockers - must resolve before implementing
#    ⚠️ Warnings - note for implementation

# 3. Implement (Claude follows: domain layer first, adapters second)

# 4. Verify implementation
/coder:verify-behavior target-program/my-feature

# 5. Fix any ❌ violations, document ⚠️ manual checks
```

### Workflow 4: Update Outdated Blueprint

```
# 1. Mark as outdated
/coder:blueprint update myprogram/section --status outdated

# 2. Claude re-analyzes code

# 3. Mark complete
/coder:blueprint update myprogram/section --status complete
```

---

## File Structure

```
.planning/blueprints/
├── MANIFEST.md                    # Human-readable index
├── onetrainer/
│   ├── _index.json                # Machine-readable metadata
│   ├── overview.md                # High-level architecture
│   ├── training-pipeline.md       # Section blueprint
│   ├── training-pipeline-BEHAVIOR.md  # Behavior spec
│   └── models/
│       ├── flux.md
│       ├── flux-BEHAVIOR.md
│       ├── sana.md
│       └── sana-BEHAVIOR.md
└── eritrainer/
    ├── _index.json
    └── overview.md

.planning/features/
├── eritrainer-sana.md             # Feature spec (from --reference)
└── feature-auth.md                # Standard feature spec
```

---

## Compatibility Checking

### Ownership Compatibility

When porting to memory-safe languages (Rust, etc.):

| Source Pattern | Issue | Resolution |
|----------------|-------|------------|
| 'static lifetime | Requires explicit cleanup | Add unload() method |
| Move consumed input | Caller can't reuse | Document clearly |
| Shared mutable state | Needs Arc<RwLock> | Add thread safety |

### Side Effect Compatibility

When target forbids global state:

| Source Pattern | Issue | Resolution |
|----------------|-------|------------|
| Global mutations | Forbidden | Encapsulate in struct |
| Env var writes | May be forbidden | Pass config explicitly |
| Not thread-safe | May conflict | Add synchronization |

---

## Best Practices

### DO
- ✅ Extract behavior before implementation details
- ✅ Document ownership semantics for all data
- ✅ Include resource budgets with real numbers
- ✅ Map state machines for complex features
- ✅ Extract test contracts from source tests
- ✅ Verify implementation against spec

### DON'T
- ❌ Copy code between languages
- ❌ Skip compatibility checking
- ❌ Ignore ❌ violations
- ❌ Leave ⚠️ items unverified
- ❌ Mix framework code into domain layer

---

## Troubleshooting

### "No behavior spec found"

Create one:
```
/coder:blueprint add program section "desc" --extract-behavior
```

### "No blueprint found for target"

Create target overview:
```
/coder:blueprint add target overview "Architecture"
```

### Compatibility check shows ❌ issues

These are blockers. Fix before implementing:
- Ownership issues → Restructure data flow
- Side effect issues → Encapsulate state

### verify-behavior shows ❌ violations

Your code doesn't match the spec. Either:
- Fix the code to match spec, OR
- Update the spec if intentional change

---

## Example: Porting Sana from OneTrainer to EriTrainer

**Goal:** Port Sana model training from Python/PyTorch to Rust/Candle

### Step 1: Document the Source

```
/coder:blueprint add onetrainer models/sana "Sana model training" --extract-tests
```

Claude creates and fills in the BEHAVIOR.md with:
- Interface: SanaModel, SanaModelLoader, BaseSanaSetup
- Ownership: model owned, batch borrowed, latents per-step
- Resources: ~14GB VRAM (LoRA), ~32GB (full)
- State: UNINITIALIZED → LOADING → READY → TRAINING → DONE

### Step 2: Document the Target

```
/coder:blueprint add eritrainer overview "EriTrainer architecture"
```

Claude maps conventions:
- Base traits: `ModelTrait`, `Forward`
- Error handling: `Result<T, ModelError>`
- Threading: `Arc<RwLock<T>>` for shared state

### Step 3: Port with Reference

```
/coder:add-feature eritrainer sana "Sana model" --reference onetrainer/models/sana
```

Claude reports:
- ✅ Interface compatible (can implement ModelTrait)
- ⚠️ Python dict returns → need typed struct
- ⚠️ Global CUDA state → need encapsulation

### Step 4: Implement

Claude implements following domain-first principle:
1. Core sana logic (no framework deps)
2. Candle tensor adapters
3. EriTrainer integration layer

### Step 5: Verify

```
/coder:verify-behavior eritrainer/sana
```

Verification table:
| Spec | Check | Status |
|------|-------|--------|
| Input: Dataset | fn new(dataset: &Dataset) | ✅ |
| Output: TrainedModel | -> Result<Model> | ✅ |
| State: Idle→Loading→Ready | Found state enum | ✅ |
| Thread safe | Uses Arc<RwLock> | ✅ |
| Resource: <24GB VRAM | Manual check | ⚠️ |

All ✅, implementation complete.

---

## Version History

- **v0.57** - Initial blueprint & behavior system
- **v0.58** - Added interface contract, ownership model, side effect checking
- **v0.59** - Added verify-behavior command
