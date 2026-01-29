"""
EriRPG Project Configuration.

Per-project settings stored in .eri-rpg/config.json.

Supports two operational modes (enforcement):
- bootstrap: No enforcement, hooks pass through (for new/developing projects)
- maintain: Full enforcement, hooks enforce preflight/runs (for stable projects)

Supports three feature tiers:
- lite: Fast workflow tracking, no indexing required
- standard: Adds codebase awareness, discussion, learning
- full: All features including agent runs, specs, plans, verification
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Dict, List, Any


# Type aliases
Mode = Literal["bootstrap", "maintain"]
Tier = Literal["lite", "standard", "full"]

# Tier hierarchy (higher index = more features)
TIER_LEVELS = {"lite": 0, "standard": 1, "full": 2}

# Tier configuration - defines what each tier includes
TIER_CONFIG: Dict[str, Dict[str, Any]] = {
    "lite": {
        "description": "Fast workflow tracking",
        "requires_index": False,
        "token_budget": "minimal",
        "commands": [
            # Core workflow
            "take", "work", "done", "next",
            # Quick tasks
            "quick", "quick-done", "quick-cancel", "quick-status",
            # Basic tracking
            "list", "todo", "notes", "session", "handoff",
            # Setup (always available)
            "add", "remove", "index", "init", "graduate", "mode", "info",
            "install", "uninstall", "install-status", "config",
        ],
    },
    "standard": {
        "description": "Codebase awareness + discussion",
        "requires_index": True,
        "token_budget": "moderate",
        "commands": [
            # Inherits lite commands
            # Exploration
            "show", "find", "impact",
            # Discussion
            "discuss", "discuss-answer", "discuss-resolve", "discuss-show", "discuss-clear",
            # Learning
            "learn", "recall", "relearn", "history", "pattern", "patterns",
            # Decisions & roadmap
            "log-decision", "list-decisions", "defer", "deferred", "promote",
            "roadmap", "roadmap-add", "roadmap-next", "roadmap-edit",
            # Context
            "describe", "decision", "decisions", "log", "knowledge",
            "extract", "transplant-plan", "context", "gaps",
        ],
    },
    "full": {
        "description": "All features, agent runs, advanced tracking",
        "requires_index": True,
        "token_budget": "full",
        "commands": [
            # Inherits standard commands
            # Runs & execution
            "run", "do", "status", "validate", "diagnose", "reset",
            # Specs & plans
            "spec", "plan",
            # Goals
            "goal-plan", "goal-run", "goal-status",
            # Verification
            "verify",
            # Memory management
            "memory", "rollback",
            # Analysis & advanced
            "analyze", "implement", "transplant-feature", "describe-feature",
            "research", "execute", "new",
            # Personas & workflows
            "persona", "workflow", "ctx", "commands",
            # Drift tracking
            "drift-status", "enrich-learnings", "sync-patterns", "sync",
            "drift-patterns", "drift-impact",
            # Cleanup & maintenance
            "cleanup", "runs",
            # UI
            "serve",
        ],
    },
}


def tier_includes_command(tier: Tier, command: str) -> bool:
    """Check if a tier includes a specific command.

    Args:
        tier: The tier to check
        command: The command name

    Returns:
        True if the command is available in this tier
    """
    tier_level = TIER_LEVELS[tier]

    # Check each tier up to and including the current tier
    for t, level in TIER_LEVELS.items():
        if level <= tier_level:
            if command in TIER_CONFIG[t]["commands"]:
                return True
    return False


def get_tier_for_command(command: str) -> Optional[Tier]:
    """Get the minimum tier required for a command.

    Args:
        command: The command name

    Returns:
        The minimum tier required, or None if command not found
    """
    for tier in ["lite", "standard", "full"]:
        if command in TIER_CONFIG[tier]["commands"]:
            return tier
    return None


@dataclass
class MultiAgentConfig:
    """Multi-agent execution settings."""
    enabled: bool = False
    max_concurrency: int = 3
    parallel_steps: bool = True


@dataclass
class ProjectConfig:
    """Project-level configuration."""
    # Operational mode (enforcement)
    mode: Mode = "bootstrap"
    created_at: Optional[str] = None
    graduated_at: Optional[str] = None  # Set when project graduates to maintain
    graduated_by: Optional[str] = None  # "user" | "auto"

    # Feature tier
    tier: Tier = "lite"

    # Multi-agent settings
    multi_agent: MultiAgentConfig = field(default_factory=MultiAgentConfig)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "tier": self.tier,
            "created_at": self.created_at,
            "graduated_at": self.graduated_at,
            "graduated_by": self.graduated_by,
            "multi_agent": asdict(self.multi_agent),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        ma_data = data.get("multi_agent", {})
        return cls(
            mode=data.get("mode", "bootstrap"),
            tier=data.get("tier", "lite"),
            created_at=data.get("created_at"),
            graduated_at=data.get("graduated_at"),
            graduated_by=data.get("graduated_by"),
            multi_agent=MultiAgentConfig(
                enabled=ma_data.get("enabled", False),
                max_concurrency=ma_data.get("max_concurrency", 3),
                parallel_steps=ma_data.get("parallel_steps", True),
            )
        )

    def is_bootstrap(self) -> bool:
        """Check if project is in bootstrap mode."""
        return self.mode == "bootstrap"

    def is_maintain(self) -> bool:
        """Check if project is in maintain mode."""
        return self.mode == "maintain"

    def has_graduated(self) -> bool:
        """Check if project has ever graduated."""
        return self.graduated_at is not None

    def is_lite(self) -> bool:
        """Check if project is in lite tier."""
        return self.tier == "lite"

    def is_standard(self) -> bool:
        """Check if project is in standard tier."""
        return self.tier == "standard"

    def is_full(self) -> bool:
        """Check if project is in full tier."""
        return self.tier == "full"

    def tier_level(self) -> int:
        """Get numeric tier level (0=lite, 1=standard, 2=full)."""
        return TIER_LEVELS.get(self.tier, 0)

    def can_use_command(self, command: str) -> bool:
        """Check if current tier allows a command."""
        return tier_includes_command(self.tier, command)


def get_config_path(project_path: str) -> Path:
    """Get the config file path for a project."""
    return Path(project_path) / ".eri-rpg" / "config.json"


def load_config(project_path: str) -> ProjectConfig:
    """Load project configuration. Returns defaults if not found."""
    config_file = get_config_path(project_path)

    if not config_file.exists():
        return ProjectConfig()

    try:
        with open(config_file) as f:
            data = json.load(f)
        return ProjectConfig.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return ProjectConfig()


def save_config(project_path: str, config: ProjectConfig) -> None:
    """Save project configuration."""
    config_file = get_config_path(project_path)

    # Ensure .eri-rpg directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


def set_multi_agent(project_path: str, enabled: bool) -> ProjectConfig:
    """Enable or disable multi-agent mode."""
    config = load_config(project_path)
    config.multi_agent.enabled = enabled
    save_config(project_path, config)
    return config


def set_concurrency(project_path: str, max_concurrency: int) -> ProjectConfig:
    """Set max concurrency for multi-agent mode."""
    config = load_config(project_path)
    config.multi_agent.max_concurrency = max(1, min(15, max_concurrency))
    save_config(project_path, config)
    return config


# ============================================================================
# Mode Management
# ============================================================================

def get_mode(project_path: str) -> Mode:
    """Get the operational mode for a project.

    Handles migration: projects with learnings default to 'maintain',
    new/empty projects default to 'bootstrap'.

    Args:
        project_path: Path to project root

    Returns:
        "bootstrap" or "maintain"
    """
    config_file = get_config_path(project_path)

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)

            # If mode is explicitly set, use it
            if "mode" in data:
                return data["mode"]

        except (json.JSONDecodeError, KeyError):
            pass

    # Migration: check if project has learnings
    knowledge_file = Path(project_path) / ".eri-rpg" / "knowledge.json"
    if knowledge_file.exists():
        try:
            with open(knowledge_file) as f:
                knowledge = json.load(f)

            # Has learnings → assume stable project → maintain
            if knowledge.get("learnings"):
                return "maintain"
        except (json.JSONDecodeError, KeyError):
            pass

    # Default for new/empty projects
    return "bootstrap"


def set_mode(project_path: str, mode: Mode) -> ProjectConfig:
    """Set the operational mode for a project.

    Args:
        project_path: Path to project root
        mode: "bootstrap" or "maintain"

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.mode = mode
    save_config(project_path, config)
    return config


