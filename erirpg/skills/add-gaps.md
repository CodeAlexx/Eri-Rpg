---
name: coder:add-gaps
description: Report bugs found during manual testing and route to gap closure
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

## CLI Integration

**First, call the CLI to gather phase context:**
```bash
python3 -m erirpg.cli coder-add-gaps $ARGUMENTS
```

This returns JSON with:
- `phase`: Phase number
- `phase_dir`: Path to phase directory
- `phase_goal`: Goal from ROADMAP.md
- `must_haves`: Object with truths, artifacts, key_links
- `has_verification`: Whether VERIFICATION.md already exists
- `verification_status`: Current verification status
- `existing_gaps`: Already-reported gaps (avoid duplicates)
- `verification_path`: Path to VERIFICATION.md

Use this data to guide the bug reporting loop.

---

<objective>
Lightweight bug reporting: user describes bugs found during manual testing,
skill writes/updates VERIFICATION.md with status: gaps_found, then routes
to the existing gap closure pipeline (plan-phase --gaps).
No agent spawn needed — this is direct user interaction + file writing.
</objective>

<context>
Phase number: $ARGUMENTS
Read: CLI output (phase context, must_haves, existing verification)
Output: .planning/phases/{XX-name}/VERIFICATION.md (created or updated)
</context>

<process>
## Step 1: Show Phase Context

Display:
```
Phase {N}: {phase_goal}

Must-Have Truths (reference for bug reports):
  1. {truth_1}
  2. {truth_2}
  ...
```

If existing_gaps is non-empty, show:
```
Already reported gaps:
  - {gap_1}
  - {gap_2}
```

## Step 2: Bug Reporting Loop

Use AskUserQuestion in a loop:

**First question — describe the bug:**
Ask: "Describe the bug or issue you found"
- Options: free text (user selects "Other")

**Second question — which truth does it relate to?**
Show the numbered must_haves truths list.
Ask: "Which truth/requirement does this relate to?"
- Options: numbered truths from must_haves, plus "None / New issue"

**Third question — affected files (optional):**
Ask: "Which files are affected? (comma-separated paths, or skip)"
- Options: "Skip — not sure", or free text

**Fourth question — more bugs?**
Ask: "Do you have more bugs to report?"
- Options: "Yes, report another", "No, that's all"

Repeat the loop if user says "Yes, report another".

Collect all bugs as a list:
```
bugs = [
  {description, related_truth, affected_files},
  ...
]
```

## Step 3: Write/Update VERIFICATION.md

### If VERIFICATION.md does NOT exist — create from scratch:

```markdown
---
phase: {XX-name}
verified: {timestamp}
status: gaps_found
score: "0/{total_truths} must-haves verified"
gaps:
  - "{bug_1_description}"
  - "{bug_2_description}"
---

# Phase {N} Verification

## Must-Have Results

{For each truth in must_haves.truths:}
### {truth}
- **Status:** {gap if related bug exists, else untested}
- **Gap:** {bug description if related}
- **Files:** {affected files if provided}

## Gaps Summary

| # | Description | Related Truth | Affected Files |
|---|-------------|--------------|----------------|
| 1 | {bug_1_desc} | {truth or N/A} | {files or —} |
| 2 | {bug_2_desc} | {truth or N/A} | {files or —} |
```

### If VERIFICATION.md ALREADY exists — merge new gaps:

1. Read existing file
2. Parse existing frontmatter (preserve status fields, passed items)
3. Set `status: gaps_found`
4. Append new gaps to the `gaps:` YAML list (avoid duplicates)
5. Append new rows to `## Gaps Summary` table
6. Do NOT overwrite any existing passing results — merge only

## Step 4: Commit

```bash
git add {verification_path}
git commit -m "verify: report gaps for phase {N}"
```
</process>

<completion>
## On Completion

### 1. Update STATE.md

```markdown
## Current Phase
**Phase {N}: {phase-name}** - gaps_found

## Last Action
Completed add-gaps {N}
- Bugs reported: {count}
- Status: gaps_found

## Next Step
Plan gap closure: /coder:plan-phase {N} --gaps
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ⚠ GAPS REPORTED FOR PHASE {N}                                  ║
╠════════════════════════════════════════════════════════════════╣
║  Bugs reported: {count}                                        ║
║  Written to: VERIFICATION.md                                   ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Plan fixes for the gaps

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:plan-phase {N} --gaps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This creates fix plans targeting the reported bugs.
```
</completion>
