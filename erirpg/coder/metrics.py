"""
Metrics tracking for coder workflow.

Commands:
- cost: Token and cost estimation
- metrics: Execution metrics tracking
- history: Execution history
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from . import get_planning_dir, load_roadmap, load_config, ensure_planning_dir


# Token estimation constants
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
        "debug": 8000,
    },
    "discuss-phase": {
        "base": 3000,
        "per_question": 500,
    },
    "quick": {
        "base": 4000,
        "per_file": 1000,
    },
    "debug": {
        "base": 6000,
        "per_hypothesis": 2000,
    },
}

# Pricing per 1M tokens (input/output)
MODEL_PRICING = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.25, "output": 1.25},
}


def estimate_tokens(
    operation: str,
    context: Optional[Dict] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Estimate tokens for an operation.

    Args:
        operation: Operation name (e.g., "execute-phase")
        context: Additional context (phase number, etc.)
        project_path: Project path

    Returns:
        Token estimate breakdown
    """
    context = context or {}
    estimates = TOKEN_ESTIMATES.get(operation, {"base": 5000})

    breakdown = {"base": estimates.get("base", 5000)}
    total = breakdown["base"]

    # Add context-dependent estimates
    if operation == "execute-phase":
        phase_num = context.get("phase", 1)
        phase_info = _get_phase_info(phase_num, project_path)

        if phase_info:
            plans = phase_info.get("plan_count", 3)
            tasks = phase_info.get("task_count", plans * 3)
            files = phase_info.get("file_count", tasks * 2)

            breakdown["plans"] = plans * estimates.get("per_task", 3000)
            breakdown["files"] = files * estimates.get("per_file", 500)
            breakdown["verification"] = estimates.get("verification", 6000)

            total += breakdown["plans"] + breakdown["files"] + breakdown["verification"]

    elif operation == "plan-phase":
        config = load_config(project_path)
        depth = config.get("depth", "standard")
        plans_per_depth = {"quick": 2, "standard": 4, "comprehensive": 8}
        plan_count = plans_per_depth.get(depth, 4)

        breakdown["plans"] = plan_count * estimates.get("per_plan", 5000)
        if config.get("workflow", {}).get("plan_check", True):
            breakdown["plan_check"] = estimates.get("plan_check", 4000)
        total += breakdown.get("plans", 0) + breakdown.get("plan_check", 0)

    elif operation == "new-project":
        config = load_config(project_path)
        if config.get("workflow", {}).get("research", True):
            breakdown["research"] = estimates.get("research", 40000)
        breakdown["roadmap"] = estimates.get("roadmap", 15000)
        total += breakdown.get("research", 0) + breakdown["roadmap"]

    breakdown["total"] = total
    return breakdown


def _get_phase_info(phase_num: int, project_path: Optional[Path] = None) -> Dict:
    """Get phase information for estimation."""
    planning_dir = get_planning_dir(project_path)
    phases_dir = planning_dir / "phases"

    if not phases_dir.exists():
        return {}

    # Find phase directory
    for d in phases_dir.iterdir():
        if d.name.startswith(f"{phase_num:02d}-"):
            plans = list(d.glob("*-PLAN.md"))
            task_count = 0
            file_count = 0

            for plan_path in plans:
                content = plan_path.read_text()
                # Count tasks (rough estimate)
                task_count += content.count("<task ")
                # Count files (rough estimate)
                file_count += content.count("<files>")

            return {
                "plan_count": len(plans),
                "task_count": task_count or len(plans) * 3,
                "file_count": file_count or task_count * 2,
            }

    return {}


