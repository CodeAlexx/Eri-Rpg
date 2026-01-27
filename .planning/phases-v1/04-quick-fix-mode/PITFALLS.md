# Phase 04: Pitfalls & Gotchas

## Scope Creep

### "Just one more file"
**Problem**: User wants to edit second file during quick fix.

**Solution**: Blocked by design. Complete current, start new, or use full workflow.

### Large Changes
**Problem**: "Quick fix" turns into major refactor.

**Solution**: Cancel and use spec-driven workflow. Quick fix is for small changes only.

## State Issues

### Stale Quick Fix
**Problem**: Started quick fix, forgot about it, came back days later.

**Solution**: `quick-status` shows age. Consider `quick-cancel` and fresh start.

### Crash During Edit
**Problem**: Editor crashes mid-edit, file in weird state.

**Solution**: `quick-cancel` restores from snapshot. Or `quick-done` commits current state.

### Multiple Projects
**Problem**: Confusing which project has active quick fix.

**Solution**: `quick-status` requires project name. One quick fix per project.

## Git Issues

### Uncommitted Changes
**Problem**: Other uncommitted changes exist when starting quick fix.

**Status**: Quick fix commits only its file. Other changes remain staged/unstaged.

### Branch Mismatch
**Problem**: Started on branch A, completing on branch B.

**Status**: Git handles this. Commit goes to current branch.

## Hook Issues

### Hook Not Installed
**Problem**: Quick fix started but hook not blocking other edits.

**Solution**: `eri-rpg install` to set up hooks.

### Hook Bypassed
**Problem**: Direct file edit outside Claude Code.

**Status**: Can't enforce outside Claude Code. User responsibility.
