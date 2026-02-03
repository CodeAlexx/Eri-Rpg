# /coder:cost - Estimate Tokens and Cost

Estimate token usage and API cost before executing commands.

## CLI Integration

**First, call the CLI to get cost estimate:**
```bash
# Estimate for specific operation
erirpg coder-cost plan-phase --phase 2
erirpg coder-cost execute-phase --phase 2
erirpg coder-cost new-project

# Detailed breakdown
erirpg coder-cost execute-phase --phase 2 --detailed

# Compare with local model
erirpg coder-cost execute-phase --phase 2 --compare local
```

This returns JSON with:
- `operation`: The operation being estimated
- `tokens`: Total estimated tokens
- `input_tokens`, `output_tokens`: Breakdown
- `model`: Model being used
- `cost_usd`: Estimated cost in USD
- `cost_breakdown`: {input, output} costs
- `comparison`: Cost across all models (opus, sonnet, haiku)

Use this data to render the cost estimate display.

---

## Usage

```
/coder:cost plan-phase 2           # Cost to plan phase 2
/coder:cost execute-phase 2        # Cost to execute phase 2
/coder:cost new-project            # Cost for full project init
/coder:cost --detailed             # Breakdown by agent
/coder:cost --compare local        # Compare with local model
```

## Token Estimation Model

### Base Costs by Operation

```python
TOKEN_ESTIMATES = {
    "new-project": {
        "base": 50000,
        "per_question": 2000,
        "research": 40000,  # 4 agents × 10K
        "roadmap": 15000,
    },
    "plan-phase": {
        "base": 8000,
        "per_plan": 5000,
        "plan_check": 4000,
    },
    "execute-phase": {
        "base": 5000,
        "per_task": 3000,
        "per_file": 500,
        "verification": 6000,
    },
    "verify-work": {
        "base": 4000,
        "per_check": 1000,
        "debug": 8000,  # If failures
    }
}
```

### Cost Calculation

```python
def estimate_cost(operation, context):
    # Base tokens
    tokens = TOKEN_ESTIMATES[operation]["base"]

    # Context-dependent additions
    if operation == "execute-phase":
        phase = load_phase(context.phase)
        tokens += len(phase.plans) * TOKEN_ESTIMATES[operation]["per_task"]
        tokens += sum(len(p.files) for p in phase.plans) * 500

    # Model pricing (per 1M tokens)
    PRICING = {
        "opus": {"input": 15.00, "output": 75.00},
        "sonnet": {"input": 3.00, "output": 15.00},
        "haiku": {"input": 0.25, "output": 1.25},
    }

    # Calculate cost
    model = context.model_profile or "sonnet"
    input_cost = (tokens * 0.6) / 1_000_000 * PRICING[model]["input"]
    output_cost = (tokens * 0.4) / 1_000_000 * PRICING[model]["output"]

    return {
        "tokens": tokens,
        "input_tokens": int(tokens * 0.6),
        "output_tokens": int(tokens * 0.4),
        "cost_usd": input_cost + output_cost,
        "model": model
    }
```

## Output Format

### Standard Output

```markdown
## Cost Estimate: execute-phase 2

**Phase:** 2 - User Authentication
**Plans:** 3
**Tasks:** 8
**Files:** 12

### Token Estimate
| Category | Tokens |
|----------|--------|
| Base overhead | 5,000 |
| Plan execution (3×) | 15,000 |
| Task processing (8×) | 24,000 |
| File handling (12×) | 6,000 |
| Verification | 6,000 |
| **Total** | **56,000** |

### Cost Estimate (Sonnet)
| Type | Tokens | Rate | Cost |
|------|--------|------|------|
| Input | 33,600 | $3.00/1M | $0.10 |
| Output | 22,400 | $15.00/1M | $0.34 |
| **Total** | 56,000 | | **$0.44** |

### Comparison
| Model | Est. Cost | Quality | Speed |
|-------|-----------|---------|-------|
| Opus | $2.94 | Best | Slow |
| Sonnet | $0.44 | Good | Medium |
| Haiku | $0.04 | Basic | Fast |
| Local | $0.00 | Varies | Varies |

Proceed with execution? (yes/no/change-model)
```

### Detailed Output (--detailed)

