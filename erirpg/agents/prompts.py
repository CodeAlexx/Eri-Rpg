"""
Agent prompt loading and management.

Prompts are stored in ~/.eri-rpg/agents/ for production use.
The erirpg/agents/ package directory stores them for version control.
Environment variable ERI_AGENTS_DIR can override the default location.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


# Default agents directory - user's home for production
DEFAULT_AGENTS_DIR = Path.home() / ".eri-rpg" / "agents"

# Agent types with their prompt files
# Note: Most files have 'eri-' prefix, behavior-extractor does not
AGENT_PROMPTS: Dict[str, str] = {
    "planner": "planner.md",
    "executor": "executor.md",
    "verifier": "verifier.md",
    "plan-checker": "plan-checker.md",
    "project-researcher": "project-researcher.md",
    "phase-researcher": "phase-researcher.md",
    "research-synthesizer": "research-synthesizer.md",
    "roadmapper": "roadmapper.md",
    "debugger": "debugger.md",
    "codebase-mapper": "codebase-mapper.md",
    "integration-checker": "integration-checker.md",
    "behavior-extractor": "behavior-extractor.md",
}


def get_agents_dir() -> Path:
    """Get the agents directory path.

    Returns:
        Path to agents directory
    """
    # Check environment override
    if "ERI_AGENTS_DIR" in os.environ:
        return Path(os.environ["ERI_AGENTS_DIR"])
    return DEFAULT_AGENTS_DIR


def get_prompt_path(agent_type: str) -> Path:
    """Get the path to an agent's prompt file.

    Args:
        agent_type: Type of agent

    Returns:
        Path to prompt file

    Raises:
        ValueError: If agent type is unknown
    """
    if agent_type not in AGENT_PROMPTS:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Valid types: {', '.join(AGENT_PROMPTS.keys())}"
        )

    return get_agents_dir() / AGENT_PROMPTS[agent_type]


def load_agent_prompt(agent_type: str) -> str:
    """Load an agent's prompt from disk.

    Args:
        agent_type: Type of agent

    Returns:
        Prompt content

    Raises:
        ValueError: If agent type is unknown
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_path = get_prompt_path(agent_type)

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Run 'eri-rpg init' to create default prompts."
        )

    return prompt_path.read_text()


def list_available_agents() -> List[str]:
    """List all available agent types.

    Returns:
        List of agent type names
    """
    return list(AGENT_PROMPTS.keys())


def get_agent_description(agent_type: str) -> str:
    """Get a brief description of an agent type.

    Args:
        agent_type: Type of agent

    Returns:
        Brief description
    """
    descriptions = {
        "planner": "Creates goal-backward plans with must-haves and tasks",
        "executor": "Executes plans task-by-task following deviation rules",
        "verifier": "Verifies must-haves using three-level verification",
        "plan-checker": "Validates plans across 6 dimensions before execution",
        "project-researcher": "Researches project structure and patterns",
        "phase-researcher": "Researches requirements for a specific phase",
        "research-synthesizer": "Combines research into actionable planning context",
        "roadmapper": "Creates and updates project roadmaps",
        "debugger": "Systematically debugs issues using scientific method",
        "codebase-mapper": "Creates detailed maps of codebase structure",
        "integration-checker": "Verifies component integrations and connections",
        "behavior-extractor": "Extracts portable behavior specs from source code",
    }
    return descriptions.get(agent_type, f"Agent type: {agent_type}")


def prompt_exists(agent_type: str) -> bool:
    """Check if a prompt file exists for an agent type.

    Args:
        agent_type: Type of agent

    Returns:
        True if prompt file exists
    """
    try:
        return get_prompt_path(agent_type).exists()
    except ValueError:
        return False


def validate_all_prompts() -> Dict[str, bool]:
    """Validate that all agent prompts exist.

    Returns:
        Dict mapping agent type to existence status
    """
    return {
        agent_type: prompt_exists(agent_type)
        for agent_type in AGENT_PROMPTS.keys()
    }


def format_agent_list() -> str:
    """Format a list of agents for display.

    Returns:
        Formatted string
    """
    lines = ["Available Agents", "=" * 40]

    for agent_type in AGENT_PROMPTS.keys():
        exists = prompt_exists(agent_type)
        status = "✓" if exists else "✗"
        desc = get_agent_description(agent_type)
        lines.append(f"{status} {agent_type}: {desc}")

    return "\n".join(lines)
