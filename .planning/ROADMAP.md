# EriRPG Development Roadmap

## Milestone: v1 - Core Framework ✅ COMPLETE

### Phase 1: Core Infrastructure ✅
- Goals:
  - [x] Build project registry (registry.py - 8KB)
  - [x] Create code indexer (indexer.py - 14KB)
  - [x] Implement dependency graph (graph.py - 17KB)
  - [x] Add language parsers (parsers/ - Python, Rust, C)
- Status: complete

### Phase 2: Knowledge System ✅
- Goals:
  - [x] Implement memory/learning storage (memory.py - 73KB)
  - [x] Add module recall functionality
  - [x] Create pattern storage system
  - [x] Build decision logging
- Status: complete

### Phase 3: Agent Workflow ✅
- Goals:
  - [x] Create agent API for Claude Code (agent/)
  - [x] Implement run state management (runs.py - 13KB)
  - [x] Add verification system (verification.py - 37KB)
  - [x] Build execution tracking
- Status: complete

### Phase 4: Quick Fix Mode ✅
- Goals:
  - [x] Implement snapshot/restore for quick fixes (quick.py - 18KB)
  - [x] Add single-file edit tracking
  - [x] Create lightweight workflow bypass
- Status: complete

### Phase 5: Discuss & Roadmap ✅
- Goals:
  - [x] Build goal clarification flow (discuss.py - 33KB)
  - [x] Implement roadmap generation from spec (planner.py - 46KB)
  - [x] Add phase planning helpers
- Status: complete

### Phase 6: Claude Integration ✅
- Goals:
  - [x] Create CLI commands for Claude Code (cli_commands/)
  - [x] Implement hook-based enforcement (hooks/)
  - [x] Add skill file integration (skills/)
  - [x] Build session state management
- Status: complete

---

## Future Features (v2.0+)

### Language Support
- Dart parser - For Flutter/Dart projects
- Go parser - For Go projects
- TypeScript parser - Improve beyond regex
- Java parser - For Android/backend

### Performance
- Incremental indexing - Only re-index changed files
- SQLite backend - For large projects (>10k files)
- Parallel parsing - Multi-threaded indexing

### Quality
- Test coverage - Improve from current ~70%
- Documentation - API docs, tutorials
- CI/CD - Automated testing and releases
