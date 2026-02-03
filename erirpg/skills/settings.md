# /coder:settings - Configure Workflow Preferences

View and modify eri-coder workflow configuration.

## CLI Integration

**First, call the CLI to manage settings:**
```bash
# View current settings
erirpg coder-settings

# Set a single value
erirpg coder-settings mode yolo

# Reset to defaults
erirpg coder-settings --reset
```

This returns JSON with:
- `settings`: Current settings
- `defaults`: Default values
- For set operations: `key`, `old_value`, `new_value`, `saved`

Use this data in the workflow below.

---

## Usage

```
/coder:settings                    # Show current settings
/coder:settings --edit             # Interactive configuration
/coder:settings mode yolo          # Set specific setting
/coder:settings reset              # Reset to defaults
```

## Settings File

Location: `.planning/config.json`

```json
{
  "mode": "yolo",
  "depth": "standard",
  "parallelization": true,
  "commit_tracking": true,
  "model_profile": "balanced",
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true
  },
  "notifications": {
    "checkpoint_sound": false,
    "phase_complete": true
  }
}
```

## Execution Steps

### Step 1: Load Current Settings

Read `.planning/config.json` or use defaults:

```json
{
  "mode": "interactive",
  "depth": "standard",
  "parallelization": true,
  "commit_tracking": true,
  "model_profile": "balanced",
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true
  }
}
```

### Step 2: Display Settings

**Show current (default):**
```markdown
# eri-coder Settings

## Workflow Mode
**Current:** `yolo`
- `yolo` - Build without stopping for approval
- `interactive` - Ask for approval at each step

## Depth
**Current:** `standard`
- `quick` - 3-5 phases, 1-3 plans each
- `standard` - 5-8 phases, 3-5 plans each
- `comprehensive` - 8-12 phases, 5-10 plans each

## Parallelization
**Current:** `enabled`
- Execute plans in parallel within waves
- Faster but uses more resources

## Git Tracking
**Current:** `enabled`
- Atomic commits per task
- Automatic commit messages

## Model Profile
**Current:** `balanced`

| Agent | quality | balanced | budget |
|-------|---------|----------|--------|
| Researcher | opus | sonnet | haiku |
| Roadmapper | opus | sonnet | sonnet |
| Planner | opus | sonnet | sonnet |
| Executor | opus | sonnet | sonnet |
| Verifier | sonnet | sonnet | haiku |

## Workflow Agents
| Agent | Status |
|-------|--------|
| Research | ✅ Enabled |
| Plan Checker | ✅ Enabled |
| Verifier | ✅ Enabled |

---

**Edit:** `/coder:settings --edit`
**Set single:** `/coder:settings mode yolo`
**Reset:** `/coder:settings reset`
```

### Step 3: Interactive Edit (--edit)

```markdown
## Configure eri-coder

### 1. Workflow Mode
How should Claude proceed during execution?

- **[Y] YOLO** - Build continuously without approval stops
- **[I] Interactive** - Pause for approval at each major step

Select (Y/I):

### 2. Project Depth
How thorough should planning be?

- **[Q] Quick** - Fast iteration, minimal phases (3-5)
- **[S] Standard** - Balanced approach (5-8 phases)
- **[C] Comprehensive** - Thorough planning (8-12 phases)

Select (Q/S/C):

### 3. Parallelization
Execute plans in parallel when possible?

- **[Y] Yes** - Faster execution, more resources
- **[N] No** - Sequential execution, predictable

Select (Y/N):

### 4. Model Profile
Which model tier for agents?

- **[Q] Quality** - Best results, higher cost (Opus)
- **[B] Balanced** - Good results, moderate cost (Sonnet)
- **[U] Budget** - Fast iteration, lower cost (Haiku/Sonnet mix)

Select (Q/B/U):

### 5. Workflow Agents
Toggle optional workflow agents:

- **[R] Research** - Domain research before roadmap
- **[P] Plan Checker** - Verify plans before execution
- **[V] Verifier** - Automated verification after phases

Currently: R:✅ P:✅ V:✅
Toggle (R/P/V) or [Enter] to keep:

---

## Summary

| Setting | Value |
|---------|-------|
| Mode | yolo |
| Depth | standard |
| Parallelization | enabled |
| Model Profile | balanced |
| Research | enabled |
| Plan Checker | enabled |
| Verifier | enabled |

Save these settings? (yes/no)
```

### Step 4: Set Single Setting

`/coder:settings mode yolo`:
```markdown
## Setting Updated

**mode:** `interactive` → `yolo`

Updated `.planning/config.json`
```

Valid settings and values:

| Setting | Valid Values |
|---------|--------------|
| `mode` | `yolo`, `interactive` |
| `depth` | `quick`, `standard`, `comprehensive` |
| `parallelization` | `true`, `false` |
| `commit_tracking` | `true`, `false` |
| `model_profile` | `quality`, `balanced`, `budget` |
| `research` | `true`, `false` |
| `plan_check` | `true`, `false` |
| `verifier` | `true`, `false` |

### Step 5: Reset to Defaults

`/coder:settings reset`:
```markdown
## Reset Settings

This will reset all settings to defaults:
- mode: interactive
- depth: standard
- parallelization: true
- commit_tracking: true
- model_profile: balanced
- All workflow agents: enabled

Confirm reset? (yes/no)
```

## Settings Effects

### Mode Effects
| Mode | Behavior |
|------|----------|
| `yolo` | Skip approval prompts, continuous execution |
| `interactive` | Pause for user approval at decision points |

### Depth Effects
| Depth | Phases | Plans/Phase | Research |
|-------|--------|-------------|----------|
| `quick` | 3-5 | 1-3 | Abbreviated |
| `standard` | 5-8 | 3-5 | Full |
| `comprehensive` | 8-12 | 5-10 | Extensive |

### Model Profile Effects
| Profile | Token Cost | Quality | Speed |
|---------|------------|---------|-------|
| `quality` | High | Best | Slow |
| `balanced` | Medium | Good | Medium |
| `budget` | Low | Adequate | Fast |

## Project-Level vs Global

Settings in `.planning/config.json` are **project-level**.

For global defaults, create:
`~/.eri-rpg/config.json`

Project settings override global.

## Validation

On save, validate:
- JSON syntax valid
- All values within allowed options
- No conflicting settings

```markdown
## Validation Error

Invalid value for 'depth': 'extreme'

Allowed values: quick, standard, comprehensive

Setting not changed.
```
