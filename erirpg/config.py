"""
EriRPG Project Configuration.

Per-project settings stored in .eri-rpg/config.json.

Supports two operational modes:
- bootstrap: No enforcement, hooks pass through (for new/developing projects)
- maintain: Full enforcement, hooks enforce preflight/runs (for stable projects)
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal


# Mode type alias
Mode = Literal["bootstrap", "maintain"]


@dataclass
class MultiAgentConfig:
    """Multi-agent execution settings."""
    enabled: bool = False
    max_concurrency: int = 3
    parallel_steps: bool = True


@dataclass
class ProjectConfig:
    """Project-level configuration."""
    # Operational mode
    mode: Mode = "bootstrap"
    created_at: Optional[str] = None
    graduated_at: Optional[str] = None  # Set when project graduates to maintain
    graduated_by: Optional[str] = None  # "user" | "auto"

    # Multi-agent settings
    multi_agent: MultiAgentConfig = field(default_factory=MultiAgentConfig)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
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


def init_project_config(project_path: str) -> ProjectConfig:
    """Initialize config for a new project in bootstrap mode.

    Creates .eri-rpg/config.json with bootstrap defaults.

    Args:
        project_path: Path to project root

    Returns:
        New ProjectConfig
    """
    config = ProjectConfig(
        mode="bootstrap",
        created_at=datetime.now().isoformat(),
    )
    save_config(project_path, config)
    return config
