# Phase 01: Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                    CLI Layer                         │
│                   (cli.py)                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Registry   │  │   Indexer   │  │    Graph    │ │
│  │             │  │             │  │             │ │
│  │ - add()     │  │ - index()   │  │ - build()   │ │
│  │ - remove()  │  │ - scan()    │  │ - search()  │ │
│  │ - list()    │  │ - parse()   │  │ - impact()  │ │
│  │ - get()     │  │             │  │ - deps()    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │        │
│         v                v                v        │
│  ┌─────────────────────────────────────────────┐   │
│  │              Storage Layer                   │   │
│  │                                              │   │
│  │  ~/.eri-rpg/registry.json                   │   │
│  │  <project>/.eri-rpg/index.json              │   │
│  │  <project>/.eri-rpg/graph.json              │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │              Parsers                         │   │
│  │                                              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ Python  │ │  Rust   │ │    C    │       │   │
│  │  │  (AST)  │ │ (regex) │ │ (regex) │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Data Flow

### Project Registration
```
User → CLI add → Registry.add() → ~/.eri-rpg/registry.json
```

### Indexing
```
User → CLI index → Indexer.index() → Parser.parse() → Graph.build() 
                                                    ↓
                                        .eri-rpg/index.json
                                        .eri-rpg/graph.json
```

### Search
```
User → CLI find → Graph.search() → ranked results
```

## Key Data Structures

### Registry Entry
```python
{
    "name": "myproject",
    "path": "/absolute/path",
    "language": "python",
    "indexed_at": "2026-01-26T10:00:00",
    "file_count": 150
}
```

### Module Entry
```python
{
    "path": "src/utils.py",
    "name": "utils",
    "docstring": "Utility functions",
    "functions": ["helper", "validate"],
    "classes": ["Config"],
    "imports": ["os", "json"],
    "hash": "abc123..."
}
```

### Graph Edge
```python
{
    "from": "src/main.py",
    "to": "src/utils.py",
    "type": "import"  # or "call"
}
```

## File Locations

| Data | Location |
|------|----------|
| Global registry | `~/.eri-rpg/registry.json` |
| Project index | `<project>/.eri-rpg/index.json` |
| Dependency graph | `<project>/.eri-rpg/graph.json` |
