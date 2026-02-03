"""
Agent spawning for ERI execution.

Spawns agents using Claude Code's Task tool with appropriate
prompts and model selection based on configuration.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from erirpg.agents.prompts import load_agent_prompt, AGENT_PROMPTS
from erirpg.config import load_config, get_model_for_agent, ModelName


# All supported agent types
AGENT_TYPES = list(AGENT_PROMPTS.keys())


@dataclass
class AgentSpawnConfig:
    """Configuration for spawning an agent."""
    agent_type: str
    model: ModelName
    prompt: str
    context: str
    description: str


@dataclass
class SpawnResult:
    """Result of spawning an agent."""
    agent_type: str
    agent_id: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


def get_agent_prompt(agent_type: str, context: str = "") -> str:
    """Get the full prompt for an agent including context.

    Args:
        agent_type: Type of agent
        context: Additional context to include

    Returns:
        Full prompt string
    """
    base_prompt = load_agent_prompt(agent_type)

    if context:
        return f"{base_prompt}\n\n## Context\n\n{context}"

    return base_prompt


def build_spawn_config(
    project_path: str,
    agent_type: str,
    context: str = "",
    description: str = "",
) -> AgentSpawnConfig:
    """Build configuration for spawning an agent.

    Args:
        project_path: Path to project
        agent_type: Type of agent to spawn
        context: Additional context for the agent
        description: Short description for the spawn

    Returns:
        AgentSpawnConfig
    """
    if agent_type not in AGENT_TYPES:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Valid types: {', '.join(AGENT_TYPES)}"
        )

    # Get model from config
    model = get_model_for_agent(project_path, agent_type)

    # Get prompt with context
    prompt = get_agent_prompt(agent_type, context)

    # Generate description if not provided
    if not description:
        description = f"{agent_type} agent"

    return AgentSpawnConfig(
        agent_type=agent_type,
        model=model,
        prompt=prompt,
        context=context,
        description=description,
    )


def format_task_tool_call(config: AgentSpawnConfig) -> Dict[str, Any]:
    """Format the Task tool call for spawning an agent.

    This returns the parameters that would be passed to the Task tool
    in Claude Code. The actual invocation happens in the Claude Code
    context.

    Args:
        config: Agent spawn configuration

    Returns:
        Dict with Task tool parameters
    """
    return {
        "description": config.description,
        "prompt": config.prompt,
        "subagent_type": "general-purpose",
        "model": config.model,
    }


def spawn_agent(
    project_path: str,
    agent_type: str,
    context: str = "",
    description: str = "",
) -> Dict[str, Any]:
    """Prepare to spawn an agent.

    This prepares the Task tool parameters for spawning an agent.
    The actual spawning must be done by the calling Claude Code context.

    Args:
        project_path: Path to project
        agent_type: Type of agent to spawn
        context: Additional context
        description: Short description

    Returns:
        Task tool parameters ready for invocation
    """
    config = build_spawn_config(project_path, agent_type, context, description)
    return format_task_tool_call(config)


# ============================================================================
# Convenience functions for common agent types
# ============================================================================

def spawn_planner(
    project_path: str,
    phase: str,
    objective: str,
    research_context: str = "",
) -> Dict[str, Any]:
    """Spawn a planner agent.

    Args:
        project_path: Path to project
        phase: Phase name
        objective: Phase objective
        research_context: Research context for planning

    Returns:
        Task tool parameters
    """
    context = f"""## Phase: {phase}
## Objective: {objective}

{research_context}
"""
    return spawn_agent(
        project_path,
        "planner",
        context=context,
        description=f"Plan {phase}",
    )


def spawn_executor(
    project_path: str,
    plan_id: str,
    plan_content: str,
) -> Dict[str, Any]:
    """Spawn an executor agent.

    Args:
        project_path: Path to project
        plan_id: Plan identifier
        plan_content: Full plan content

    Returns:
        Task tool parameters
    """
    context = f"""## Plan: {plan_id}

{plan_content}
"""
    return spawn_agent(
        project_path,
        "executor",
        context=context,
        description=f"Execute {plan_id}",
    )


def spawn_verifier(
    project_path: str,
    plan_id: str,
    must_haves: str,
    level: int = 2,
) -> Dict[str, Any]:
    """Spawn a verifier agent.

    Args:
        project_path: Path to project
        plan_id: Plan identifier
        must_haves: Must-haves to verify
        level: Verification level (1, 2, or 3)

    Returns:
        Task tool parameters
    """
    context = f"""## Plan: {plan_id}
