# Phase 05: Features

## Discussion Mode

### Vague Goal Detection
```python
is_vague = is_vague_goal("improve performance")  # True
is_vague = is_vague_goal("add login endpoint to auth.py")  # False
```

Detection triggers:
- Short goals (<20 chars)
- Vague words: improve, fix, refactor, update, change
- Missing specifics: no file names, function names, etc.

### New Project Detection
```python
is_new = is_new_project("/path/to/project")  # True if <5 source files
```

New projects need discussion to understand intended structure.

### Starting Discussion
```bash
eri-rpg discuss myproject "improve the API"
```

Auto-generates questions based on goal type:
- **Add/Create**: "What specific behavior?", "Where to integrate?"
- **Fix**: "Expected behavior?", "Steps to reproduce?"
- **Refactor**: "What aspect to improve?", "Constraints?"

### Answering Questions
```bash
eri-rpg discuss-answer myproject "What endpoints?" "The /users endpoint"
```

Stores answer linked to question.

### Viewing Discussion
```bash
eri-rpg discuss-show myproject
```

Shows:
- Goal
- Questions with answers (✓) or unanswered (○)
- Roadmap if exists
- Next action suggestion

### Resolving Discussion
```bash
eri-rpg discuss-resolve myproject
```

Marks discussion complete. Goal now enriched with context.

## Roadmaps

### Adding Milestones
```bash
eri-rpg roadmap-add myproject "Phase 1: Research" "Understand current implementation"
eri-rpg roadmap-add myproject "Phase 2: Design" "Plan the changes"
eri-rpg roadmap-add myproject "Phase 3: Implement" "Write the code"
```

### Viewing Roadmap
```bash
eri-rpg roadmap myproject
```

Output:
```
════════════════════════════════════════
 ROADMAP: improve the API
════════════════════════════════════════

  ✓ Phase 1: Research
      Understand current implementation
      Spec: abc123
      Run: run-abc123
  ◐ Phase 2: Design [current]
      Plan the changes
  ○ Phase 3: Implement
      Write the code

Progress: 1/3 (33%)
Current: Phase 2 - Design
```

### Advancing Phases
```bash
eri-rpg roadmap-next myproject
```

Marks current phase done, moves to next.

### Editing Milestones
```bash
eri-rpg roadmap-edit myproject 1 "Research & Analysis" "Deep dive into codebase"
```

## Goal Enrichment

When generating spec, discussion context is included:

```
Goal: improve the API

Context from discussion:
- What endpoints should be improved?
  Answer: The /users endpoint
- What specific improvements?
  Answer: Add pagination and filtering
- Any constraints?
  Answer: Must be backwards compatible
```

This enriched goal produces better specs.
