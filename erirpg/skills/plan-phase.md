---
name: coder:plan-phase
description: Create executable plans with verification criteria for a phase
argument-hint: "<phase-number> [--gaps]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
---

# Plan Phase

Create executable plans for a phase. This skill orchestrates research, planning, and validation - do not skip steps.

<process>

<step name="1_call_cli" priority="first">
## Step 1: Get Phase Context from CLI

```bash
python3 -m erirpg.cli coder-plan-phase $ARGUMENTS
```

For gap mode (re-planning from verification failures):
```bash
python3 -m erirpg.cli coder-plan-phase $ARGUMENTS --gaps
```

The CLI returns JSON with:
- `phase_number`: Phase number
- `phase_name`: Phase name
- `phase_dir`: Path to phase directory
- `goal`: Phase goal from ROADMAP.md
- `has_context`: Whether CONTEXT.md exists
- `has_research`: Whether RESEARCH.md exists
- `is_brownfield`: Whether codebase docs exist
- `settings`: Workflow settings (includes `model_profile`)
- `paths`: Paths to PROJECT.md, ROADMAP.md, STATE.md, etc.

Parse and store these values for subsequent steps.

### Resolve Model Profile

Extract the model profile from settings and resolve models for each agent type:

```bash
MODEL_PROFILE=$(cat .planning/config.json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('model_profile', 'balanced'))
except: print('balanced')
" 2>/dev/null || echo "balanced")
```

**Model lookup table:**

| Profile | Researcher | Planner | Plan-Checker |
|---------|-----------|---------|--------------|
| quality | opus | opus | sonnet |
| balanced | haiku | sonnet | sonnet |
| budget | haiku | sonnet | haiku |

Resolve the specific models you'll use in this command:

```bash
case "$MODEL_PROFILE" in
  quality)  RESEARCHER_MODEL="opus";  PLANNER_MODEL="opus";  CHECKER_MODEL="sonnet" ;;
  budget)   RESEARCHER_MODEL="haiku"; PLANNER_MODEL="sonnet"; CHECKER_MODEL="haiku" ;;
  *)        RESEARCHER_MODEL="haiku"; PLANNER_MODEL="sonnet"; CHECKER_MODEL="sonnet" ;;
esac
```

Report: `Model profile: {MODEL_PROFILE} (researcher={RESEARCHER_MODEL}, planner={PLANNER_MODEL}, checker={CHECKER_MODEL})`
</step>

<step name="2_load_state">
## Step 2: Load Project State

Read and internalize project state:

```bash
cat .planning/STATE.md 2>/dev/null
cat .planning/PROJECT.md 2>/dev/null
cat .planning/ROADMAP.md 2>/dev/null
```

Parse:
- Current position
- Prior phase decisions (constraints on this phase)
- Blockers/concerns from previous phases
</step>

<step name="3_detect_research_depth" priority="critical">
## Step 3: Detect Research Depth (MANDATORY)

**Research is NOT optional.** Determine required depth based on phase characteristics.

### Depth Indicators

**Level 0 - Skip** (only if ALL true):
- All work follows existing codebase patterns (grep confirms)
- No new external dependencies
- Pure internal refactoring or feature extension
- Examples: Add delete button, add field to model, extend existing CRUD

**Level 1 - Quick Verify** (2-5 min):
- Single known library, confirming syntax/version
- Low-risk decision (easily changed later)
- Examples: Confirm React hook syntax, check Prisma migration command

**Level 2 - Standard Research** (15-30 min) - MANDATORY for:
- New library not in package.json/requirements.txt
- External API integration
- "Choose/select/evaluate" in phase description
- Multiple implementation approaches possible
- Examples: Pick auth library, integrate Stripe, choose state management

**Level 3 - Deep Dive** (1+ hour) - MANDATORY for:
- Architectural decisions with long-term impact
- "Architecture/design/system" in phase description
- Multiple external services
- Data modeling decisions
- Auth/security design
- Examples: Design database schema, plan microservices split, security model

### Detection Logic

