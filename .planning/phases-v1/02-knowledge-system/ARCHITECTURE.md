# Phase 02: Architecture

## Data Model

```
┌─────────────────────────────────────────────────────┐
│                 KnowledgeStore                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  learnings: Dict[str, StoredLearning]               │
│  discussions: Dict[str, Discussion]                  │
│  snapshots: Dict[str, Snapshot]                      │
│                                                      │
│  + add_learning(learning)                            │
│  + get_learning(path) -> StoredLearning             │
│  + remove_learning(path)                             │
│  + list_learnings() -> List[StoredLearning]         │
│                                                      │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│                 StoredLearning                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  module_path: str                                    │
│  learned_at: datetime                                │
│  summary: str                                        │
│  purpose: str                                        │
│  key_functions: Dict[str, str]                       │
│  key_params: Dict[str, str]                          │
│  gotchas: List[str]                                  │
│  dependencies: List[str]                             │
│  confidence: float                                   │
│  versions: List[LearningVersion]                     │
│  source_ref: Optional[CodeRef]                       │
│                                                      │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│                    CodeRef                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│  file_path: str                                      │
│  line_start: int                                     │
│  line_end: int                                       │
│  content_hash: str                                   │
│  git_commit: Optional[str]                           │
│                                                      │
│  + is_stale(project_path) -> bool                   │
│  + hydrate(project_path) -> str                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Storage Location

```
<project>/.eri-rpg/
├── knowledge.json       # All learnings
├── snapshots/           # File snapshots
│   ├── <hash1>.snap
│   └── <hash2>.snap
└── snapshot_index.json  # Maps files to snapshots
```

## Staleness Flow

```
recall(path)
    │
    ▼
load_learning(path)
    │
    ▼
is_stale(learning, project_path)
    │
    ├── current_hash = hash_file(path)
    ├── stored_hash = learning.source_ref.content_hash
    │
    ▼
current_hash != stored_hash → STALE
```
