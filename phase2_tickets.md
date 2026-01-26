# Phase 2 Tickets: Durable Memory

## P2-001: Add dedicated knowledge store
Goal
- Persist learnings independently of graph.json.

Changes
- Add `erirpg/memory.py` with load/save APIs.
- Store learnings in `.eri-rpg/knowledge.json`.
- Update CLI to read/write from the new store.

Acceptance Criteria
- Learnings persist across reindex.
- Knowledge can be loaded without graph.json.

Dependencies
- Phase 1 complete.

## P2-002: Add staleness metadata
Goal
- Detect when learnings are out of date.

Changes
- Add `source_hash` and `source_mtime` to Learning.
- Compute metadata on `learn`.
- Update `recall` and context generation to warn when stale.

Acceptance Criteria
- Learnings show stale warnings when source changes.
- Fresh learnings do not warn.

Dependencies
- P2-001.

## P2-003: Context behavior for stale learnings
Goal
- Avoid using stale knowledge silently.

Changes
- If stale, include source code instead of learning (or annotate clearly).
- Provide a CLI flag to force use of stale learnings.

Acceptance Criteria
- Stale learnings are clearly marked in context output.

Dependencies
- P2-002.

## P2-004: Migrate embedded knowledge
Goal
- Preserve any knowledge stored in graph.json.

Changes
- On load, detect embedded knowledge and migrate to knowledge.json.
- Write a one-time migration notice.

Acceptance Criteria
- Existing learnings are not lost after migration.

Dependencies
- P2-001.

## P2-005: Tests for durability and staleness
Goal
- Prevent regressions in memory persistence.

Changes
- Add tests for persistence across reindex.
- Add tests for staleness detection.

Acceptance Criteria
- Tests fail without fixes and pass after implementation.

Dependencies
- P2-001, P2-002.
