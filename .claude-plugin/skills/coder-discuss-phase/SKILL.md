---
name: coder:discuss-phase
description: Capture implementation decisions for a specific phase before planning
argument-hint: "<phase-number>"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

# Coder Discuss-Phase

Extract implementation decisions that downstream agents need. Analyze the phase to identify gray areas, let the user choose what to discuss, then deep-dive each selected area.

**You are a thinking partner, not an interviewer.** The user is the visionary — you are the builder. Capture decisions that will guide research and planning.

## Dynamic Context

**CLI phase data:**
!`python3 -m erirpg.cli coder-discuss-phase $ARGUMENTS 2>/dev/null || echo '{"error": "Phase not found"}'`

**Existing context:**
!`cat .planning/phases/*/CONTEXT.md 2>/dev/null | head -20 || echo "none"`

---

## Philosophy

**User = founder/visionary. Claude = builder.**

The user knows:
- How they imagine it working
- What it should look/feel like
- What's essential vs nice-to-have

Don't ask the user about:
- Codebase patterns (researcher reads the code)
- Technical risks (researcher identifies these)
- Implementation approach (planner figures this out)

---

## Downstream Awareness

**CONTEXT.md feeds into:**

1. **eri-phase-researcher** — Reads CONTEXT.md to know WHAT to research
2. **eri-planner** — Reads CONTEXT.md to know WHAT decisions are locked

Capture decisions clearly enough that downstream agents can act without asking the user again.

---

## Scope Guardrail

**CRITICAL: No scope creep.**

The phase boundary comes from ROADMAP.md and is FIXED.

**Allowed:** "How should posts be displayed?" (clarifying)
**Not allowed:** "Should we also add comments?" (new capability)

When user suggests scope creep:
```
"[Feature X] would be a new capability — that's its own phase.
Want me to note it for the roadmap backlog?
For now, let's focus on [phase domain]."
```

Capture the idea in "Deferred Ideas" section.

---

## Workflow Steps

### Step 1: Validate Phase
Call CLI, check phase exists.
See [reference.md](reference.md#step-1-validate-phase).

### Step 2: Check Existing Context
If context exists, offer: Update / View / Skip.
See [reference.md](reference.md#step-2-check-existing-context).

### Step 3: Analyze Phase
Identify gray areas worth discussing.
See [reference.md](reference.md#step-3-analyze-phase).

### Step 4: Present Gray Areas
Use AskUserQuestion (multiSelect) for area selection.
See [reference.md](reference.md#step-4-present-gray-areas).

### Step 5: Discuss Selected Areas
4 questions, then check. Repeat until satisfied.
See [reference.md](reference.md#step-5-discuss-selected-areas).

### Step 6: Write CONTEXT.md
Create context file with decisions.
See [reference.md](reference.md#step-6-write-contextmd).

### Step 7: Commit
Commit context file.

---

## Gray Area Examples

| Phase Domain | Gray Areas |
|--------------|------------|
| Post Feed | Layout style, Loading behavior, Content ordering, Post metadata |
| Database CLI | Output format, Flag design, Progress reporting, Error recovery |
| Photo Library | Grouping criteria, Duplicate handling, Naming convention, Folder structure |
| Authentication | Session handling, Error responses, Multi-device policy, Recovery flow |

See [reference.md](reference.md#gray-area-identification) for full examples.

---

## Completion

Use [templates/completion-box.md](templates/completion-box.md) format.
Use [templates/context-file.md](templates/context-file.md) for CONTEXT.md structure.
