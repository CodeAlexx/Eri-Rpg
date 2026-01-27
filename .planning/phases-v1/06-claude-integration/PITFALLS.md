# Phase 06: Pitfalls & Gotchas

## Hook Issues

### Hook Not Running
**Problem**: Edits not being blocked.

**Causes**:
- Hooks not configured in settings.json
- ERIRPG_ROOT not set
- Python path issues

**Solution**: `eri-rpg install-status` to diagnose.

### Hook Errors
**Problem**: Hook crashes, blocks all edits.

**Solution**: Check hook stderr. Fix Python errors. Reinstall if needed.

### Hook Bypass
**Problem**: User edits files outside Claude Code.

**Status**: Can't enforce outside Claude Code. User responsibility.

### Hook Latency
**Problem**: Hook adds delay to every edit.

**Mitigation**: Hook is fast (<100ms). Acceptable tradeoff.

## Installation Issues

### Permission Denied
**Problem**: Can't write to ~/.claude/settings.json.

**Solution**: Check permissions. May need sudo for global install.

### Existing Hooks
**Problem**: User has other hooks configured.

**Solution**: Installer merges, doesn't overwrite. Manual review if conflicts.

### Path Issues
**Problem**: ERIRPG_ROOT not found when hook runs.

**Solution**: Add to shell profile (.bashrc, .zshrc). Restart shell.

## Command Issues

### Command Not Found
**Problem**: /eri:execute doesn't work.

**Causes**:
- Commands not installed
- Wrong directory structure

**Solution**: `eri-rpg install` again.

### Command Errors
**Problem**: Slash command fails with Python error.

**Solution**: Check ERIRPG_ROOT. Ensure eri-rpg package importable.

## State Synchronization

### Stale Preflight State
**Problem**: Preflight state file exists but run was aborted.

**Solution**: `eri-rpg cleanup` clears stale state.

### Multiple Sessions
**Problem**: Two Claude Code sessions for same project.

**Status**: Not supported. One session per project.

### Context Compaction
**Problem**: State lost after compaction.

**Solution**: PreCompact hook saves state. Resume works after compaction.
