# Phase 03: Pitfalls & Gotchas

## Preflight Issues

### Forgetting Preflight
**Problem**: Agent tries to edit without preflight → blocked.

**Solution**: Error message tells user exactly what to do.

### Wrong Files in Preflight
**Problem**: Preflighted `file1.py` but need to edit `file2.py`.

**Solution**: Re-run preflight with all intended files.

### Stale Preflight
**Problem**: Preflight done long ago, file changed since.

**Status**: Preflight state persists until step complete. Could add timeout.

## Edit Tracking Issues

### Content Mismatch
**Problem**: `old_content` doesn't match file content.

**Solution**: Edit fails with clear error. User must use exact content.

### Partial Edits
**Problem**: Edit succeeds but run crashes before tracking.

**Mitigation**: Snapshot exists for rollback. But tracking may be incomplete.

## Verification Issues

### Test Failures
**Problem**: Tests fail after edit.

**Solution**: 
- Run shown verification output
- Rollback available
- Step not marked complete

### must_haves False Positives
**Problem**: Grep pattern matches unintended code.

**Mitigation**: Use specific patterns. Review results.

### Slow Tests
**Problem**: Large test suite takes minutes.

**Mitigation**: Configure specific test paths in spec verification.

## Run State Issues

### Corrupted State
**Problem**: JSON file corrupted (disk issue, crash).

**Solution**: Keep backups. State file is small, can regenerate from git.

### Orphan Runs
**Problem**: Run started but never completed.

**Solution**: `cleanup --prune` removes old runs.

### Resume After Code Change
**Problem**: Code changed outside EriRPG during paused run.

**Status**: Known issue. Run may have stale understanding. Consider fresh run.
