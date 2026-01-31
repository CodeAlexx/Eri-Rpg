"""
Original slash command system for EriRPG.

This module contains the original command parsing used by erirpg core.
Kept separate from the new /coder:* command modules.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from erirpg.workflow import Stage
from erirpg.persona import Persona


@dataclass
class CommandConfig:
    """Configuration for a slash command."""
    description: str
    stage: Optional[Stage] = None
    persona: Optional[Persona] = None
    action: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "stage": self.stage.name if self.stage else None,
            "persona": self.persona.name if self.persona else None,
            "action": self.action,
            "flags": self.flags,
            "aliases": self.aliases,
        }


@dataclass
class ParsedCommand:
    """Result of parsing user input."""
    name: str
    config: CommandConfig
    args: List[str]
    flags: Dict[str, Any]
    raw_input: str = ""

    def has_flag(self, flag: str) -> bool:
        """Check if a flag was provided."""
        return flag in self.flags

    def get_flag(self, flag: str, default: Any = None) -> Any:
        """Get flag value with default."""
        return self.flags.get(flag, default)


# Core commands - deliberately minimal compared to SuperClaude's 30
COMMANDS: Dict[str, CommandConfig] = {
    # Workflow stages - each sets stage AND appropriate persona
    "/analyze": CommandConfig(
        description="Understand codebase structure, detect patterns",
        stage=Stage.ANALYZE,
        flags=["--deep", "--focus", "--module"],
        aliases=["/a", "/analyse"],
    ),
    "/discuss": CommandConfig(
        description="Plan approach, generate roadmap with must_haves",
        stage=Stage.DISCUSS,
        flags=["--roadmap", "--estimate", "--quick"],
        aliases=["/d", "/plan"],
    ),
    "/implement": CommandConfig(
        description="Write code following the plan",
        stage=Stage.IMPLEMENT,
        flags=["--test", "--dry-run", "--step"],
        aliases=["/i", "/build", "/code"],
    ),
    "/review": CommandConfig(
        description="Critique, find issues, suggest improvements",
        stage=Stage.REVIEW,
        flags=["--security", "--perf", "--thorough", "--diff"],
        aliases=["/r", "/check"],
    ),
    "/debug": CommandConfig(
        description="Investigate problems, find root cause",
        stage=Stage.DEBUG,
        flags=["--trace", "--hypothesis", "--bisect"],
        aliases=["/db", "/fix"],
    ),

    # Persona overrides - when you need a specific lens regardless of stage
    "/architect": CommandConfig(
        description="Switch to architect perspective (systems, tradeoffs)",
        persona=Persona.ARCHITECT,
        aliases=["/arch"],
    ),
    "/dev": CommandConfig(
        description="Switch to developer perspective (pragmatic, ship it)",
        persona=Persona.DEV,
    ),
    "/critic": CommandConfig(
        description="Switch to critic perspective (find issues)",
        persona=Persona.CRITIC,
    ),
    "/analyst": CommandConfig(
        description="Switch to analyst perspective (root cause)",
        persona=Persona.ANALYST,
    ),
    "/mentor": CommandConfig(
        description="Switch to mentor/teaching mode (explain)",
        persona=Persona.MENTOR,
        aliases=["/teach", "/explain"],
    ),

    # Project management
    "/roadmap": CommandConfig(
        description="Show current roadmap and progress",
        action="show_roadmap",
        aliases=["/rm"],
    ),
    "/status": CommandConfig(
        description="Show session status, decisions, learnings",
        action="show_status",
        aliases=["/st", "/s"],
    ),
    "/learn": CommandConfig(
        description="Capture a learning/pattern for future sessions",
        action="capture_learning",
        aliases=["/l"],
    ),
    "/context": CommandConfig(
        description="Output current CLAUDE.md context",
        action="show_context",
        aliases=["/ctx"],
    ),
    "/help": CommandConfig(
        description="Show available commands",
        action="show_help",
        aliases=["/h", "/?"],
    ),
    "/reset": CommandConfig(
        description="Reset to idle state",
        action="reset_state",
    ),
}


def _build_alias_map() -> Dict[str, str]:
    """Build map from aliases to canonical command names."""
    alias_map = {}
    for cmd_name, config in COMMANDS.items():
        for alias in config.aliases:
            alias_map[alias] = cmd_name
    return alias_map


ALIAS_MAP = _build_alias_map()


def parse_command(user_input: str) -> Optional[ParsedCommand]:
    """
    Parse slash command from user input.
    Returns None if not a command.

    Examples:
        /analyze --deep src/
        /implement --test
        /architect
        /help
    """
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None

    parts = stripped.split()
    cmd_name = parts[0].lower()

    # Resolve aliases
    if cmd_name in ALIAS_MAP:
        cmd_name = ALIAS_MAP[cmd_name]

    if cmd_name not in COMMANDS:
        return None

    config = COMMANDS[cmd_name]
    args = []
    flags = {}

    # Parse remaining parts
    i = 1
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            flag_name = part[2:]
            # Check if next part is a value (not another flag)
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                flags[flag_name] = parts[i + 1]
                i += 2
            else:
                flags[flag_name] = True
                i += 1
        elif part.startswith("-") and len(part) == 2:
            # Short flag like -v
            flags[part[1]] = True
            i += 1
        else:
            args.append(part)
            i += 1

    return ParsedCommand(
        name=cmd_name,
        config=config,
        args=args,
        flags=flags,
        raw_input=user_input,
    )


def is_command(user_input: str) -> bool:
    """Check if input looks like a command."""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return False
    cmd = stripped.split()[0].lower()
    return cmd in COMMANDS or cmd in ALIAS_MAP


def get_help_text() -> str:
    """Generate help text for all commands."""
    lines = ["# EriRPG Commands\n"]

    # Group by type
    workflow_cmds = {k: v for k, v in COMMANDS.items() if v.stage}
    persona_cmds = {k: v for k, v in COMMANDS.items() if v.persona}
    action_cmds = {k: v for k, v in COMMANDS.items() if v.action}

    lines.append("## Workflow Stages")
    lines.append("*Each stage sets both workflow phase AND appropriate persona*\n")
    for cmd, cfg in workflow_cmds.items():
        flags_str = f" [{', '.join('--' + f for f in cfg.flags)}]" if cfg.flags else ""
        aliases = f" (aliases: {', '.join(cfg.aliases)})" if cfg.aliases else ""
        lines.append(f"  `{cmd}`{flags_str}")
        lines.append(f"    {cfg.description}{aliases}")

    lines.append("\n## Persona Overrides")
    lines.append("*Override persona without changing workflow stage*\n")
    for cmd, cfg in persona_cmds.items():
        aliases = f" (aliases: {', '.join(cfg.aliases)})" if cfg.aliases else ""
        lines.append(f"  `{cmd}` - {cfg.description}{aliases}")

    lines.append("\n## Project Management")
    for cmd, cfg in action_cmds.items():
        aliases = f" (aliases: {', '.join(cfg.aliases)})" if cfg.aliases else ""
        lines.append(f"  `{cmd}` - {cfg.description}{aliases}")

    return "\n".join(lines)


def get_command_names() -> List[str]:
    """Get all command names including aliases."""
    names = list(COMMANDS.keys())
    names.extend(ALIAS_MAP.keys())
    return sorted(set(names))
