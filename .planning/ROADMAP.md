# EriRPG Development Roadmap

## Milestone: v1 - Core Framework

### Phase 1: Core Infrastructure
- Goals:
  - [ ] Build project registry (add/remove/list projects)
  - [ ] Create code indexer (scan files, extract modules)
  - [ ] Implement dependency graph (track imports)
  - [ ] Add language parsers (Python, Rust, C)
- Dependencies: none
- Status: pending

### Phase 2: Knowledge System
- Goals:
  - [ ] Implement memory/learning storage
  - [ ] Add module recall functionality
  - [ ] Create pattern storage system
  - [ ] Build decision logging
- Dependencies: 1
- Status: pending

### Phase 3: Agent Workflow
- Goals:
  - [ ] Create agent API for Claude Code
  - [ ] Implement run state management
  - [ ] Add verification system
  - [ ] Build execution tracking
- Dependencies: 1, 2
- Status: pending

### Phase 4: Quick Fix Mode
- Goals:
  - [ ] Implement snapshot/restore for quick fixes
  - [ ] Add single-file edit tracking
  - [ ] Create lightweight workflow bypass
- Dependencies: 3
- Status: pending

### Phase 5: Discuss & Roadmap
- Goals:
  - [ ] Build goal clarification flow
  - [ ] Implement roadmap generation from spec
  - [ ] Add phase planning helpers
- Dependencies: 3
- Status: pending

### Phase 6: Claude Integration
- Goals:
  - [ ] Create CLI commands for Claude Code
  - [ ] Implement hook-based enforcement
  - [ ] Add skill file integration
  - [ ] Build session state management
- Dependencies: 3, 4, 5
- Status: pending

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
