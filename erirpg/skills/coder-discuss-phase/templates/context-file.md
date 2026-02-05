# CONTEXT.md Template

```markdown
# Phase [X]: [Name] - Context

**Gathered:** [date]
**Status:** Ready for planning

<domain>
## Phase Boundary

[Clear statement of what this phase delivers — the scope anchor]

</domain>

<decisions>
## Implementation Decisions

### [Category 1 that was discussed]
- [Decision or preference captured]
- [Another decision if applicable]

### [Category 2 that was discussed]
- [Decision or preference captured]

### Claude's Discretion
[Areas where user said "you decide" — note that Claude has flexibility here]

</decisions>

<specifics>
## Specific Ideas

[Any particular references, examples, or "I want it like X" moments from discussion]

[If none: "No specific requirements — open to standard approaches"]

</specifics>

<deferred>
## Deferred Ideas

[Ideas that came up but belong in other phases. Don't lose them.]

[If none: "None — discussion stayed within phase scope"]

</deferred>

---

*Phase: XX-name*
*Context gathered: [date]*
```

## Section Guidelines

### Phase Boundary
- State clearly what this phase delivers
- This anchors scope discussions
- Downstream agents use this to stay focused

### Implementation Decisions
- Group by the areas that were discussed
- Be specific: "Cards with 3 items per row" not "nice layout"
- Include rationale if user provided it

### Claude's Discretion
- List areas where user explicitly said "you decide"
- Planner has flexibility here
- Don't leave implicit — be explicit about discretion

### Specific Ideas
- Capture any references: "like Twitter's feed"
- Capture any examples user mentioned
- Capture any "must have" specific behaviors

### Deferred Ideas
- Don't lose scope creep — capture it here
- These become input for roadmap updates
- Include enough context to understand later