def graduate_project(project_path: str, by: str = "user") -> ProjectConfig:
    """Graduate a project from bootstrap to maintain mode.

    Sets graduated_at timestamp and switches to maintain mode.

    Args:
        project_path: Path to project root
        by: Who triggered graduation ("user" or "auto")

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.mode = "maintain"
    config.graduated_at = datetime.now().isoformat()
    config.graduated_by = by
    save_config(project_path, config)
    return config


def init_project_config(project_path: str, tier: Tier = "lite") -> ProjectConfig:
    """Initialize config for a new project in bootstrap mode.

    Creates .eri-rpg/config.json with bootstrap defaults and specified tier.

    Args:
        project_path: Path to project root
        tier: Feature tier (defaults to 'lite')

    Returns:
        New ProjectConfig
    """
    config = ProjectConfig(
        mode="bootstrap",
        tier=tier,
        created_at=datetime.now().isoformat(),
    )
    save_config(project_path, config)
    return config


# ============================================================================
# Tier Management
# ============================================================================

def get_tier(project_path: str) -> Tier:
    """Get the feature tier for a project.

    Args:
        project_path: Path to project root

    Returns:
        "lite", "standard", or "full"
    """
    config = load_config(project_path)
    return config.tier


def set_tier(project_path: str, tier: Tier) -> ProjectConfig:
    """Set the feature tier for a project.

    Args:
        project_path: Path to project root
        tier: "lite", "standard", or "full"

    Returns:
        Updated ProjectConfig
    """
    if tier not in TIER_LEVELS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of: lite, standard, full")

    config = load_config(project_path)
    config.tier = tier
    save_config(project_path, config)
    return config


def upgrade_tier(project_path: str) -> ProjectConfig:
    """Upgrade project to next tier level.

    lite -> standard -> full

    Args:
        project_path: Path to project root

    Returns:
        Updated ProjectConfig

    Raises:
        ValueError: If already at full tier
    """
    config = load_config(project_path)
    current_level = TIER_LEVELS[config.tier]

    if current_level >= 2:
        raise ValueError("Project is already at full tier")

    # Find next tier
    for tier, level in TIER_LEVELS.items():
        if level == current_level + 1:
            config.tier = tier
            break

    save_config(project_path, config)
    return config


def tier_allows(current_tier: Tier, required_tier: Tier) -> bool:
    """Check if current tier includes required tier level.

    Args:
        current_tier: The project's current tier
        required_tier: The minimum tier required

    Returns:
        True if current tier >= required tier
    """
    return TIER_LEVELS.get(current_tier, 0) >= TIER_LEVELS.get(required_tier, 0)
