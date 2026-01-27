# EriRPG Development Roadmap

## Completed Phases (v1.0 - v2.0)

| Phase | Name | Status |
|-------|------|--------|
| 01 | Core Infrastructure | ✅ Complete |
| 02 | Knowledge System | ✅ Complete |
| 03 | Agent Workflow | ✅ Complete |
| 04 | Quick Fix Mode | ✅ Complete |
| 05 | Discuss & Roadmap | ✅ Complete |
| 06 | Claude Integration | ✅ Complete |

## Planned Features (v2.1+)

### Language Support
- [ ] **Dart parser** - For Flutter/Dart projects
- [ ] **Go parser** - For Go projects
- [ ] **TypeScript parser** - Improve beyond regex
- [ ] **Java parser** - For Android/backend

### Performance
- [ ] **Incremental indexing** - Only re-index changed files
- [ ] **SQLite backend** - For large projects (>10k files)
- [ ] **Parallel parsing** - Multi-threaded indexing

### Workflow
- [ ] **Wave execution** - Parallel step execution
- [ ] **Metrics tracking** - Time, tokens, success rate
- [ ] **Integration audit** - Verify transplants work correctly
- [ ] **Batch learning** - Learn entire directories

### Claude Code
- [ ] **MCP server** - Native protocol integration
- [ ] **Better error messages** - More actionable guidance
- [ ] **Auto-resume** - Automatically resume after compaction

### Quality
- [ ] **Test coverage** - Improve from current ~70%
- [ ] **Documentation** - API docs, tutorials
- [ ] **CI/CD** - Automated testing and releases

## Version Plan

### v2.1 (Next)
- Dart parser
- Incremental indexing
- Batch learning

### v2.2
- Go parser  
- Wave execution
- Metrics tracking

### v3.0
- MCP server
- SQLite backend
- TypeScript/Java parsers

## Contributing

See main README for contribution guidelines.
Priorities are marked with issue labels on GitHub.
