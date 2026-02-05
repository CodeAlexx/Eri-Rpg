# Discuss-Phase Reference

Detailed documentation for implementation decision capture.

---

## Step 1: Validate Phase

Call CLI first:
```bash
python3 -m erirpg.cli coder-discuss-phase {phase_number}
```

CLI returns:
- `phase`: Phase number
- `phase_content`: Full phase section from ROADMAP.md
- `goal`: Extracted goal
- `requirements`: Mapped requirements
- `context_exists`: Whether CONTEXT.md already exists
- `phase_dir`: Path to phase directory

If phase not found:
```
Phase [X] not found in roadmap.
Use /coder:progress to see available phases.
```

---

## Step 2: Check Existing Context

If CLI returns `context_exists: true`:

Use AskUserQuestion:
- header: "Existing context"
- question: "Phase [X] already has context. What do you want to do?"
- options:
  - "Update it" — Review and revise existing context
  - "View it" — Show me what's there
  - "Skip" — Use existing context as-is

| Selection | Action |
|-----------|--------|
| Update | Load existing, continue to Step 3 |
| View | Display CONTEXT.md, then offer update/skip |
| Skip | Exit workflow |

---

## Step 3: Analyze Phase

Read the phase description from ROADMAP.md and determine:

1. **Domain boundary** — What capability is this phase delivering?
2. **Gray areas** — 3-5 concrete ambiguities that would change implementation
3. **Skip assessment** — If no meaningful gray areas, phase may not need discussion

### Domain Types

| Domain Type | What Matters |
|-------------|--------------|
| Something users SEE | Visual presentation, interactions, states |
| Something users CALL | Interface contracts, responses, errors |
| Something users RUN | Invocation, output, behavior modes |
| Something users READ | Structure, tone, depth, flow |
| Something being ORGANIZED | Criteria, grouping, handling exceptions |

---

## Step 4: Present Gray Areas

**First, state the boundary:**
```
Phase [X]: [Name]
Domain: [What this phase delivers]

We'll clarify HOW to implement this.
(New capabilities belong in other phases.)
```

**Then use AskUserQuestion (multiSelect: true):**
- header: "Discuss"
- question: "Which areas do you want to discuss for [phase name]?"
- options: Generate 3-4 phase-specific gray areas

---

## Gray Area Identification

**Don't use generic category labels** (UI, UX, Behavior). Generate specific gray areas.

### Examples by Domain

**For "Post Feed" (visual feature):**
```
☐ Layout style — Cards vs list vs timeline? Information density?
☐ Loading behavior — Infinite scroll or pagination? Pull to refresh?
☐ Content ordering — Chronological, algorithmic, or user choice?
☐ Post metadata — What info per post? Timestamps, reactions, author?
```

**For "Database backup CLI" (command-line tool):**
```
☐ Output format — JSON, table, or plain text? Verbosity levels?
☐ Flag design — Short flags, long flags, or both? Required vs optional?
☐ Progress reporting — Silent, progress bar, or verbose logging?
☐ Error recovery — Fail fast, retry, or prompt for action?
```

**For "Organize photo library" (organization task):**
```
☐ Grouping criteria — By date, location, faces, or events?
☐ Duplicate handling — Keep best, keep all, or prompt each time?
☐ Naming convention — Original names, dates, or descriptive?
☐ Folder structure — Flat, nested by year, or by category?
```

**For "User authentication" (system feature):**
```
☐ Session handling — Duration, refresh strategy, remember me?
☐ Error responses — Generic or specific? Rate limiting?
☐ Multi-device policy — Allow all, limit, or notify?
☐ Recovery flow — Email, SMS, or security questions?
```

### The Key Question

What decisions would change the outcome that the user should weigh in on?

### Claude Handles These (Don't Ask)

- Technical implementation details
- Architecture patterns
- Performance optimization
- Scope (roadmap defines this)

---

## Step 5: Discuss Selected Areas

**Philosophy: 4 questions, then check.**

For each selected area:

1. **Announce the area:**
   ```
   Let's talk about [Area].
   ```

2. **Ask up to 4 questions using AskUserQuestion:**
   - header: "[Area]"
   - question: Specific decision for this area
   - options: 2-3 concrete choices
   - Include "You decide" as an option when reasonable

3. **After 4 questions, check:**
   - header: "[Area]"
   - question: "More questions about [area], or move to next?"
   - options: "More questions" / "Next area"

4. **After all areas complete:**
   - header: "Done"
   - question: "That covers [list areas]. Ready to create context?"
   - options: "Create context" / "Revisit an area"

### Scope Creep Handling

If user mentions something outside the phase domain:
```
"[Feature] sounds like a new capability — that belongs in its own phase.
I'll note it as a deferred idea.

Back to [current area]: [return to current question]"
```

Track deferred ideas internally.

---

## Step 6: Write CONTEXT.md

Create `.planning/phases/{XX-name}/CONTEXT.md`:

See [templates/context-file.md](templates/context-file.md) for full template.

Key sections:
- **Phase Boundary** — Clear statement of what this phase delivers
- **Implementation Decisions** — Captured decisions by category
- **Claude's Discretion** — Areas where user said "you decide"
- **Specific Ideas** — References or examples from discussion
- **Deferred Ideas** — Scope creep captured for future phases

---

## Step 7: Commit

```bash
git add .planning/phases/
git commit -m "docs(phase-{N}): capture implementation context

- Implementation decisions documented
- Phase boundary established

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Criteria

- Phase validated against roadmap
- Gray areas identified through intelligent analysis (not generic questions)
- User selected which areas to discuss
- Each selected area explored until user satisfied
- Scope creep redirected to deferred ideas
- CONTEXT.md captures actual decisions, not vague vision
- Deferred ideas preserved for future phases
- User knows next steps
