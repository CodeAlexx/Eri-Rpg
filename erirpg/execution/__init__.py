"""
EriRPG Execution System.

Handles:
- Wave-based parallel execution
- Deviation rules (auto-fix vs checkpoint)
- Checkpoint handling and continuation
- Agent spawning and coordination
"""

from erirpg.execution.deviation_rules import (
    DeviationType,
    DeviationRule,
    classify_deviation,
    should_auto_fix,
    should_checkpoint,
    DEVIATION_RULES,
)
from erirpg.execution.wave_assignment import (
    assign_waves,
    get_plans_for_wave,
    validate_wave_assignment,
)
# Import results first to avoid circular import
from erirpg.execution.results import (
    PlanResult,
    WaveResult,
    PhaseResult,
)
from erirpg.execution.parallel_agents import (
    AgentPool,
    spawn_plan_executor,
    wait_for_agents,
)
from erirpg.execution.wave_executor import (
    WaveExecutor,
    execute_phase,
)
from erirpg.execution.checkpoint_handler import (
    CheckpointHandler,
    create_checkpoint,
    continue_from_checkpoint,
)

__all__ = [
    # Deviation rules
    "DeviationType",
    "DeviationRule",
    "classify_deviation",
    "should_auto_fix",
    "should_checkpoint",
    "DEVIATION_RULES",
    # Wave assignment
    "assign_waves",
    "get_plans_for_wave",
    "validate_wave_assignment",
    # Results
    "PlanResult",
    "WaveResult",
    "PhaseResult",
    # Wave executor
    "WaveExecutor",
    "execute_phase",
    # Checkpoint handler
    "CheckpointHandler",
    "create_checkpoint",
    "continue_from_checkpoint",
    # Parallel agents
    "AgentPool",
    "spawn_plan_executor",
    "wait_for_agents",
]
