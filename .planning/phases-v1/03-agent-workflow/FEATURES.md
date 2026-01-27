# Phase 03: Features

## Specs

### Spec Structure
```yaml
id: abc123
goal: "Add caching to API"
project: myproject
steps:
  - id: learn
    action: learn
    targets: [api/handlers.py]
  - id: implement
    action: modify
    targets: [api/handlers.py]
    depends_on: [learn]
  - id: verify
    action: verify
must_haves:
  truths:
    - "Responses cached for 5 minutes"
  artifacts:
    - path: api/cache.py
      exports: [CacheMiddleware]
  key_links:
    - from_file: api/handlers.py
      to_file: api/cache.py
      pattern: "from.*cache.*import"
verification:
  - pytest
constraints:
  - "No external dependencies"
```

### Generate from Goal
```bash
eri-rpg goal-plan myproject "Add user authentication"
```
Auto-generates spec with learn/implement/verify steps.

## Preflight

### Mandatory Check
```python
report = agent.preflight(['src/file.py'], 'modify')
```
Returns PreflightReport with:
- `ready`: bool
- `blockers`: list of issues
- `must_learn_first`: files needing learning
- `impact_zone`: affected files

### What Preflight Does
1. Check learning exists for each target
2. Check staleness of learnings
3. Create file snapshots for rollback
4. Register target files for edit tracking

## File Operations

### Edit File
```python
agent.edit_file(
    file_path='src/module.py',
    old_content='def old():',
    new_content='def new():',
    description='Renamed function'
)
```
- Requires active preflight
- File must be in preflight targets
- Change tracked in run state

### Write New File
```python
agent.write_file(
    file_path='src/new.py',
    content='# New module',
    description='Created module'
)
```

## Step Lifecycle

```
next_step() → start_step() → preflight() → edit_file() → complete_step()
                                                              │
                                                              ▼
                                                        auto-learn
                                                        verification
                                                        git commit
```

## Verification

### must_haves Verification
```python
passed, results = spec.verify_must_haves(project_path)
```
Checks:
- truths: grep for patterns in codebase
- artifacts: file exists with expected exports
- key_links: import patterns between files

### Test Verification
```bash
# Auto-runs on step completion if configured
pytest tests/
npm test
```
