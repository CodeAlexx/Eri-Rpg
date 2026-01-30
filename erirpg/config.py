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

# GSD-specific type aliases
GSDMode = Literal["yolo", "interactive"]
GSDDepth = Literal["quick", "standard", "comprehensive"]
ModelProfile = Literal["quality", "balanced", "budget"]
ModelName = Literal["opus", "sonnet", "haiku"]

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
class EnvironmentConfig:
    """Per-project environment and command settings.

    Stores how to run tests, lint, build, etc. for this specific project.
    Avoids guessing and wasting tokens figuring out the environment.
    """
    # Package manager / runner
    runner: Optional[str] = None  # uv, pip, poetry, cargo, npm, pnpm, yarn, etc.

    # Common commands (full command strings)
    test: Optional[str] = None      # e.g., "uv run pytest", "cargo test", "npm test"
    lint: Optional[str] = None      # e.g., "uv run ruff check", "cargo clippy"
    format: Optional[str] = None    # e.g., "uv run ruff format", "cargo fmt"
    build: Optional[str] = None     # e.g., "uv build", "cargo build --release"
    run: Optional[str] = None       # e.g., "uv run python main.py", "cargo run"
    typecheck: Optional[str] = None # e.g., "uv run mypy", "npx tsc --noEmit"

    # Paths
    python: Optional[str] = None    # e.g., ".venv/bin/python", "python3.11"
    venv: Optional[str] = None      # e.g., ".venv", "venv", "conda env"

    # Environment variables (key=value pairs)
    env_vars: Dict[str, str] = field(default_factory=dict)

    # Project-specific paths
    src_dir: Optional[str] = None   # e.g., "src", "lib", "erirpg"
    test_dir: Optional[str] = None  # e.g., "tests", "test", "spec"

    def to_dict(self) -> dict:
        return {
            "runner": self.runner,
            "test": self.test,
            "lint": self.lint,
            "format": self.format,
            "build": self.build,
            "run": self.run,
            "typecheck": self.typecheck,
            "python": self.python,
            "venv": self.venv,
            "env_vars": self.env_vars,
            "src_dir": self.src_dir,
            "test_dir": self.test_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnvironmentConfig":
        return cls(
            runner=data.get("runner"),
            test=data.get("test"),
            lint=data.get("lint"),
            format=data.get("format"),
            build=data.get("build"),
            run=data.get("run"),
            typecheck=data.get("typecheck"),
            python=data.get("python"),
            venv=data.get("venv"),
            env_vars=data.get("env_vars", {}),
            src_dir=data.get("src_dir"),
            test_dir=data.get("test_dir"),
        )

    def get_command(self, name: str) -> Optional[str]:
        """Get a command by name."""
        return getattr(self, name, None)

    def set_command(self, name: str, value: str) -> None:
        """Set a command by name."""
        if hasattr(self, name):
            setattr(self, name, value)


@dataclass
class EnforcementConfig:
    """Enforcement behavior settings."""
    fail_closed: bool = False  # Block on hook errors instead of allowing (safer but may cause false positives)
    block_bash_writes: bool = False  # Block all Bash file writes (safest, requires all writes via tools)


@dataclass
class MultiAgentConfig:
    """Multi-agent execution settings."""
    enabled: bool = False
    max_concurrency: int = 3
    parallel_steps: bool = True


@dataclass
class WorkflowConfig:
    """Workflow behavior settings."""
    auto_commit: bool = True  # Auto-commit after completing tasks (prevents losing work)
    auto_push: bool = False   # Auto-push after commits (disabled by default for safety)


# ============================================================================
# GSD Configuration
# ============================================================================

# Model profile matrices - defines which model to use for each agent type
MODEL_PROFILES: Dict[str, Dict[str, ModelName]] = {
    "quality": {
        # High-quality: opus for researchers/planner/executor, sonnet for verifier
        "planner": "opus",
        "executor": "opus",
        "verifier": "sonnet",
        "plan-checker": "sonnet",
        "project-researcher": "opus",
        "phase-researcher": "opus",
        "research-synthesizer": "opus",
        "roadmapper": "opus",
        "debugger": "sonnet",
        "codebase-mapper": "sonnet",
        "integration-checker": "sonnet",
    },
    "balanced": {
        # Balanced: sonnet for most, haiku for researchers
        "planner": "sonnet",
        "executor": "sonnet",
        "verifier": "sonnet",
        "plan-checker": "sonnet",
        "project-researcher": "haiku",
        "phase-researcher": "haiku",
        "research-synthesizer": "sonnet",
        "roadmapper": "sonnet",
        "debugger": "sonnet",
        "codebase-mapper": "haiku",
        "integration-checker": "sonnet",
    },
    "budget": {
        # Budget: sonnet for planner/executor, haiku for others
        "planner": "sonnet",
        "executor": "sonnet",
        "verifier": "haiku",
        "plan-checker": "haiku",
        "project-researcher": "haiku",
        "phase-researcher": "haiku",
        "research-synthesizer": "haiku",
        "roadmapper": "haiku",
        "debugger": "haiku",
        "codebase-mapper": "haiku",
        "integration-checker": "haiku",
    },
}

# Agent types for validation
AGENT_TYPES = [
    "planner",
    "executor",
    "verifier",
    "plan-checker",
    "project-researcher",
    "phase-researcher",
    "research-synthesizer",
    "roadmapper",
    "debugger",
    "codebase-mapper",
    "integration-checker",
]

# Depth configurations
DEPTH_CONFIG: Dict[str, Dict[str, Any]] = {
    "quick": {
        "description": "Fast execution with minimal verification",
        "verification_level": 1,  # Existence only
        "max_retries": 1,
        "parallel_plans": True,
    },
    "standard": {
        "description": "Balanced execution with substantive verification",
        "verification_level": 2,  # Existence + Substantive
        "max_retries": 2,
        "parallel_plans": True,
    },
    "comprehensive": {
        "description": "Thorough execution with full verification",
        "verification_level": 3,  # Existence + Substantive + Wired
        "max_retries": 3,
        "parallel_plans": False,  # Sequential for full verification
    },
}


@dataclass
class GSDConfig:
    """GSD (Get Shit Done) methodology settings.

    Controls execution behavior for goal-backward planning and verification.
    """
    # Execution mode
    mode: GSDMode = "interactive"  # yolo: auto-proceed, interactive: confirm at checkpoints

    # Verification depth
    depth: GSDDepth = "standard"  # quick/standard/comprehensive

    # Parallelization
    parallelization: bool = True  # Run independent plans in parallel

    # Documentation commits
    commit_docs: bool = True  # Commit after writing/updating docs

    # Model profile for agent selection
    model_profile: ModelProfile = "balanced"  # quality/balanced/budget

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "depth": self.depth,
            "parallelization": self.parallelization,
            "commit_docs": self.commit_docs,
            "model_profile": self.model_profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GSDConfig":
        return cls(
            mode=data.get("mode", "interactive"),
            depth=data.get("depth", "standard"),
            parallelization=data.get("parallelization", True),
            commit_docs=data.get("commit_docs", True),
            model_profile=data.get("model_profile", "balanced"),
        )

    def get_model_for_agent(self, agent_type: str) -> ModelName:
        """Get the model to use for a specific agent type.

        Args:
            agent_type: One of the 11 agent types

        Returns:
            Model name: opus, sonnet, or haiku
        """
        profile = MODEL_PROFILES.get(self.model_profile, MODEL_PROFILES["balanced"])
        return profile.get(agent_type, "sonnet")

    def get_verification_level(self) -> int:
        """Get the verification level for current depth.

        Returns:
            1 = existence, 2 = substantive, 3 = wired
        """
        return DEPTH_CONFIG.get(self.depth, DEPTH_CONFIG["standard"])["verification_level"]

    def should_run_parallel(self) -> bool:
        """Check if plans should run in parallel.

        Returns:
            True if parallelization is enabled and depth allows it
        """
        depth_allows = DEPTH_CONFIG.get(self.depth, {}).get("parallel_plans", True)
        return self.parallelization and depth_allows

    def is_yolo(self) -> bool:
        """Check if running in yolo mode (auto-proceed)."""
        return self.mode == "yolo"

    def is_interactive(self) -> bool:
        """Check if running in interactive mode (confirm checkpoints)."""
        return self.mode == "interactive"


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

    # Environment settings (commands, paths, etc.)
    env: EnvironmentConfig = field(default_factory=EnvironmentConfig)

    # Enforcement settings
    enforcement: EnforcementConfig = field(default_factory=EnforcementConfig)

    # Multi-agent settings
    multi_agent: MultiAgentConfig = field(default_factory=MultiAgentConfig)

    # Workflow settings
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)

    # GSD methodology settings
    gsd: GSDConfig = field(default_factory=GSDConfig)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "tier": self.tier,
            "created_at": self.created_at,
            "graduated_at": self.graduated_at,
            "graduated_by": self.graduated_by,
            "env": self.env.to_dict(),
            "enforcement": asdict(self.enforcement),
            "multi_agent": asdict(self.multi_agent),
            "workflow": asdict(self.workflow),
            "gsd": self.gsd.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        ma_data = data.get("multi_agent", {})
        enf_data = data.get("enforcement", {})
        env_data = data.get("env", {})
        wf_data = data.get("workflow", {})
        gsd_data = data.get("gsd", {})
        return cls(
            mode=data.get("mode", "bootstrap"),
            tier=data.get("tier", "lite"),
            created_at=data.get("created_at"),
            graduated_at=data.get("graduated_at"),
            graduated_by=data.get("graduated_by"),
            env=EnvironmentConfig.from_dict(env_data),
            enforcement=EnforcementConfig(
                fail_closed=enf_data.get("fail_closed", False),
                block_bash_writes=enf_data.get("block_bash_writes", False),
            ),
            multi_agent=MultiAgentConfig(
                enabled=ma_data.get("enabled", False),
                max_concurrency=ma_data.get("max_concurrency", 3),
                parallel_steps=ma_data.get("parallel_steps", True),
            ),
            workflow=WorkflowConfig(
                auto_commit=wf_data.get("auto_commit", True),
                auto_push=wf_data.get("auto_push", False),
            ),
            gsd=GSDConfig.from_dict(gsd_data),
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


# ============================================================================
# Environment Management
# ============================================================================

def get_env(project_path: str) -> EnvironmentConfig:
    """Get environment config for a project."""
    config = load_config(project_path)
    return config.env


def set_env_command(project_path: str, command_name: str, value: str) -> ProjectConfig:
    """Set an environment command (test, lint, build, etc.).

    Args:
        project_path: Path to project root
        command_name: One of: runner, test, lint, format, build, run, typecheck, python, venv, src_dir, test_dir
        value: The command string or path

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)

    valid_fields = ["runner", "test", "lint", "format", "build", "run", "typecheck", "python", "venv", "src_dir", "test_dir"]
    if command_name not in valid_fields:
        raise ValueError(f"Invalid field: {command_name}. Must be one of: {', '.join(valid_fields)}")

    setattr(config.env, command_name, value)
    save_config(project_path, config)
    return config


def set_env_var(project_path: str, key: str, value: str) -> ProjectConfig:
    """Set an environment variable for the project.

    Args:
        project_path: Path to project root
        key: Environment variable name
        value: Environment variable value

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.env.env_vars[key] = value
    save_config(project_path, config)
    return config


def unset_env_var(project_path: str, key: str) -> ProjectConfig:
    """Remove an environment variable from the project.

    Args:
        project_path: Path to project root
        key: Environment variable name to remove

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.env.env_vars.pop(key, None)
    save_config(project_path, config)
    return config


def detect_environment(project_path: str) -> EnvironmentConfig:
    """Auto-detect environment settings from project files.

    Looks for:
    - pyproject.toml (uv/poetry)
    - requirements.txt (pip)
    - package.json (npm/pnpm/yarn)
    - Cargo.toml (cargo)
    - .venv, venv directories

    Args:
        project_path: Path to project root

    Returns:
        Detected EnvironmentConfig
    """
    p = Path(project_path)
    env = EnvironmentConfig()

    # Detect Python environments
    if (p / "pyproject.toml").exists():
        content = (p / "pyproject.toml").read_text()
        if "[tool.uv]" in content or "uv.lock" in [f.name for f in p.iterdir() if f.is_file()]:
            env.runner = "uv"
            env.test = "uv run pytest"
            env.lint = "uv run ruff check"
            env.format = "uv run ruff format"
            env.typecheck = "uv run mypy"
        elif "[tool.poetry]" in content:
            env.runner = "poetry"
            env.test = "poetry run pytest"
            env.lint = "poetry run ruff check"
            env.format = "poetry run ruff format"
        else:
            # Plain pyproject.toml, assume pip
            env.runner = "pip"
            env.test = "pytest"

    elif (p / "requirements.txt").exists():
        env.runner = "pip"
        env.test = "pytest"
        env.lint = "ruff check"
        env.format = "ruff format"

    # Detect venv
    for venv_name in [".venv", "venv", ".env"]:
        if (p / venv_name).is_dir():
            env.venv = venv_name
            env.python = f"{venv_name}/bin/python"
            break

    # Detect Node.js
    if (p / "package.json").exists():
        content = (p / "package.json").read_text()
        if (p / "pnpm-lock.yaml").exists():
            env.runner = "pnpm"
            env.test = "pnpm test"
            env.lint = "pnpm lint"
            env.build = "pnpm build"
        elif (p / "yarn.lock").exists():
            env.runner = "yarn"
            env.test = "yarn test"
            env.lint = "yarn lint"
            env.build = "yarn build"
        else:
            env.runner = "npm"
            env.test = "npm test"
            env.lint = "npm run lint"
            env.build = "npm run build"

    # Detect Rust
    if (p / "Cargo.toml").exists():
        env.runner = "cargo"
        env.test = "cargo test"
        env.lint = "cargo clippy"
        env.format = "cargo fmt"
        env.build = "cargo build --release"
        env.run = "cargo run"

    # Detect common directories
    for src_name in ["src", "lib", p.name]:
        if (p / src_name).is_dir():
            env.src_dir = src_name
            break

    for test_name in ["tests", "test", "spec"]:
        if (p / test_name).is_dir():
            env.test_dir = test_name
            break

    return env


def auto_detect_and_save(project_path: str) -> ProjectConfig:
    """Auto-detect environment and save to config.

    Args:
        project_path: Path to project root

    Returns:
        Updated ProjectConfig with detected environment
    """
    config = load_config(project_path)
    detected = detect_environment(project_path)

    # Only set values that were detected (don't overwrite existing)
    for field in ["runner", "test", "lint", "format", "build", "run", "typecheck", "python", "venv", "src_dir", "test_dir"]:
        detected_val = getattr(detected, field)
        current_val = getattr(config.env, field)
        if detected_val and not current_val:
            setattr(config.env, field, detected_val)

    save_config(project_path, config)
    return config


def format_env_summary(env: EnvironmentConfig) -> str:
    """Format environment config for display.

    Args:
        env: EnvironmentConfig to format

    Returns:
        Formatted string
    """
    lines = []

    if env.runner:
        lines.append(f"Runner: {env.runner}")

    commands = [
        ("test", env.test),
        ("lint", env.lint),
        ("format", env.format),
        ("build", env.build),
        ("run", env.run),
        ("typecheck", env.typecheck),
    ]

    if any(cmd for _, cmd in commands):
        lines.append("\nCommands:")
        for name, cmd in commands:
            if cmd:
                lines.append(f"  {name}: {cmd}")

    paths = [
        ("python", env.python),
        ("venv", env.venv),
        ("src_dir", env.src_dir),
        ("test_dir", env.test_dir),
    ]

    if any(path for _, path in paths):
        lines.append("\nPaths:")
        for name, path in paths:
            if path:
                lines.append(f"  {name}: {path}")

    if env.env_vars:
        lines.append("\nEnvironment Variables:")
        for key, val in env.env_vars.items():
            # Mask sensitive values
            display_val = val if len(val) < 20 else f"{val[:8]}...{val[-4:]}"
            lines.append(f"  {key}={display_val}")

    return "\n".join(lines) if lines else "(not configured)"


# ============================================================================
# Workflow Settings
# ============================================================================

def get_auto_commit(project_path: str) -> bool:
    """Check if auto-commit is enabled for a project.

    Args:
        project_path: Path to project root

    Returns:
        True if auto-commit is enabled (default: True)
    """
    config = load_config(project_path)
    return config.workflow.auto_commit


def set_auto_commit(project_path: str, enabled: bool) -> ProjectConfig:
    """Enable or disable auto-commit for a project.

    Args:
        project_path: Path to project root
        enabled: Whether to enable auto-commit

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.workflow.auto_commit = enabled
    save_config(project_path, config)
    return config


def get_auto_push(project_path: str) -> bool:
    """Check if auto-push is enabled for a project.

    Args:
        project_path: Path to project root

    Returns:
        True if auto-push is enabled (default: False)
    """
    config = load_config(project_path)
    return config.workflow.auto_push


def set_auto_push(project_path: str, enabled: bool) -> ProjectConfig:
    """Enable or disable auto-push for a project.

    Args:
        project_path: Path to project root
        enabled: Whether to enable auto-push

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.workflow.auto_push = enabled
    save_config(project_path, config)
    return config


# ============================================================================
# GSD Settings
# ============================================================================

def get_gsd_config(project_path: str) -> GSDConfig:
    """Get GSD configuration for a project.

    Args:
        project_path: Path to project root

    Returns:
        GSDConfig
    """
    config = load_config(project_path)
    return config.gsd


def set_gsd_mode(project_path: str, mode: GSDMode) -> ProjectConfig:
    """Set GSD execution mode.

    Args:
        project_path: Path to project root
        mode: "yolo" (auto-proceed) or "interactive" (confirm checkpoints)

    Returns:
        Updated ProjectConfig
    """
    if mode not in ("yolo", "interactive"):
        raise ValueError(f"Invalid GSD mode: {mode}. Must be 'yolo' or 'interactive'")

    config = load_config(project_path)
    config.gsd.mode = mode
    save_config(project_path, config)
    return config


def set_gsd_depth(project_path: str, depth: GSDDepth) -> ProjectConfig:
    """Set GSD verification depth.

    Args:
        project_path: Path to project root
        depth: "quick", "standard", or "comprehensive"

    Returns:
        Updated ProjectConfig
    """
    if depth not in ("quick", "standard", "comprehensive"):
        raise ValueError(f"Invalid depth: {depth}. Must be 'quick', 'standard', or 'comprehensive'")

    config = load_config(project_path)
    config.gsd.depth = depth
    save_config(project_path, config)
    return config


def set_model_profile(project_path: str, profile: ModelProfile) -> ProjectConfig:
    """Set model profile for agent selection.

    Args:
        project_path: Path to project root
        profile: "quality", "balanced", or "budget"

    Returns:
        Updated ProjectConfig
    """
    if profile not in ("quality", "balanced", "budget"):
        raise ValueError(f"Invalid profile: {profile}. Must be 'quality', 'balanced', or 'budget'")

    config = load_config(project_path)
    config.gsd.model_profile = profile
    save_config(project_path, config)
    return config


def set_parallelization(project_path: str, enabled: bool) -> ProjectConfig:
    """Enable or disable plan parallelization.

    Args:
        project_path: Path to project root
        enabled: Whether to enable parallel execution

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.gsd.parallelization = enabled
    save_config(project_path, config)
    return config


def set_commit_docs(project_path: str, enabled: bool) -> ProjectConfig:
    """Enable or disable doc commits.

    Args:
        project_path: Path to project root
        enabled: Whether to commit after doc updates

    Returns:
        Updated ProjectConfig
    """
    config = load_config(project_path)
    config.gsd.commit_docs = enabled
    save_config(project_path, config)
    return config


def get_model_for_agent(project_path: str, agent_type: str) -> ModelName:
    """Get the model to use for a specific agent type.

    Uses the project's configured model profile to select the appropriate
    model for each agent type.

    Args:
        project_path: Path to project root
        agent_type: One of the 11 agent types:
            - planner, executor, verifier, plan-checker
            - project-researcher, phase-researcher, research-synthesizer
            - roadmapper, debugger, codebase-mapper, integration-checker

    Returns:
        Model name: "opus", "sonnet", or "haiku"
    """
    config = load_config(project_path)
    return config.gsd.get_model_for_agent(agent_type)


def format_gsd_summary(gsd: GSDConfig) -> str:
    """Format GSD config for display.

    Args:
        gsd: GSDConfig to format

    Returns:
        Formatted string
    """
    lines = [
        "GSD Settings",
        "=" * 40,
        f"Mode: {gsd.mode}",
        f"Depth: {gsd.depth}",
        f"Model Profile: {gsd.model_profile}",
        f"Parallelization: {'enabled' if gsd.parallelization else 'disabled'}",
        f"Commit Docs: {'enabled' if gsd.commit_docs else 'disabled'}",
        "",
        f"Verification Level: {gsd.get_verification_level()} ({'existence' if gsd.get_verification_level() == 1 else 'substantive' if gsd.get_verification_level() == 2 else 'wired'})",
        f"Parallel Execution: {'yes' if gsd.should_run_parallel() else 'no'}",
    ]
    return "\n".join(lines)


def format_model_profile_summary(profile: ModelProfile) -> str:
    """Format model profile for display.

    Args:
        profile: Model profile name

    Returns:
        Formatted string showing agent → model mapping
    """
    if profile not in MODEL_PROFILES:
        return f"Unknown profile: {profile}"

    mapping = MODEL_PROFILES[profile]
    lines = [
        f"Model Profile: {profile}",
        "=" * 40,
    ]

    for agent_type in AGENT_TYPES:
        model = mapping.get(agent_type, "sonnet")
        lines.append(f"  {agent_type}: {model}")

    return "\n".join(lines)