## Verification Level: {level}

{must_haves}
"""
    return spawn_agent(
        project_path,
        "verifier",
        context=context,
        description=f"Verify {plan_id}",
    )


def spawn_researcher(
    project_path: str,
    researcher_type: str,
    target: str,
    context: str = "",
) -> Dict[str, Any]:
    """Spawn a researcher agent.

    Args:
        project_path: Path to project
        researcher_type: "project", "phase", or "synthesizer"
        target: What to research
        context: Additional context

    Returns:
        Task tool parameters
    """
    agent_map = {
        "project": "project-researcher",
        "phase": "phase-researcher",
        "synthesizer": "research-synthesizer",
    }

    agent_type = agent_map.get(researcher_type, f"{researcher_type}-researcher")

    research_context = f"""## Research Target: {target}

{context}
"""
    return spawn_agent(
        project_path,
        agent_type,
        context=research_context,
        description=f"Research {target}",
    )


def spawn_debugger(
    project_path: str,
    bug_description: str,
    error_context: str = "",
) -> Dict[str, Any]:
    """Spawn a debugger agent.

    Args:
        project_path: Path to project
        bug_description: Description of the bug
        error_context: Error messages, stack traces, etc.

    Returns:
        Task tool parameters
    """
    context = f"""## Bug Description
{bug_description}

## Error Context
{error_context}
"""
    return spawn_agent(
        project_path,
        "debugger",
        context=context,
        description="Debug issue",
    )


def spawn_plan_checker(
    project_path: str,
    plan_content: str,
    spec_content: str = "",
) -> Dict[str, Any]:
    """Spawn a plan checker agent.

    Args:
        project_path: Path to project
        plan_content: Plan to check
        spec_content: Spec to validate against

    Returns:
        Task tool parameters
    """
    context = f"""## Plan to Check
{plan_content}

## Spec
{spec_content}
"""
    return spawn_agent(
        project_path,
        "plan-checker",
        context=context,
        description="Check plan",
    )


def spawn_codebase_mapper(project_path: str) -> Dict[str, Any]:
    """Spawn a codebase mapper agent.

    Args:
        project_path: Path to project

    Returns:
        Task tool parameters
    """
    return spawn_agent(
        project_path,
        "codebase-mapper",
        context=f"## Project Path: {project_path}",
        description="Map codebase",
    )


def spawn_integration_checker(
    project_path: str,
    key_links: str,
) -> Dict[str, Any]:
    """Spawn an integration checker agent.

    Args:
        project_path: Path to project
        key_links: Key links to verify

    Returns:
        Task tool parameters
    """
    context = f"""## Key Links to Verify
{key_links}
"""
    return spawn_agent(
        project_path,
        "integration-checker",
        context=context,
        description="Check integrations",
    )


def spawn_roadmapper(
    project_path: str,
    goal: str,
    context: str = "",
) -> Dict[str, Any]:
    """Spawn a roadmapper agent.

    Args:
        project_path: Path to project
        goal: Overall goal
        context: Additional context

    Returns:
        Task tool parameters
    """
    roadmap_context = f"""## Goal: {goal}

{context}
"""
    return spawn_agent(
        project_path,
        "roadmapper",
        context=roadmap_context,
        description="Create roadmap",
    )


def spawn_behavior_extractor(
    project_path: str,
    source_path: str,
    module_name: str,
    extract_tests: bool = True,
) -> Dict[str, Any]:
    """Spawn a behavior extractor agent.

    Args:
        project_path: Path to target project
        source_path: Path to source code to extract from
        module_name: Name of module to extract
        extract_tests: Whether to extract test contracts

    Returns:
        Task tool parameters
    """
    context = f"""## Source Path: {source_path}
## Module: {module_name}
## Extract Tests: {extract_tests}

Extract portable behavior specification from the source code.
Output to: .planning/blueprints/{module_name}-BEHAVIOR.md
"""
    return spawn_agent(
        project_path,
        "behavior-extractor",
        context=context,
        description=f"Extract behavior: {module_name}",
    )
