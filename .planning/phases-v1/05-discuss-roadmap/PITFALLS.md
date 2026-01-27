# Phase 05: Pitfalls & Gotchas

## Discussion Issues

### Over-Detection
**Problem**: Specific goals flagged as vague.

**Mitigation**: Detection is conservative. Short goals or vague words trigger.
User can skip: `--skip` flag or proceed anyway.

### Incomplete Answers
**Problem**: User gives vague answers to questions.

**Status**: No enforcement. Garbage in, garbage out.

### Abandoned Discussions
**Problem**: Started discussion, never resolved.

**Solution**: `discuss-clear` to remove. Or just start fresh.

### Multiple Discussions
**Problem**: Want to discuss multiple goals.

**Status**: One active discussion per project. Resolve first, then start new.

## Roadmap Issues

### Too Many Phases
**Problem**: 20-phase roadmap is overwhelming.

**Recommendation**: 3-5 phases max. Can always add more later.

### Phase Scope Creep
**Problem**: Phase 1 turns into entire project.

**Solution**: Keep phases focused. If too big, split into sub-phases.

### Skipping Phases
**Problem**: Want to skip Phase 2, go directly to Phase 3.

**Status**: Not supported. Phases are sequential. Mark Phase 2 done to advance.

### Changing Roadmap Mid-Project
**Problem**: Realized Phase 3 should come before Phase 2.

**Solution**: Edit phase descriptions, or clear and rebuild roadmap.

## Integration Issues

### Discussion Without Roadmap
**Problem**: Discussion resolved but no roadmap added.

**Status**: OK. Roadmap is optional. Goal still enriched.

### Roadmap Without Discussion
**Problem**: Want roadmap but goal isn't vague.

**Solution**: Use `--discuss` flag to force discussion mode.

### Spec Without Discussion
**Problem**: Went straight to `goal-plan` without discuss.

**Status**: Works fine. Discussion is optional for specific goals.
