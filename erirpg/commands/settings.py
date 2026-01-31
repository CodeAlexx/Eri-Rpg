#!/usr/bin/env python3
"""
/coder:settings - Configure workflow preferences.

Manages:
- Mode (interactive, autonomous)
- Depth (minimal, standard, thorough)
- Parallelization
- Model profile
- Workflow options

Usage:
    python -m erirpg.commands.settings [--json]
    python -m erirpg.commands.settings --set <key>=<value> [--json]
    python -m erirpg.commands.settings --reset [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder import load_config, save_config, get_default_config, ensure_planning_dir


def settings(
    get_all: bool = True,
    set_value: Optional[str] = None,
    reset: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Manage project settings."""
    if project_path is None:
        project_path = Path.cwd()

    ensure_planning_dir(project_path)

    result = {
        "command": "settings",
        "project": str(project_path),
    }

    if reset:
        # Reset to defaults
        config = get_default_config()
        save_config(config, project_path)
        result["action"] = "reset"
        result["config"] = config
        result["message"] = "Settings reset to defaults"

    elif set_value:
        # Set a specific value
        config = load_config(project_path)

        if "=" not in set_value:
            result["error"] = "Invalid format. Use key=value"
        else:
            key, value = set_value.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Parse value type
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)

            # Handle nested keys
            if "." in key:
                parts = key.split(".")
                target = config
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = value
            else:
                config[key] = value

            save_config(config, project_path)
            result["action"] = "set"
            result["key"] = key
            result["value"] = value
            result["config"] = config

    else:
        # Get all settings
        config = load_config(project_path)
        result["action"] = "get"
        result["config"] = config

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    reset = "--reset" in sys.argv

    # Parse --set argument
    set_value = None
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        if idx + 1 < len(sys.argv):
            set_value = sys.argv[idx + 1]

    settings(
        set_value=set_value,
        reset=reset,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
