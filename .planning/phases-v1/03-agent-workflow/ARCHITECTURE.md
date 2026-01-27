# Phase 03: Architecture

## Agent Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Claude                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Agent                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Public API                            │   │
│  │  from_goal() | from_spec() | resume()                   │   │
│  │  next_step() | start_step() | complete_step()           │   │
│  │  preflight() | edit_file() | write_file()               │   │
│  │  add_decision() | generate_summary()                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │     Spec      │  │     Plan      │  │     RunState      │   │
│  │               │  │               │  │                   │   │
│  │  goal         │  │  steps[]      │  │  log[]            │   │
│  │  steps[]      │  │  current      │  │  files_learned[]  │   │
│  │  must_haves   │  │  progress()   │  │  files_edited[]   │   │
│  │  constraints  │  │               │  │  decisions[]      │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supporting Services                           │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Preflight  │  │Verification │  │    Auto-Learner         │ │
│  │             │  │             │  │                         │ │
│  │  check()    │  │  run()      │  │  auto_learn()           │ │
│  │  snapshot() │  │  verify()   │  │  update_learning()      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Spec → Plan → Run

```
Spec (what)              Plan (how)              Run (execution)
────────────             ────────────            ────────────────
goal: "Add X"     →      steps:                  id: run-abc123
steps:                     - learn-target        started_at: ...
  - learn                  - implement           log: [...]
  - modify                 - verify              files_edited: [...]
  - verify                                       decisions: [...]
must_haves: [...]        current_step: 1        completed_at: ...
```

## Preflight Flow

```
agent.preflight(files, operation)
         │
         ▼
┌─────────────────────┐
│ Check learning      │──── Missing ──→ report.must_learn_first
│ for each file       │
└─────────────────────┘
         │ OK
         ▼
┌─────────────────────┐
│ Check staleness     │──── Stale ──→ Warning (not blocker)
└─────────────────────┘
         │ OK
         ▼
┌─────────────────────┐
│ Create snapshots    │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Register targets    │──→ agent._preflight_done = True
└─────────────────────┘
         │
         ▼
    report.ready = True
```

## Storage

```
<project>/.eri-rpg/
├── specs/
│   └── <spec_id>.yaml
├── runs/
│   └── <run_id>.json
├── knowledge.json
└── snapshots/
```
