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
"""

__all__ = [
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
