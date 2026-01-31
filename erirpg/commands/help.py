#!/usr/bin/env python3
"""
/coder:help - Command reference and usage.

Displays:
- Available commands
- Command descriptions
- Usage examples

Usage:
    python -m erirpg.commands.help [--json]
    python -m erirpg.commands.help <command> [--json]
"""

import json
import sys
from typing import Optional


COMMANDS = {
    # Core Workflow
    "new-project": {
        "description": "Initialize a new project with research, requirements, and roadmap",
        "usage": "/coder:new-project",
        "category": "Core Workflow"
    },
    "plan-phase": {
        "description": "Create executable plans for a phase",
        "usage": "/coder:plan-phase <phase-number>",
        "category": "Core Workflow"
    },
    "execute-phase": {
        "description": "Execute all plans for a phase",
        "usage": "/coder:execute-phase <phase-number>",
        "category": "Core Workflow"
    },
    "verify-work": {
        "description": "Manual user acceptance testing",
        "usage": "/coder:verify-work <phase-number>",
        "category": "Core Workflow"
    },
    "complete-milestone": {
        "description": "Archive milestone and tag release",
        "usage": "/coder:complete-milestone",
        "category": "Core Workflow"
    },

    # Phase Management
    "add-phase": {
        "description": "Append a new phase to the roadmap",
        "usage": "/coder:add-phase <name>",
        "category": "Phase Management"
    },
    "insert-phase": {
        "description": "Insert urgent work between phases",
        "usage": "/coder:insert-phase <position> <name>",
        "category": "Phase Management"
    },
    "remove-phase": {
        "description": "Remove a future phase",
        "usage": "/coder:remove-phase <phase-number>",
        "category": "Phase Management"
    },
    "discuss-phase": {
        "description": "Capture implementation decisions for a phase",
        "usage": "/coder:discuss-phase <phase-number>",
        "category": "Phase Management"
    },
    "list-phase-assumptions": {
        "description": "See Claude's approach for a phase",
        "usage": "/coder:list-phase-assumptions <phase-number>",
        "category": "Phase Management"
    },
    "plan-milestone-gaps": {
        "description": "Create phases for audit gaps",
        "usage": "/coder:plan-milestone-gaps",
        "category": "Phase Management"
    },

    # Navigation
    "progress": {
        "description": "Show current position and metrics",
        "usage": "/coder:progress",
        "category": "Navigation"
    },
    "help": {
        "description": "Show this help",
        "usage": "/coder:help [command]",
        "category": "Navigation"
    },
    "settings": {
        "description": "Configure workflow preferences",
        "usage": "/coder:settings [--set key=value]",
        "category": "Navigation"
    },
    "resume": {
        "description": "Restore from last session",
        "usage": "/coder:resume",
        "category": "Navigation"
    },
    "pause": {
        "description": "Create handoff state when stopping",
        "usage": "/coder:pause [reason]",
        "category": "Navigation"
    },

    # Utilities
    "quick": {
        "description": "Ad-hoc task with coder guarantees",
        "usage": "/coder:quick <description>",
        "category": "Utilities"
    },
    "debug": {
        "description": "Systematic debugging with scientific method",
        "usage": "/coder:debug <symptom>",
        "category": "Utilities"
    },
    "add-todo": {
        "description": "Capture idea for later",
        "usage": "/coder:add-todo <idea>",
        "category": "Utilities"
    },
    "map-codebase": {
        "description": "Analyze existing codebase (brownfield)",
        "usage": "/coder:map-codebase",
        "category": "Utilities"
    },
    "add-feature": {
        "description": "Add feature to existing codebase",
        "usage": "/coder:add-feature <description>",
        "category": "Utilities"
    },
    "new-milestone": {
        "description": "Start next version",
        "usage": "/coder:new-milestone <version>",
        "category": "Utilities"
    },

    # Git Operations
    "rollback": {
        "description": "Undo execution via git",
        "usage": "/coder:rollback [--to <commit>]",
        "category": "Git Operations"
    },
    "diff": {
        "description": "Show changes since checkpoint",
        "usage": "/coder:diff [checkpoint]",
        "category": "Git Operations"
    },
    "compare": {
        "description": "Compare approaches/branches",
        "usage": "/coder:compare <branch1> <branch2>",
        "category": "Git Operations"
    },

    # Analysis
    "cost": {
        "description": "Estimate tokens and cost",
        "usage": "/coder:cost [--phase <n>]",
        "category": "Analysis"
    },
    "metrics": {
        "description": "Track execution metrics",
        "usage": "/coder:metrics",
        "category": "Analysis"
    },
    "history": {
        "description": "Execution history",
        "usage": "/coder:history",
        "category": "Analysis"
    },

    # Plan Operations
    "split": {
        "description": "Break plan into smaller plans",
        "usage": "/coder:split <plan-file>",
        "category": "Plan Operations"
    },
    "merge": {
        "description": "Combine multiple plans",
        "usage": "/coder:merge <plan1> <plan2>",
        "category": "Plan Operations"
    },
    "replay": {
        "description": "Re-run phase with different parameters",
        "usage": "/coder:replay <phase-number>",
        "category": "Plan Operations"
    },

    # Knowledge
    "learn": {
        "description": "Pattern extraction to knowledge graph",
        "usage": "/coder:learn <pattern>",
        "category": "Knowledge"
    },
    "template": {
        "description": "Save as reusable template",
        "usage": "/coder:template <name>",
        "category": "Knowledge"
    },
    "handoff": {
        "description": "Generate context documentation",
        "usage": "/coder:handoff",
        "category": "Knowledge"
    },
}


def help_command(
    command: Optional[str] = None,
    output_json: bool = False
) -> dict:
    """Show command help."""
    result = {
        "command": "help",
    }

    if command:
        # Show specific command help
        cmd_key = command.replace("/coder:", "").replace("coder:", "")
        if cmd_key in COMMANDS:
            result["command_help"] = {
                "name": cmd_key,
                **COMMANDS[cmd_key]
            }
        else:
            result["error"] = f"Unknown command: {command}"
            result["available_commands"] = list(COMMANDS.keys())
    else:
        # Show all commands grouped by category
        categories = {}
        for name, info in COMMANDS.items():
            cat = info["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": name,
                "description": info["description"],
                "usage": info["usage"]
            })
        result["categories"] = categories
        result["total_commands"] = len(COMMANDS)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    command = args[0] if args else None
    help_command(command=command, output_json=output_json)


if __name__ == "__main__":
    main()
