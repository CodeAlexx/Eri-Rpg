# Plan Phase Reference

Detailed documentation for phase planning.

## CLI Response Format

`python3 -m erirpg.cli coder-plan-phase N` returns:

```json
{
  "phase_number": 1,
  "phase_name": "setup",
  "phase_dir": ".planning/phases/01-setup",
  "goal": "Set up project infrastructure",
  "has_context": true,
  "has_research": false,
  "is_brownfield": true,
  "settings": {
    "plan_check": true,
    "research": true
  },
  "paths": {
    "project": ".planning/PROJECT.md",
    "roadmap": ".planning/ROADMAP.md",
    "state": ".planning/STATE.md"
  }
}
```

---

## Research Depth Indicators

### Level 0 - Skip Research

**ALL must be true:**
- Work follows existing codebase patterns (grep confirms)
- No new external dependencies
- Pure internal refactoring or feature extension

**Examples:**
- Add delete button using existing button component
- Add field to existing model
- Extend existing CRUD operations

### Level 1 - Quick Verify (2-5 min)

**Indicators:**
- Single known library, confirming syntax/version
- Low-risk decision (easily changed later)
- Keywords: add, extend, update, modify

**Examples:**
- Confirm React hook syntax
- Check Prisma migration command
- Verify API endpoint format

**No agent needed.** Verify inline with grep/read.

### Level 2 - Standard Research (15-30 min)

**MANDATORY for:**
- New library not in package.json/requirements.txt
- External API integration
- "Choose/select/evaluate" in phase description
- Multiple implementation approaches possible

**Keywords:** integrate, api, external, library, choose, select, evaluate, implement new

**Examples:**
- Pick authentication library
- Integrate Stripe payments
- Choose state management solution

### Level 3 - Deep Dive (1+ hour)

**MANDATORY for:**
- Architectural decisions with long-term impact
- "Architecture/design/system" in phase description
- Multiple external services
- Data modeling decisions
- Auth/security design

**Keywords:** architect, design, system, security, auth, database, schema, model

**Examples:**
- Design database schema
- Plan microservices architecture
- Security model for multi-tenant

---

## Detection Logic

```bash
GOAL="$1"

# Level 3 indicators
if echo "$GOAL" | grep -qiE "architect|design|system|security|auth|database|schema|model"; then
  echo "3"
# Level 2 indicators
elif echo "$GOAL" | grep -qiE "integrat|api|external|library|choose|select|evaluat|implement.*new"; then
  echo "2"
# Level 1 indicators
elif echo "$GOAL" | grep -qiE "add|extend|update|modify"; then
  echo "1"
# Level 0
else
  echo "0"
fi

# Override if RESEARCH.md exists
if [ -f "${phase_dir}/RESEARCH.md" ]; then
  echo "0"  # Already done
fi
```

---

## Confidence Gates

After researcher returns, check RESEARCH.md frontmatter:

```bash
CONFIDENCE=$(grep "^confidence:" "${phase_dir}/RESEARCH.md" | cut -d: -f2 | tr -d ' ')
```

| Confidence | Action |
|------------|--------|
| HIGH | Proceed to planning immediately |
| MEDIUM | Warn user: "Research confidence is MEDIUM - some assumptions made." Proceed. |
| LOW | **STOP** - Do not proceed without user approval |

**LOW confidence handling:**
1. Present what's uncertain and why
2. Ask user: "Dig deeper / Proceed anyway / Pause"
3. Wait for explicit response
4. Do NOT proceed automatically

---

## Planner Prompt Structure

The eri-planner needs full context:

```
<project>
{Full PROJECT.md content}
</project>

<roadmap>
{Full ROADMAP.md content}
</roadmap>

<state>
{Full STATE.md content}
</state>

<context>
{CONTEXT.md if exists, else "No CONTEXT.md - plan freely based on goal"}
</context>

<research>
{RESEARCH.md if exists, else "No research performed - Level 0"}
</research>

<mode>
{"gap_closure" if --gaps flag, else "standard"}
</mode>
```

**Planner outputs:**
- PLAN.md files in phase directory
- Wave assignments (wave: N in frontmatter)
- must_haves for verification
- Runtime verification criteria

---

## Plan Checker Dimensions

eri-plan-checker validates:

1. **Requirement coverage** - All requirements have tasks
2. **Task completeness** - Each task has files/action/verify/done
3. **Dependency correctness** - depends_on and waves consistent
4. **Key links planned** - Critical wiring has explicit tasks
5. **Scope sanity** - Plans fit in ~50% context
6. **Must-haves derivation** - Goal-backward methodology used
7. **Context compliance** - Locked decisions honored, deferred excluded

**If issues found:** Spawn planner in revision mode with issues list.

---

## Agent Failure Handling

If Task tool returns error:

1. **Retry once** — transient errors common
2. **If still fails, STOP:**
   ```
   Agent spawn failed: {error}

   Options:
   - Retry: Try spawning again
   - Skip: Continue without (not recommended)
   - Abort: Stop and preserve state
   ```
3. **DO NOT improvise** — Never do agent's job yourself
4. **Wait for user decision**

---

## Gap Mode (--gaps)

When re-planning from verification failures:

1. CLI returns with `mode: "gap_closure"`
2. Read VERIFICATION.md for gap details
3. Planner creates targeted gap-closure plans
4. Plans get `gap_closure: true` in frontmatter
5. Execute with `/coder:execute-phase N --gaps-only`

Gap plans are smaller, focused fixes.
