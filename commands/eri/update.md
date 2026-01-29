# /eri:update - Update Session Status Files

Update STATE.md, ROADMAP.md, and TASKS.md based on current project state.

## Usage

```bash
/eri:update [project]                    # Auto-detect from files
/eri:update [project] --phase 4          # Mark phase 4 complete
/eri:update [project] --activity "..."   # Set last activity description
```

## Arguments
- `$ARGUMENTS` - Project name and options

## Execution

1. **Find project**: Use argument or detect from current directory
2. **Run update command**:
   ```bash
   python3 -m erirpg.cli goal-update <project> [--phase N] [--activity "..."]
   ```
3. **Show results**: Display updated progress

## What It Updates

| File | Updated Fields |
|------|----------------|
| STATE.md | Progress bar, phase status, last activity |
| ROADMAP.md | Deliverable checkboxes, phase status |
| TASKS.md | Move tasks to Completed, update Active |

## Auto-Detection

The command auto-detects phase completion by checking if deliverable files exist:
- `requirements.txt` exists → Phase 1 (Setup) complete
- `main.py` exists → Phase 2 (Backend) complete
- `static/index.html` exists → Phase 3 (Frontend) complete

For phases without file deliverables (Integration, Testing), use `--phase N`.

## Example

After building backend and frontend:
```bash
/eri:update myproject --phase 5 --activity "Manual testing on mobile complete"
```
