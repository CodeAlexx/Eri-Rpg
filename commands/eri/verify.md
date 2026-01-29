---
name: eri:verify
description: Verify plan covers all spec requirements
argument-hint: "[plan-path] [--spec <spec-path>]"
---

<action>
You are performing **adversarial plan verification**. Your job is to find gaps between the spec and the plan, NOT to confirm the plan looks good.

## Core Mindset
**Assume gaps exist until proven otherwise.** The plan is guilty until proven innocent.

## Verification Process

### Step 1: Extract the Spec and Plan
First, get the spec and plan content:

```bash
# If plan path provided as argument
eri-rpg plan show $ARGUMENTS --json > /tmp/plan.json 2>/dev/null

# Get associated spec (usually in same .eri-rpg/specs/ directory)
# Or use --spec flag if provided
```

If no arguments, ask the user for the plan path.

### Step 2: Run Adversarial Verification

Perform this verification manually (or via the CLI when available):

**A. QUANTIFIER AUDIT (MANDATORY)**
Find all universal quantifiers in the spec:
- "all", "every", "each", "any", "both", "complete", "full", "entire"

For EACH quantifier found:
1. List what it refers to (e.g., "all models" -> image models, video models)
2. Check if the plan has steps covering EACH item
3. Mark as covered or MISSING

**B. EXPLICIT REQUIREMENTS CHECK**
For every noun/entity in the spec:
- Does the plan have a step that addresses it?
- Is the step concrete or vague?

**C. IMPLICIT REQUIREMENTS**
Things the spec assumes but doesn't state:
- Error handling
- Edge cases
- Testing

### Step 3: Output Format

Use this exact format:

```
═══════════════════════════════════════════════════════════
 ERI:VERIFY RESULTS
═══════════════════════════════════════════════════════════

Verdict: [COMPLETE | GAPS_FOUND | INCOMPLETE]
Confidence: [high | medium | low]
Coverage: X of Y requirements · Z gaps found

───────────────────────────────────────────────────────────
QUANTIFIER AUDIT
───────────────────────────────────────────────────────────
• "[quantifier phrase]"
  Refers to: [list of items]
  Covered:   [items with plan steps] ✓
  Missing:   [items without plan steps] ✗

───────────────────────────────────────────────────────────
GAPS
───────────────────────────────────────────────────────────

🔴 CRITICAL (blocks completion)
GAP-001: [short description]
  Spec says: "[quote from spec]"
  Plan has:  [what plan has or "nothing"]
  Fix:       [suggested fix]

🟡 MODERATE (notable omission)
GAP-002: ...

🟢 MINOR (could be deferred)
GAP-003: ...

───────────────────────────────────────────────────────────
RECOMMENDATION: [proceed | revise_plan | clarify_spec]
═══════════════════════════════════════════════════════════
```

## Anti-Patterns (DO NOT DO)
- ❌ "The plan looks comprehensive" - this is NOT verification
- ❌ Assuming coverage without listing each item
- ❌ Ignoring quantifiers
- ❌ Marking "covered" without specific step reference

## CLI Command
```bash
eri-rpg plan verify <plan-path> [--spec <spec-path>]
```

## Model Selection

```bash
# Auto mode (default): Sonnet first, escalate to Opus if needed
eri-rpg plan verify myproject

# Force specific model
eri-rpg plan verify myproject --model sonnet
eri-rpg plan verify myproject --model opus

# Skip auto-escalation
eri-rpg plan verify myproject --no-escalate
```

### Auto-Escalation Triggers
Sonnet → Opus escalation happens when:
- Verdict is PASS with 0 gaps (suspicious)
- Confidence is low or medium
- Gaps contain ambiguity-related findings

### Status Line
The CLI displays current model:
```
───────────────────────────────────────────────────────────
 PERSONA: Verifier │ MODEL: sonnet │ TASK: eri:verify
───────────────────────────────────────────────────────────
```

Updates to show `opus` when escalating.

</action>
