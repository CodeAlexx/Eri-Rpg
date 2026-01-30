"""
Wave executor for parallel plan execution.

Executes plans in waves:
1. All plans in wave N run in parallel
2. Wait for all to complete
3. Move to wave N+1
4. Repeat until done

Each plan runs in a fresh subagent with no context bleed.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import json
import os

from erirpg.models.plan import Plan, list_plans
from erirpg.execution.results import PlanResult, WaveResult, PhaseResult
from erirpg.execution.wave_assignment import (
    assign_waves,
    get_plans_for_wave,
    get_max_wave,
    validate_wave_assignment,
)


# Lazy imports to avoid circular import with parallel_agents
_AgentPool = None
_spawn_plan_executor = None
_wait_for_agents = None


def _ensure_agent_imports():
    """Lazy import agent functions to avoid circular imports."""
    global _AgentPool, _spawn_plan_executor, _wait_for_agents
    if _AgentPool is None:
        from erirpg.execution.parallel_agents import AgentPool, spawn_plan_executor, wait_for_agents
        _AgentPool = AgentPool
        _spawn_plan_executor = spawn_plan_executor
        _wait_for_agents = wait_for_agents


class WaveExecutor:
    """Executes plans in parallel waves."""

    def __init__(
        self,
        project_path: str,
        max_parallel: int = 3,
        on_plan_start: Optional[Callable[[Plan], None]] = None,
        on_plan_complete: Optional[Callable[[Plan, PlanResult], None]] = None,
        on_wave_complete: Optional[Callable[[WaveResult], None]] = None,
    ):
        """Initialize wave executor.

        Args:
            project_path: Path to project root
            max_parallel: Maximum parallel agents
            on_plan_start: Callback when plan starts
            on_plan_complete: Callback when plan completes
            on_wave_complete: Callback when wave completes
        """
        _ensure_agent_imports()
        self.project_path = project_path
        self.max_parallel = max_parallel
        self.on_plan_start = on_plan_start
        self.on_plan_complete = on_plan_complete
        self.on_wave_complete = on_wave_complete
        self.agent_pool = _AgentPool(max_parallel)

    def execute_phase(self, phase: str) -> PhaseResult:
        """Execute all plans for a phase.

        Args:
            phase: Phase name

        Returns:
            PhaseResult
        """
        result = PhaseResult(phase=phase)
        result.started_at = datetime.now().isoformat()

        # Load and prepare plans
        plans = list_plans(self.project_path, phase)
        if not plans:
            result.status = "completed"
            result.completed_at = datetime.now().isoformat()
            return result

        # Assign waves
        assign_waves(plans)

        # Validate
        errors = validate_wave_assignment(plans)
        if errors:
            result.status = "failed"
            result.completed_at = datetime.now().isoformat()
            return result

        # Execute wave by wave
        max_wave = get_max_wave(plans)
        for wave_num in range(1, max_wave + 1):
            wave_result = self.execute_wave(plans, wave_num)
            result.wave_results.append(wave_result)

            if self.on_wave_complete:
                self.on_wave_complete(wave_result)

            # Stop if wave has failures or checkpoints
            if wave_result.has_failures:
                result.status = "failed"
                break
            if wave_result.has_checkpoints:
                result.status = "checkpoint"
                break

        if result.status == "pending":
            result.status = "completed"

        result.completed_at = datetime.now().isoformat()
        return result

    def execute_wave(self, plans: List[Plan], wave_number: int) -> WaveResult:
        """Execute all plans in a wave in parallel.

        Args:
            plans: All plans for the phase
            wave_number: Wave number to execute

        Returns:
            WaveResult
        """
        result = WaveResult(wave_number=wave_number)
        result.started_at = datetime.now().isoformat()

        wave_plans = get_plans_for_wave(plans, wave_number)

        if not wave_plans:
            result.completed_at = datetime.now().isoformat()
            return result

        # Spawn agents for each plan
        agents = []
        for plan in wave_plans:
            if self.on_plan_start:
                self.on_plan_start(plan)

            agent = _spawn_plan_executor(
                self.project_path,
                plan,
                self.agent_pool,
            )
            agents.append((plan, agent))

        # Wait for all to complete
        for plan, agent in agents:
            plan_result = _wait_for_agents([agent])[0]
            result.plan_results.append(plan_result)

            if self.on_plan_complete:
                self.on_plan_complete(plan, plan_result)

        result.completed_at = datetime.now().isoformat()
        return result


def execute_phase(
    project_path: str,
    phase: str,
    max_parallel: int = 3,
) -> PhaseResult:
    """Convenience function to execute a phase.

    Args:
        project_path: Path to project root
        phase: Phase name
        max_parallel: Maximum parallel agents

    Returns:
        PhaseResult
    """
    executor = WaveExecutor(project_path, max_parallel)
    return executor.execute_phase(phase)


def save_phase_result(project_path: str, result: PhaseResult) -> str:
    """Save phase execution result.

    Args:
        project_path: Path to project root
        result: PhaseResult to save

    Returns:
        Path to saved file
    """
    phase_dir = os.path.join(project_path, ".eri-rpg", "phases", result.phase)
    os.makedirs(phase_dir, exist_ok=True)

    file_path = os.path.join(phase_dir, "execution-result.json")
    with open(file_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    return file_path


def load_phase_result(project_path: str, phase: str) -> Optional[PhaseResult]:
    """Load phase execution result.

    Args:
        project_path: Path to project root
        phase: Phase name

    Returns:
        PhaseResult if found, None otherwise
    """
    file_path = os.path.join(project_path, ".eri-rpg", "phases", phase, "execution-result.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    result = PhaseResult(
        phase=data.get("phase", ""),
        status=data.get("status", "pending"),
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
    )

    # Parse wave results
    for wave_data in data.get("wave_results", []):
        wave = WaveResult(
            wave_number=wave_data.get("wave_number", 0),
            started_at=wave_data.get("started_at"),
            completed_at=wave_data.get("completed_at"),
        )

        for plan_data in wave_data.get("plan_results", []):
            plan_result = PlanResult(
                plan_id=plan_data.get("plan_id", ""),
                status=plan_data.get("status", ""),
                checkpoint_id=plan_data.get("checkpoint_id"),
                error=plan_data.get("error"),
                duration_seconds=plan_data.get("duration_seconds", 0),
            )
            wave.plan_results.append(plan_result)

        result.wave_results.append(wave)

    return result
