"""
EriRPG Commands - Individual command modules for /coder:* skills.

Each module is a standalone command that can be called via CLI:
    python -m erirpg.commands.{command} [args]

Pattern:
- .md skill in ~/.claude/commands/coder/ tells Claude Code the workflow
- .py module here does the actual operations (git, file, state, metrics)
- Claude Code calls these via CLI, not inline logic

Commands are organized by category:
- Core Workflow: new_project, plan_phase, execute_phase, verify_work, complete_milestone
- Phase Management: add_phase, insert_phase, remove_phase, discuss_phase
- Navigation: progress, help, settings, resume, pause
- Utilities: quick, debug, add_todo, map_codebase
- Git Operations: rollback, diff, compare
- Analysis: cost, metrics, history, list_phase_assumptions, plan_milestone_gaps
- Plan Operations: split, merge, replay
- Knowledge: learn, template, handoff
- Project: add_feature, new_milestone

Also exports legacy command system (parse_command, is_command, get_help_text)
for backward compatibility with erirpg core.
"""

# Legacy exports for backward compatibility with erirpg core
from erirpg.commands.legacy import (
    parse_command,
    is_command,
    get_help_text,
    get_command_names,
    COMMANDS,
    ALIAS_MAP,
    CommandConfig,
    ParsedCommand,
)

__all__ = [
    # Legacy exports
    'parse_command',
    'is_command',
    'get_help_text',
    'get_command_names',
    'COMMANDS',
    'ALIAS_MAP',
    'CommandConfig',
    'ParsedCommand',
    # Core Workflow
    'new_project',
    'plan_phase',
    'execute_phase',
    'verify_work',
    'complete_milestone',
    # Phase Management
    'add_phase',
    'insert_phase',
    'remove_phase',
    'discuss_phase',
    # Navigation
    'progress',
    'help',
    'settings',
    'resume',
    'pause',
    # Utilities
    'quick',
    'debug',
    'add_todo',
    'map_codebase',
    # Git Operations
    'rollback',
    'diff',
    'compare',
    # Analysis
    'cost',
    'metrics',
    'history',
    'list_phase_assumptions',
    'plan_milestone_gaps',
    # Plan Operations
    'split',
    'merge',
    'replay',
    # Knowledge
    'learn',
    'template',
    'handoff',
    # Project
    'add_feature',
    'new_milestone',
]