```bash
# Check for new dependencies in phase goal
GOAL="${phase_goal}"

# Level 3 indicators
if echo "$GOAL" | grep -qiE "architect|design|system|security|auth|database|schema|model"; then
  RESEARCH_DEPTH=3
# Level 2 indicators
elif echo "$GOAL" | grep -qiE "integrat|api|external|library|choose|select|evaluat|implement.*new"; then
  RESEARCH_DEPTH=2
# Level 1 indicators
elif echo "$GOAL" | grep -qiE "add|extend|update|modify"; then
  RESEARCH_DEPTH=1
# Level 0 - pure internal
else
  RESEARCH_DEPTH=0
fi

# Override: If RESEARCH.md already exists, use it
if [ -f "${phase_dir}/RESEARCH.md" ]; then
  RESEARCH_DEPTH=0  # Already done
fi
```

Report detected depth:
```
Research depth: Level {N} ({reason})
```
</step>

<step name="4_research">
## Step 4: Execute Research (If Depth > 0)

**Skip this step only if Level 0 detected.**

### Level 1: Quick Verify

No agent needed. Verify inline:

```bash
# Check existing patterns
grep -r "import.*{library}" src/ --include="*.ts" | head -3

# Check package.json for version
grep "{library}" package.json
```

Confirm syntax/version is current. Document any concerns.

### Level 2-3: Spawn Researcher

Spawn **eri-phase-researcher** with depth parameter and resolved model:

```
Task(
  subagent_type="eri-phase-researcher",
  model="{RESEARCHER_MODEL}",
  prompt="Research implementation for phase {phase_number}: {phase_name}

<depth>{RESEARCH_DEPTH}</depth>

<phase_goal>
{goal from ROADMAP.md}
</phase_goal>

<context_md>
{CONTEXT.md content if exists, else "None"}
</context_md>

<existing_patterns>
{Key patterns from codebase if brownfield}
</existing_patterns>

Create {phase_dir}/RESEARCH.md with:
- Recommended approach with rationale
- Step-by-step implementation guidance
- Integration points with existing code
- Pitfalls specific to this phase
- Confidence level (HIGH/MEDIUM/LOW)

If confidence is LOW, flag for user review before planning."
)
```

### Confidence Gate

After researcher returns, check confidence:

```bash
CONFIDENCE=$(grep "^confidence:" "${phase_dir}/RESEARCH.md" | cut -d: -f2 | tr -d ' ')
```

| Confidence | Action |
|------------|--------|
| HIGH | Proceed to planning |
| MEDIUM | Warn user, proceed |
| LOW | **STOP** - Ask user: "Research confidence is LOW. Dig deeper / Proceed anyway / Pause" |

**Do NOT proceed to planning on LOW confidence without user approval.**
</step>

<step name="5_planning">
## Step 5: Create Plans

Spawn **eri-planner** with full context and resolved model:

```bash
# Read all context files
PROJECT=$(cat .planning/PROJECT.md 2>/dev/null)
ROADMAP=$(cat .planning/ROADMAP.md 2>/dev/null)
STATE=$(cat .planning/STATE.md 2>/dev/null)
CONTEXT=$(cat "${phase_dir}/CONTEXT.md" 2>/dev/null)
RESEARCH=$(cat "${phase_dir}/RESEARCH.md" 2>/dev/null)
```

```
Task(
  subagent_type="eri-planner",
  model="{PLANNER_MODEL}",
  prompt="Create execution plans for phase {phase_number}: {phase_name}

<project>
{PROJECT}
</project>

<roadmap>
{ROADMAP}
</roadmap>

<state>
{STATE}
</state>

<context>
{CONTEXT if exists, else 'No CONTEXT.md - plan freely based on goal'}
</context>

<research>
{RESEARCH if exists, else 'No research performed - Level 0'}
</research>

<mode>{'gap_closure' if --gaps else 'standard'}</mode>

Create PLAN.md files in {phase_dir}/ with:
- 2-3 tasks per plan (stay under 50% context)
- Wave assignments for parallel execution
- must_haves in frontmatter (goal-backward derived)
- Runtime verification criteria (not just static checks)

Return: List of plans created, wave structure, any concerns."
)
```

Wait for planner to complete.
</step>

<step name="6_plan_check">
## Step 6: Validate Plans (If Enabled)

Check if plan validation is enabled:

```bash
PLAN_CHECK=$(cat .planning/config.json 2>/dev/null | grep -o '"plan_check"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o 'true\|false' || echo "true")
```

**If plan_check is true:**

Spawn **eri-plan-checker** with resolved model:

