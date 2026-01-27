# Phase 05: Architecture

## Data Model

```
┌─────────────────────────────────────────────────────────────┐
│                     KnowledgeStore                           │
│                                                              │
│   discussions: Dict[str, Discussion]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Discussion                              │
├─────────────────────────────────────────────────────────────┤
│  id: str                                                     │
│  goal: str                                                   │
│  project: str                                                │
│  questions: List[str]                                        │
│  answers: Dict[str, str]                                     │
│  resolved: bool                                              │
│  created_at: datetime                                        │
│  resolved_at: Optional[datetime]                             │
│  roadmap: Optional[Roadmap]  ◄────────────────────────────┐ │
└─────────────────────────────────────────────────────────────┘
                                                               │
                           ┌───────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       Roadmap                                │
├─────────────────────────────────────────────────────────────┤
│  id: str                                                     │
│  goal: str                                                   │
│  milestones: List[Milestone]                                 │
│  created_at: datetime                                        │
│                                                              │
│  + add_milestone(name, desc) -> Milestone                   │
│  + current_milestone() -> Optional[Milestone]               │
│  + advance() -> Optional[Milestone]                         │
│  + progress() -> str  # "2/5"                               │
│  + is_complete() -> bool                                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Milestone                               │
├─────────────────────────────────────────────────────────────┤
│  id: str                                                     │
│  name: str                                                   │
│  description: str                                            │
│  done: bool                                                  │
│  spec_id: Optional[str]   # Links to spec for this phase    │
│  run_id: Optional[str]    # Links to run for this phase     │
│  completed_at: Optional[datetime]                            │
└─────────────────────────────────────────────────────────────┘
```

## Discussion Flow

```
needs_discussion(goal, project_path)
         │
         ├── is_vague_goal(goal)?
         ├── is_new_project(project_path)?
         │
         ▼
    (needs, reason)
         │
         ▼ if needs
┌─────────────────┐
│ start_discussion│
│                 │
│ • Generate Qs   │
│ • Create obj    │
│ • Store in KS   │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ answer_question │──── (repeat for each Q)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ add_milestone   │──── (optional, repeat)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│resolve_discussion│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  enrich_goal    │──→ Enhanced goal string for spec
└─────────────────┘
```

## Roadmap Lifecycle

```
create_roadmap(goal)
       │
       ▼
add_milestone("Phase 1", "...")
add_milestone("Phase 2", "...")
add_milestone("Phase 3", "...")
       │
       ▼
┌──────────────────────────────────────┐
│ Execute Phase 1                       │
│   goal-plan → goal-run → complete    │
│   milestone.spec_id = spec.id        │
│   milestone.run_id = run.id          │
└──────────────────────────────────────┘
       │
       ▼
advance_roadmap()  # Phase 1 → done, Phase 2 → current
       │
       ▼
┌──────────────────────────────────────┐
│ Execute Phase 2...                    │
└──────────────────────────────────────┘
       │
       ▼
advance_roadmap()  # Phase 2 → done, Phase 3 → current
       │
       ... repeat ...
       │
       ▼
roadmap.is_complete() == True
```
