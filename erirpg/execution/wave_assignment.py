"""
Wave assignment algorithm for parallel execution.

Algorithm:
```
if plan.depends_on is empty:
    plan.wave = 1
else:
    plan.wave = max(waves[dep] for dep in plan.depends_on) + 1
```

Plans in the same wave can run in parallel.
"""

from typing import Dict, List, Optional, Set
from erirpg.models.plan import Plan


def assign_waves(plans: List[Plan]) -> Dict[str, int]:
    """Assign wave numbers to plans based on dependencies.

    Args:
        plans: List of Plan objects

    Returns:
        Dict mapping plan_id → wave_number
    """
    # Build lookup
    plan_by_id = {p.id: p for p in plans}
    waves: Dict[str, int] = {}

    # Track which plans are ready to be processed
    remaining = set(p.id for p in plans)
    processed = set()

    # Iteratively assign waves
    max_iterations = len(plans) + 1  # Prevent infinite loops
    iteration = 0

    while remaining and iteration < max_iterations:
        iteration += 1
        progress = False

        for plan_id in list(remaining):
            plan = plan_by_id[plan_id]

            # Check if all dependencies are processed
            if not plan.depends_on:
                # No dependencies → wave 1
                waves[plan_id] = 1
                remaining.remove(plan_id)
                processed.add(plan_id)
                progress = True
            elif all(dep in processed for dep in plan.depends_on):
                # All deps processed → wave = max(dep waves) + 1
                dep_waves = [waves[dep] for dep in plan.depends_on if dep in waves]
                if dep_waves:
                    waves[plan_id] = max(dep_waves) + 1
                else:
                    waves[plan_id] = 1
                remaining.remove(plan_id)
                processed.add(plan_id)
                progress = True

        # If no progress, we have a cycle or missing dependency
        if not progress and remaining:
            # Assign remaining to next wave and warn
            next_wave = max(waves.values(), default=0) + 1
            for plan_id in remaining:
                waves[plan_id] = next_wave
            break

    # Update plan objects
    for plan in plans:
        if plan.id in waves:
            plan.wave = waves[plan.id]

    return waves


def get_plans_for_wave(plans: List[Plan], wave: int) -> List[Plan]:
    """Get all plans assigned to a specific wave.

    Args:
        plans: List of Plan objects
        wave: Wave number

    Returns:
        List of plans in that wave
    """
    return [p for p in plans if p.wave == wave]


def get_max_wave(plans: List[Plan]) -> int:
    """Get the maximum wave number.

    Args:
        plans: List of Plan objects

    Returns:
        Maximum wave number (0 if no plans)
    """
    if not plans:
        return 0
    return max(p.wave for p in plans)


def validate_wave_assignment(plans: List[Plan]) -> List[str]:
    """Validate that wave assignment is correct.

    Checks:
    - All dependencies are in earlier waves
    - No cycles
    - All plans have waves assigned

    Args:
        plans: List of Plan objects

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    plan_by_id = {p.id: p for p in plans}

    for plan in plans:
        if plan.wave <= 0:
            errors.append(f"Plan {plan.id} has invalid wave: {plan.wave}")
            continue

        for dep_id in plan.depends_on:
            if dep_id not in plan_by_id:
                errors.append(f"Plan {plan.id} depends on unknown plan: {dep_id}")
                continue

            dep = plan_by_id[dep_id]
            if dep.wave >= plan.wave:
                errors.append(
                    f"Plan {plan.id} (wave {plan.wave}) depends on "
                    f"{dep_id} (wave {dep.wave}) - dependency must be in earlier wave"
                )

    return errors


def detect_cycles(plans: List[Plan]) -> List[List[str]]:
    """Detect dependency cycles in plans.

    Args:
        plans: List of Plan objects

    Returns:
        List of cycles (each cycle is a list of plan IDs)
    """
    plan_by_id = {p.id: p for p in plans}
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(plan_id: str, path: List[str]) -> Optional[List[str]]:
        if plan_id in rec_stack:
            # Found cycle - extract it
            cycle_start = path.index(plan_id)
            return path[cycle_start:]

        if plan_id in visited:
            return None

        if plan_id not in plan_by_id:
            return None

        visited.add(plan_id)
        rec_stack.add(plan_id)
        path.append(plan_id)

        plan = plan_by_id[plan_id]
        for dep_id in plan.depends_on:
            cycle = dfs(dep_id, path.copy())
            if cycle:
                cycles.append(cycle)

        rec_stack.remove(plan_id)
        return None

    for plan in plans:
        if plan.id not in visited:
            dfs(plan.id, [])

    return cycles


def optimize_waves(plans: List[Plan]) -> Dict[str, int]:
    """Optimize wave assignment for maximum parallelism.

    Tries to minimize the number of waves while respecting dependencies.

    Args:
        plans: List of Plan objects

    Returns:
        Optimized wave assignment
    """
    # First, detect and report cycles
    cycles = detect_cycles(plans)
    if cycles:
        # Can't optimize with cycles - use basic assignment
        return assign_waves(plans)

    # Topological sort with wave optimization
    plan_by_id = {p.id: p for p in plans}
    in_degree = {p.id: 0 for p in plans}

    # Calculate in-degrees
    for plan in plans:
        for dep_id in plan.depends_on:
            if dep_id in plan_by_id:
                in_degree[plan.id] += 1

    # Process in waves
    waves: Dict[str, int] = {}
    current_wave = 1
    remaining = set(p.id for p in plans)

    while remaining:
        # Find all plans with no remaining dependencies
        ready = [pid for pid in remaining if in_degree[pid] == 0]

        if not ready:
            # Stuck - shouldn't happen without cycles
            for pid in remaining:
                waves[pid] = current_wave
            break

        # Assign current wave
        for pid in ready:
            waves[pid] = current_wave
            remaining.remove(pid)

            # Update in-degrees
            for plan in plans:
                if pid in plan.depends_on:
                    in_degree[plan.id] -= 1

        current_wave += 1

    # Update plan objects
    for plan in plans:
        if plan.id in waves:
            plan.wave = waves[plan.id]

    return waves


def estimate_execution_time(plans: List[Plan]) -> Dict[str, any]:
    """Estimate execution time based on wave structure.

    Args:
        plans: List of Plan objects

    Returns:
        Dict with execution estimates
    """
    max_wave = get_max_wave(plans)

    wave_sizes = {}
    for wave in range(1, max_wave + 1):
        wave_plans = get_plans_for_wave(plans, wave)
        wave_sizes[wave] = len(wave_plans)

    return {
        "total_plans": len(plans),
        "total_waves": max_wave,
        "wave_sizes": wave_sizes,
        "max_parallel": max(wave_sizes.values(), default=0),
        "is_fully_parallel": max_wave == 1,
        "is_fully_sequential": max_wave == len(plans),
    }
