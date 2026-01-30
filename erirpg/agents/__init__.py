"""
Agent management for ERI execution.

Provides:
- Agent prompt loading
- Agent spawning via Task tool
- Model selection based on profile
"""

from erirpg.agents.spawn import (
    spawn_agent,
    spawn_planner,
    spawn_executor,
    spawn_verifier,
    spawn_researcher,
    get_agent_prompt,
    AGENT_TYPES,
)
from erirpg.agents.prompts import (
    load_agent_prompt,
    get_prompt_path,
    list_available_agents,
)

__all__ = [
    # Spawn functions
    "spawn_agent",
    "spawn_planner",
    "spawn_executor",
    "spawn_verifier",
    "spawn_researcher",
    "get_agent_prompt",
    "AGENT_TYPES",
    # Prompt functions
    "load_agent_prompt",
    "get_prompt_path",
    "list_available_agents",
]
