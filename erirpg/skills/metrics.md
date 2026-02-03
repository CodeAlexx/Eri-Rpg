# /coder:metrics - Track Execution Metrics

Track and display time, tokens, cost, and success rates.

## CLI Integration

**First, call the CLI to manage metrics:**
```bash
# View all metrics
erirpg coder-metrics

# Record a metric
erirpg coder-metrics --record phase --data '{"phase_num": 2, "name": "Auth", "duration_minutes": 45}'
erirpg coder-metrics --record cost --data '{"tokens": 15000, "cost_usd": 0.12}'
```

This returns JSON with:
- For view: `sessions`, `phases`, `plans`, `costs` arrays, plus `totals`
- For record: `recorded`, `type`, `data`

Use this data to track and display execution metrics.

---

## Usage

```
/coder:metrics                     # Current project metrics
/coder:metrics --phase 2           # Metrics for phase 2
/coder:metrics --compare           # Compare phases
/coder:metrics --history           # Historical trends
/coder:metrics --export csv        # Export data
```

## Metrics Tracked

### Time Metrics
- Total project duration
- Time per phase
- Time per plan
- Average task duration

### Token Metrics
- Total tokens used
- Tokens per phase
- Tokens per operation type
- Input vs output ratio

### Cost Metrics
- Total API cost
- Cost per phase
- Cost by model tier
- Cost trends

### Quality Metrics
- Verification pass rate
- Rollback frequency
- Debug session count
- First-time success rate

## Execution Steps

### Step 1: Load Metrics Data

```python
def load_metrics(project):
    metrics_file = ".planning/metrics.json"

    if exists(metrics_file):
        return json.load(metrics_file)

    # Reconstruct from artifacts
    return {
        "project": project_metrics_from_state(),
        "phases": [phase_metrics(p) for p in phases],
        "operations": aggregate_operations(),
        "history": build_history()
    }
```

### Step 2: Display Dashboard

```markdown
## Project Metrics: my-app

**Period:** 2026-01-28 to 2026-01-30
**Status:** 80% complete

### Overview
```
┌─────────────────────────────────────────────────┐
│  Total Time    │  Tokens Used   │  Total Cost   │
│    12h 30m     │    285,000     │    $2.28      │
├─────────────────────────────────────────────────┤
│  Phases: 4/5   │  Plans: 14     │  Tasks: 42    │
│  Success: 93%  │  Rollbacks: 1  │  Debugs: 2    │
└─────────────────────────────────────────────────┘
```

### Time Breakdown
```
Phase 1 ████░░░░░░░░░░ 1h 30m (12%)
Phase 2 ██████████░░░░ 3h 00m (24%)
Phase 3 ████████░░░░░░ 2h 15m (18%)
Phase 4 ██████░░░░░░░░ 1h 30m (12%)
Init    ███████████████ 4h 15m (34%)
```

### Token Usage
| Category | Tokens | % |
|----------|--------|---|
| Execution | 120,000 | 42% |
| Planning | 80,000 | 28% |
| Research | 50,000 | 18% |
| Verification | 25,000 | 9% |
| Debug | 10,000 | 3% |

### Cost Breakdown
| Model | Tokens | Cost | % |
|-------|--------|------|---|
| Sonnet | 250,000 | $2.00 | 88% |
| Haiku | 35,000 | $0.03 | 1% |
| Context | - | $0.25 | 11% |

### Quality Metrics
| Metric | Value | Trend |
|--------|-------|-------|
| First-time verification | 75% | ↑ |
| Rollback rate | 7% | ↓ |
| Debug sessions | 2 | - |
| Avg fix time | 15 min | ↓ |
```

### Step 3: Phase Comparison