```markdown
## Detailed Cost Breakdown

### By Agent
| Agent | Invocations | Tokens | Cost |
|-------|-------------|--------|------|
| eri-planner | 3 | 15,000 | $0.12 |
| eri-executor | 3 | 24,000 | $0.19 |
| eri-verifier | 1 | 6,000 | $0.05 |
| Context loading | 4 | 8,000 | $0.06 |
| **Total** | 11 | 53,000 | **$0.42** |

### By Plan
| Plan | Tasks | Files | Tokens | Cost |
|------|-------|-------|--------|------|
| 02-01 | 2 | 4 | 12,000 | $0.10 |
| 02-02 | 3 | 5 | 18,000 | $0.14 |
| 02-03 | 3 | 3 | 15,000 | $0.12 |

### Historical Comparison
Based on previous executions:

| Phase | Estimated | Actual | Accuracy |
|-------|-----------|--------|----------|
| Phase 1 | 45,000 | 42,000 | 93% |
| Phase 2 (current) | 56,000 | ? | - |

**Average accuracy:** 91%
```

## Project-Wide Estimates

```
/coder:cost new-project
```

```markdown
## Cost Estimate: New Project

**Project Type:** Web application
**Estimated Phases:** 5-7
**Estimated Complexity:** Medium

### Phase Breakdown (Estimated)
| Phase | Description | Est. Tokens | Est. Cost |
|-------|-------------|-------------|-----------|
| Init | Project setup | 50,000 | $0.40 |
| Research | 4 parallel agents | 40,000 | $0.32 |
| Roadmap | Phase planning | 15,000 | $0.12 |
| Phase 1 | Foundation | 30,000 | $0.24 |
| Phase 2 | Core features | 60,000 | $0.48 |
| Phase 3 | Additional | 45,000 | $0.36 |
| Phase 4 | Polish | 25,000 | $0.20 |
| Phase 5 | Deploy | 20,000 | $0.16 |
| **Total** | | **285,000** | **$2.28** |

### Confidence Interval
- **Optimistic:** $1.80 (minimal complexity)
- **Expected:** $2.28 (typical project)
- **Pessimistic:** $3.50 (complex, many iterations)

### Budget Recommendations
| Model Profile | Est. Cost | Recommended For |
|---------------|-----------|-----------------|
| Quality (Opus) | $15.20 | Production apps |
| Balanced (Sonnet) | $2.28 | Most projects |
| Budget (Haiku) | $0.19 | Prototypes |
| Local | $0.00 | Unlimited iteration |
```

## Local Model Comparison

```
/coder:cost execute-phase 2 --compare local
```

```markdown
## Cost Comparison: Cloud vs Local

### Cloud (Sonnet)
- Tokens: 56,000
- Cost: $0.44
- Speed: ~3 min
- Quality: High

### Local (llama-70b)
- Tokens: 56,000
- Cost: $0.00
- Speed: ~8 min (GPU dependent)
- Quality: Good

### Recommendation
**Use local for:**
- Iterative development
- Cost-sensitive phases
- Offline work

**Use cloud for:**
- Complex planning
- Production-critical code
- Time-sensitive work

### Hybrid Strategy
| Phase | Recommended |
|-------|-------------|
| Research | Cloud (quality) |
| Planning | Cloud (quality) |
| Execution | Local (cost) |
| Verification | Cloud (quality) |

**Hybrid cost:** $0.28 (36% savings)
```

## Rate Limit Awareness

```markdown
## Rate Limit Check

**Current usage:** 45,000 tokens this hour
**Limit:** 100,000 tokens/hour
**Remaining:** 55,000 tokens

### This Operation
- Estimated: 56,000 tokens
- Status: ⚠️ May hit rate limit

### Options
1. Proceed (may pause mid-execution)
2. Wait 15 min for limit reset
3. Switch to local model
4. Reduce scope (fewer plans)

Select option:
```

## Tracking Actual Costs

After execution, compare estimate to actual:

```python
def track_cost(operation, estimate, actual):
    # Store in metrics
    metrics = load_metrics()
    metrics.cost_tracking.append({
        "operation": operation,
        "timestamp": now(),
        "estimated_tokens": estimate.tokens,
        "actual_tokens": actual.tokens,
        "estimated_cost": estimate.cost_usd,
        "actual_cost": actual.cost_usd,
        "accuracy": estimate.tokens / actual.tokens
    })
    save_metrics(metrics)
```

## Integration Points

- Reads: ROADMAP.md, PLAN.md files, config.json
- Calculates: Token estimates based on operation and context
- Compares: Cloud vs local models
- Checks: Rate limits
- Tracks: Estimate accuracy over time