def estimate_cost(
    operation: str,
    context: Optional[Dict] = None,
    model: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Estimate cost for an operation.

    Returns:
        Cost estimate with breakdown by model
    """
    token_estimate = estimate_tokens(operation, context, project_path)
    total_tokens = token_estimate.get("total", 5000)

    config = load_config(project_path)
    model = model or config.get("model_profile", "sonnet")

    # Assume 60/40 input/output split
    input_tokens = int(total_tokens * 0.6)
    output_tokens = int(total_tokens * 0.4)

    # Calculate costs for each model
    costs = {}
    for model_name, pricing in MODEL_PRICING.items():
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        costs[model_name] = {
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(input_cost + output_cost, 4),
        }

    return {
        "operation": operation,
        "tokens": token_estimate,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "model": model,
        "cost_usd": costs[model]["total_cost"],
        "all_models": costs,
    }


def estimate_project_cost(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Estimate total project cost."""
    config = load_config(project_path)
    roadmap = load_roadmap(project_path)

    phases = roadmap.get("phases", [])
    total_phases = len(phases) or 5  # Default estimate

    # Depth affects estimates
    depth = config.get("depth", "standard")
    multipliers = {"quick": 0.6, "standard": 1.0, "comprehensive": 1.8}
    mult = multipliers.get(depth, 1.0)

    estimates = {
        "init": estimate_cost("new-project", project_path=project_path),
        "planning": {"total_tokens": 0, "cost_usd": 0},
        "execution": {"total_tokens": 0, "cost_usd": 0},
        "verification": {"total_tokens": 0, "cost_usd": 0},
    }

    for i in range(total_phases):
        plan_est = estimate_cost("plan-phase", {"phase": i + 1}, project_path=project_path)
        exec_est = estimate_cost("execute-phase", {"phase": i + 1}, project_path=project_path)
        verify_est = estimate_cost("verify-work", {"phase": i + 1}, project_path=project_path)

        estimates["planning"]["total_tokens"] += int(plan_est["total_tokens"] * mult)
        estimates["planning"]["cost_usd"] += plan_est["cost_usd"] * mult

        estimates["execution"]["total_tokens"] += int(exec_est["total_tokens"] * mult)
        estimates["execution"]["cost_usd"] += exec_est["cost_usd"] * mult

        estimates["verification"]["total_tokens"] += int(verify_est["total_tokens"] * mult)
        estimates["verification"]["cost_usd"] += verify_est["cost_usd"] * mult

    total_tokens = (
        estimates["init"]["total_tokens"]
        + estimates["planning"]["total_tokens"]
        + estimates["execution"]["total_tokens"]
        + estimates["verification"]["total_tokens"]
    )

    total_cost = (
        estimates["init"]["cost_usd"]
        + estimates["planning"]["cost_usd"]
        + estimates["execution"]["cost_usd"]
        + estimates["verification"]["cost_usd"]
    )

    return {
        "phases": total_phases,
        "depth": depth,
        "breakdown": estimates,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 2),
        "confidence_range": {
            "optimistic": round(total_cost * 0.7, 2),
            "expected": round(total_cost, 2),
            "pessimistic": round(total_cost * 1.5, 2),
        },
    }


def load_metrics(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load metrics from .planning/metrics.json."""
    metrics_path = get_planning_dir(project_path) / "metrics.json"
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return {
        "executions": [],
        "cost_tracking": [],
        "session_stats": [],
    }


def save_metrics(metrics: Dict[str, Any], project_path: Optional[Path] = None) -> None:
    """Save metrics to .planning/metrics.json."""
    ensure_planning_dir(project_path)
    metrics_path = get_planning_dir(project_path) / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))


def track_execution(
    operation: str,
    phase: Optional[int] = None,
    plan: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    tokens_used: Optional[int] = None,
    success: bool = True,
    project_path: Optional[Path] = None,
) -> None:
    """Track an execution event."""
    metrics = load_metrics(project_path)

    execution = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": operation,
        "phase": phase,
        "plan": plan,
        "duration_seconds": duration_seconds,
        "tokens_used": tokens_used,
        "success": success,
    }

    metrics["executions"].append(execution)
    save_metrics(metrics, project_path)


def track_cost(
    operation: str,
    estimated_tokens: int,
    actual_tokens: int,
    estimated_cost: float,
    actual_cost: float,
    project_path: Optional[Path] = None,
) -> None:
    """Track cost estimation accuracy."""
    metrics = load_metrics(project_path)

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": operation,
        "estimated_tokens": estimated_tokens,
        "actual_tokens": actual_tokens,
        "estimated_cost": estimated_cost,
        "actual_cost": actual_cost,
        "accuracy": round(estimated_tokens / actual_tokens, 3) if actual_tokens else 0,
    }

    metrics["cost_tracking"].append(entry)
    save_metrics(metrics, project_path)


def get_execution_history(
    limit: int = 20, project_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Get recent execution history."""
    metrics = load_metrics(project_path)
    executions = metrics.get("executions", [])
    return executions[-limit:][::-1]  # Most recent first


def get_metrics_summary(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get metrics summary."""
    metrics = load_metrics(project_path)
    executions = metrics.get("executions", [])
    cost_tracking = metrics.get("cost_tracking", [])

    # Calculate stats
    total_executions = len(executions)
    successful = sum(1 for e in executions if e.get("success", True))
    total_duration = sum(e.get("duration_seconds", 0) or 0 for e in executions)
    total_tokens = sum(e.get("tokens_used", 0) or 0 for e in executions)

    # Cost accuracy
    accuracies = [e.get("accuracy", 0) for e in cost_tracking if e.get("accuracy")]
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0

    # By operation
    by_operation = {}
    for e in executions:
        op = e.get("operation", "unknown")
        if op not in by_operation:
            by_operation[op] = {"count": 0, "duration": 0, "tokens": 0}
        by_operation[op]["count"] += 1
        by_operation[op]["duration"] += e.get("duration_seconds", 0) or 0
        by_operation[op]["tokens"] += e.get("tokens_used", 0) or 0

    return {
        "total_executions": total_executions,
        "success_rate": round(successful / total_executions * 100, 1) if total_executions else 0,
        "total_duration_minutes": round(total_duration / 60, 1),
        "total_tokens": total_tokens,
        "cost_estimation_accuracy": round(avg_accuracy * 100, 1),
        "by_operation": by_operation,
    }