```markdown
## Phase Comparison

| Phase | Duration | Tokens | Cost | Tasks | Success |
|-------|----------|--------|------|-------|---------|
| 1 | 1h 30m | 30,000 | $0.24 | 6 | 100% |
| 2 | 3h 00m | 60,000 | $0.48 | 12 | 83% |
| 3 | 2h 15m | 45,000 | $0.36 | 9 | 100% |
| 4 | 1h 30m | 25,000 | $0.20 | 6 | 100% |

### Efficiency Metrics
| Phase | Tokens/Task | Time/Task | Cost/Task |
|-------|-------------|-----------|-----------|
| 1 | 5,000 | 15 min | $0.04 |
| 2 | 5,000 | 15 min | $0.04 |
| 3 | 5,000 | 15 min | $0.04 |
| 4 | 4,167 | 15 min | $0.03 |

### Complexity Indicators
| Phase | Files | Lines | Complexity |
|-------|-------|-------|------------|
| 1 | 15 | 520 | Low |
| 2 | 28 | 1,200 | High |
| 3 | 22 | 890 | Medium |
| 4 | 12 | 450 | Low |
```

### Step 4: Historical Trends

```markdown
## Historical Trends

### Token Efficiency Over Time
```
Day 1: ████████████████████ 100K tokens (inefficient, learning)
Day 2: ████████████░░░░░░░░ 120K tokens (65% of Day 1 rate)
Day 3: ████████░░░░░░░░░░░░  65K tokens (40% improvement)
```

### Cost Trend
```
Day 1: $0.80 (33 tasks)
Day 2: $0.96 (40 tasks)
Day 3: $0.52 (30 tasks) ← most efficient
```

### Success Rate Trend
```
Day 1: ████████░░ 80%
Day 2: ██████████ 100%
Day 3: █████████░ 95%
```

### Key Observations
1. **Learning curve:** Day 1 used 50% more tokens per task
2. **Peak efficiency:** Day 3 achieved best cost/task ratio
3. **Quality improved:** Fewer rollbacks after Day 1
```

## Metrics Collection

### Automatic Collection
```python
def track_operation(operation_type, start_time, tokens_used):
    metrics = load_metrics()

    metrics["operations"].append({
        "type": operation_type,
        "timestamp": start_time,
        "duration": now() - start_time,
        "tokens": tokens_used,
        "cost": calculate_cost(tokens_used),
        "phase": current_phase(),
        "plan": current_plan()
    })

    save_metrics(metrics)
```

### Operation Types
| Type | Description |
|------|-------------|
| `research` | Research agent execution |
| `planning` | Plan creation/checking |
| `execution` | Plan execution |
| `verification` | Phase verification |
| `debug` | Debug sessions |
| `quick` | Quick task execution |

## Export Formats

### CSV Export
```
/coder:metrics --export csv
```
```csv
timestamp,operation,phase,plan,duration_min,tokens,cost_usd
2026-01-28T10:00:00Z,research,init,,45,50000,0.40
2026-01-28T11:00:00Z,planning,1,01-01,15,8000,0.06
...
```

### JSON Export
```
/coder:metrics --export json
```

### Markdown Export
```
/coder:metrics --export md
```
Creates `.planning/METRICS.md`

## Metrics Storage

Location: `.planning/metrics.json`

```json
{
  "project": {
    "name": "my-app",
    "started": "2026-01-28T10:00:00Z",
    "total_tokens": 285000,
    "total_cost_usd": 2.28
  },
  "phases": [...],
  "operations": [...],
  "daily": {...}
}
```

## Budget Tracking

### Set Budget
```python
# In config.json
{
  "budget": {
    "max_tokens_per_phase": 100000,
    "max_cost_per_day": 5.00,
    "warn_at_percent": 80
  }
}
```

### Budget Alerts
```markdown
## Budget Alert

⚠️ Phase 2 approaching token limit:
- Used: 85,000 / 100,000 tokens (85%)
- Remaining: 15,000 tokens

Options:
1. Continue (may exceed)
2. Pause and review
3. Switch to budget model (Haiku)
```

## Integration Points

- Stores: .planning/metrics.json
- Reads: SUMMARY files, git log, operation history
- Exports: CSV, JSON, Markdown
- Alerts: Budget thresholds
- Displays: Dashboard, comparisons, trends
