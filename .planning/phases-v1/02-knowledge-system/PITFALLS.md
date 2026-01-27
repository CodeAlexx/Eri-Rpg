# Phase 02: Pitfalls & Gotchas

## Storage Issues

### Large Learnings
**Problem**: Very detailed learnings can get huge (>10KB).

**Mitigation**: 
- Keep summaries concise
- Key functions should be brief
- Use CodeRefs for actual code snippets

### Concurrent Access
**Problem**: Multiple processes writing to knowledge.json.

**Status**: Not handled. Single-writer assumption.

## Staleness Issues

### Hash Collisions
**Problem**: Two different files could have same hash (extremely unlikely).

**Status**: Acceptable risk. SHA-256 collisions are practically impossible.

### Whitespace Changes
**Problem**: Formatting-only changes trigger staleness.

**Status**: Known issue. Could normalize whitespace before hashing, but not implemented.

### Git Checkout
**Problem**: Checking out old commit makes all learnings "stale".

**Mitigation**: Staleness is a warning, not a blocker. User decides.

## Learning Quality

### Garbage In, Garbage Out
**Problem**: User can store incorrect or incomplete learnings.

**Mitigation**: 
- Confidence field (0.0-1.0)
- Version history for corrections
- Relearn command to update

### Outdated Learnings
**Problem**: Learning says "function X does Y" but code changed.

**Mitigation**: Staleness detection warns user. Relearn to update.

## Rollback Issues

### Snapshot Size
**Problem**: Storing full file snapshots uses disk space.

**Mitigation**: 
- Only snapshot before edits (not every read)
- Prune old snapshots with cleanup command

### Missing Snapshots
**Problem**: Can't rollback if no snapshot exists.

**Status**: Rollback returns error. User must have done preflight to have snapshot.
