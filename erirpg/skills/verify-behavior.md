---
name: coder:verify-behavior
description: Run behavior diff after implementation
argument-hint: "<program>/<feature>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# /coder:verify-behavior - Behavior Diff Validation

Run "Behavior Diff" after implementation to verify code matches behavior spec.

## CLI Command

```bash
python3 -m erirpg.commands.verify_behavior <program>/<feature> --json
```

## Purpose

After implementing a feature from a behavior spec, this command checks that your code actually implements what the spec describes.

**Catches:**
- Missing input/output types
- Broken state machine transitions
- Ownership violations
- Forbidden side effects
- Missing test coverage

## Verification Table

The command generates a verification table:

```
| Behavior Spec | Code Check | Status |
|---------------|------------|--------|
| Input: Dataset | fn new(dataset: &Dataset) | ✅ |
| Output: TrainedModel | -> Result<Model> | ✅ |
| State: Idle→Loading→Ready | Found state enum | ✅ |
| Side-effect: No global mutation | No static mut | ✅ |
| Ownership: dataset borrowed | &Dataset (not owned) | ✅ |
| Test: empty dataset raises | #[test] test_empty | ✅ |
| Resource: <24GB VRAM | No check possible | ⚠️ Manual |
```

## Status Values

- **✅ Pass** - Code matches spec
- **❌ Fail** - Code violates spec (MUST FIX)
- **⚠️ Manual** - Cannot auto-check, needs human verification
- **⏳ Pending** - Not yet analyzed

## Workflow

### 1. After Implementation

```bash
# Verify your implementation
python3 -m erirpg.commands.verify_behavior eritrainer/sana --json
```

### 2. Check Results

```json
{
  "status": "FAILED",
  "message": "❌ 2 violations found - fix before marking done",
  "blocking": true,
  "report": {
    "items": [...],
    "summary": {
      "passed": 5,
      "failed": 2,
      "manual": 1,
      "pending": 0
    }
  }
}
```

### 3. Fix Violations

For each ❌ item:
1. Read the spec requirement
2. Find the corresponding code
3. Fix the code to match spec
4. Re-run verify-behavior

### 4. Manual Verification

For each ⚠️ item:
1. Understand what needs verification
2. Test manually or document verification
3. Mark as verified in feature spec

## What Gets Checked

### Inputs (type_signature)
- Input parameter types match spec
- Required inputs are present
- Optional inputs have defaults

### Outputs (output_check)
- Return types match spec
- Error types match spec
- Side effects documented

### Interface (interface_check)
- Base trait/interface implemented
- Method signatures match
- Decorators/annotations present

### State Machine (state_machine)
- All states exist in code
- Transitions are valid
- Actions per state match

### Test Contracts (test_contract)
- Each Given/When/Then has a test
- Edge cases are tested
- Error conditions are tested

### Global State (global_state_check)
- No forbidden global mutations
- Thread safety requirements met
- File/network operations documented

### Ownership (ownership_check)
- Borrow vs move matches spec
- Lifetimes are correct
- No unexpected clones

### Resources (manual_verify)
- Memory requirements documented
- Time requirements documented
- Constraints acknowledged

## When to Run

- **After implementation** - Before marking feature done
- **After refactoring** - Ensure spec still matches
- **Before PR** - Verify nothing broken
- **After merge conflicts** - Check still valid

## Blocking Behavior

If the result has `"blocking": true`:
- There are ❌ violations
- Do NOT mark feature as complete
- Do NOT commit until fixed

## Integration

This command reads:
- `.planning/blueprints/{program}/{section}-BEHAVIOR.md`
- `.planning/features/{program}-{feature}.md`

And analyzes:
- Source code in target program
- Test files for test contracts

## Arguments

$ARGUMENTS should be `<program>/<feature>`:
- `eritrainer/sana` - Verify sana feature in eritrainer
- `myapp/auth` - Verify auth feature in myapp