```
Task(
  subagent_type="eri-plan-checker",
  model="{CHECKER_MODEL}",
  prompt="Validate plans for phase {phase_number}: {phase_name}

<phase_dir>{phase_dir}</phase_dir>

<context>
{CONTEXT.md content if exists}
</context>

Check all dimensions:
1. Requirement coverage - All requirements have tasks
2. Task completeness - Each task has files/action/verify/done
3. Dependency correctness - depends_on and waves are consistent
4. Key links planned - Critical wiring has explicit tasks
5. Scope sanity - Plans fit in ~50% context
6. Must-haves derivation - Goal-backward methodology used
7. Context compliance - Locked decisions honored, deferred ideas excluded

Return: Issues list with severity and fix hints, or 'PASSED' if all clear."
)
```

### Handle Checker Results

**If issues found:**

```
Plan validation found {N} issues:

{list issues with severity}

Spawning planner in revision mode...
```

Spawn **eri-planner** again with revision context and resolved model:

```
Task(
  subagent_type="eri-planner",
  model="{PLANNER_MODEL}",
  prompt="Revise plans for phase {phase_number} based on checker feedback.

<issues>
{checker issues}
</issues>

<existing_plans>
{current plan contents}
</existing_plans>

Make targeted updates to address issues. Do NOT rewrite entire plans.
Return: Updated plans, issues addressed."
)
```

**If PASSED:** Proceed to completion.
</step>

<step name="7_commit">
## Step 7: Commit Plans

```bash
git status --short .planning/phases/
```

If uncommitted plans exist:

```bash
git add .planning/phases/${phase_dir}/
git commit -m "plan(phase-${phase_number}): create execution plans for ${phase_name}

- Plans: {count}
- Research: {depth level}
- Plan check: {passed|skipped}
"
```
</step>

</process>

<completion>
## On Completion

### 1. Update STATE.md

```markdown
## Current Phase
**Phase {N}: {phase-name}** - planned (ready to execute)

## Last Action
Completed plan-phase {N}
- Plans created: {count}
- Research depth: Level {N} ({confidence})
- Plan check: {passed|skipped}

## Next Step
Run `/coder:execute-phase {N}` to build the code
```

### 2. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 3. Present Next Steps

<offer_next>

**Primary route (execute):**
```
╔════════════════════════════════════════════════════════════════╗
║  ✓ PHASE {N} PLANNED                                           ║
╠════════════════════════════════════════════════════════════════╣
║  Plans created: {list}                                         ║
║  Research: Level {depth} ({confidence})                        ║
║  Model profile: {MODEL_PROFILE}                                ║
║  Location: .planning/phases/{NN-name}/                         ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Execute the plans

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:execute-phase {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This will spawn executors to build the code for each plan.

## Alternatives
- Review plans first:  Read .planning/phases/{NN-name}/*-PLAN.md
- Adjust settings:     /coder:settings
- View progress:       /coder:progress
```

</offer_next>
</completion>

<context_flow>
## CONTEXT.md Flow (IMPORTANT)

If CONTEXT.md exists, it MUST flow through the entire pipeline:

| Stage | How CONTEXT.md is Used |
|-------|------------------------|
| Research | Locked decisions: Don't research alternatives. Discretion: Research freely. Deferred: Ignore. |
| Planning | Locked: Implement exactly. Discretion: Make best call. Deferred: Exclude entirely. |
| Checking | Verify locked decisions have tasks, deferred ideas excluded |
| Revision | Maintain compliance when fixing issues |

**Never skip CONTEXT.md.** If it exists, every agent must receive it.
</context_flow>

<agent_failure_handling>
## If Agent Spawn Fails

If the Task tool returns an error (API 500, timeout, rejection):

1. **Retry once** - transient errors are common
2. **If still fails, STOP and report:**
   ```
   Agent spawn failed: {error}

   Options:
   - Retry: I can try spawning the agent again
   - Skip: Continue without this step (not recommended for research/planning)
   - Abort: Stop and preserve state
   ```
3. **DO NOT improvise** - Never try to do the agent's job yourself
4. **Wait for user decision** - Don't proceed until user responds
</agent_failure_handling>

<critical_rules>
## Critical Rules

1. **Research is mandatory for Level 2-3** - Don't skip external integrations
2. **Stop on LOW confidence** - Get user approval before proceeding
3. **CONTEXT.md flows everywhere** - Every agent receives it
4. **Plan check catches issues** - Don't skip validation
5. **Show the completion box** - Never say "ready when you are"
</critical_rules>
