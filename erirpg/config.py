"""
EriRPG Project Configuration.

Per-project settings stored in .eri-rpg/config.json.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class MultiAgentConfig:
    """Multi-agent execution settings."""
    enabled: bool = False
    max_concurrency: int = 3
    parallel_steps: bool = True


@dataclass
class ProjectConfig:
    """Project-level configuration."""
    multi_agent: MultiAgentConfig = field(default_factory=MultiAgentConfig)

    def to_dict(self) -> dict:
        return {
            "multi_agent": asdict(self.multi_agent)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        ma_data = data.get("multi_agent", {})
        return cls(
            multi_agent=MultiAgentConfig(
                enabled=ma_data.get("enabled", False),
                max_concurrency=ma_data.get("max_concurrency", 3),
                parallel_steps=ma_data.get("parallel_steps", True),
            )
        )


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
