"""
One-command setup for Claude Code integration.

Usage:
    eri-rpg install    # Install commands and hooks
    eri-rpg uninstall  # Remove everything cleanly
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional


def get_erirpg_root() -> Path:
    """Get the EriRPG installation root."""
    return Path(__file__).parent.parent


def install_claude_code(verbose: bool = True) -> bool:
    """
    Install EriRPG commands and hooks for Claude Code.

    Returns:
        True if successful
    """
    home = Path.home()
    claude_dir = home / ".claude"
    commands_dir = claude_dir / "commands" / "eri"
    settings_file = claude_dir / "settings.json"

    erirpg_root = get_erirpg_root()

    # Create directories
    commands_dir.mkdir(parents=True, exist_ok=True)

    # Copy command files from commands/eri/ in repo
    src_commands = erirpg_root / "commands" / "eri"
    commands_installed = []

    if src_commands.exists():
        # Copy top-level commands
        for cmd in src_commands.glob("*.md"):
            shutil.copy(cmd, commands_dir / cmd.name)
            commands_installed.append(f"/eri:{cmd.stem}")
            if verbose:
                print(f"  Installed: /eri:{cmd.stem}")

        # Copy help subdirectory if it exists
        src_help = src_commands / "help"
        if src_help.exists():
            dest_help = commands_dir / "help"
            dest_help.mkdir(parents=True, exist_ok=True)
            for cmd in src_help.glob("*.md"):
                shutil.copy(cmd, dest_help / cmd.name)
                commands_installed.append(f"/eri:help:{cmd.stem}")
                if verbose:
                    print(f"  Installed: /eri:help:{cmd.stem}")
    else:
        # Create default commands if source doesn't exist
        _create_default_commands(commands_dir, verbose)
        commands_installed = ["/eri:execute", "/eri:quick", "/eri:status"]

    # Update settings.json with hooks
    hooks_config = {
        "PreToolUse": [{
            "matcher": "Edit|Write|MultiEdit|Bash",
            "hooks": [{
                "type": "command",
                "command": f"python3 {erirpg_root}/erirpg/hooks/pretooluse.py",
                "timeout": 5
            }]
        }],
        "PreCompact": [{
            "matcher": ".*",
            "hooks": [{
                "type": "command",
                "command": f"python3 {erirpg_root}/erirpg/hooks/precompact.py",
                "timeout": 10
            }]
        }],
        "SessionStart": [{
            "matcher": ".*",
            "hooks": [{
                "type": "command",
                "command": f"python3 {erirpg_root}/erirpg/hooks/sessionstart.py",
                "timeout": 5
            }]
        }]
    }

    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    # Merge hooks (don't overwrite existing non-erirpg hooks)
    existing_hooks = settings.get("hooks", {})

    for hook_type, hook_list in hooks_config.items():
        if hook_type not in existing_hooks:
            existing_hooks[hook_type] = []

        # Remove any existing erirpg hooks
        existing_hooks[hook_type] = [
            h for h in existing_hooks[hook_type]
            if "erirpg" not in str(h.get("hooks", [{}])[0].get("command", ""))
        ]

        # Add new erirpg hooks
        existing_hooks[hook_type].extend(hook_list)

    settings["hooks"] = existing_hooks
    settings_file.write_text(json.dumps(settings, indent=2))

    if verbose:
        print(f"\nUpdated: {settings_file}")
        print(f"\nInstalled hooks:")
        print(f"  PreToolUse  - Enforces EriRPG workflow")
        print(f"  PreCompact  - Saves state before compaction")
        print(f"  SessionStart - Reminds about incomplete runs")
        print(f"\nCommands: {', '.join(commands_installed)}")
        print(f"\nRestart Claude Code to load changes.")

    return True


def uninstall_claude_code(verbose: bool = True) -> bool:
    """
    Remove EriRPG from Claude Code.

    Returns:
        True if successful
    """
    home = Path.home()
    commands_dir = home / ".claude" / "commands" / "eri"
    settings_file = home / ".claude" / "settings.json"

    removed_items = []

    # Remove commands
    if commands_dir.exists():
        shutil.rmtree(commands_dir)
        removed_items.append(f"Commands: {commands_dir}")
        if verbose:
            print(f"Removed: {commands_dir}")

    # Remove hooks from settings
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())

            if "hooks" in settings:
                for hook_type in ["PreToolUse", "PreCompact", "SessionStart"]:
                    if hook_type in settings["hooks"]:
                        original_count = len(settings["hooks"][hook_type])
                        settings["hooks"][hook_type] = [
                            h for h in settings["hooks"][hook_type]
                            if "erirpg" not in str(h.get("hooks", [{}])[0].get("command", ""))
                        ]
                        if len(settings["hooks"][hook_type]) < original_count:
                            removed_items.append(f"Hook: {hook_type}")

                # Clean up empty hook lists
                settings["hooks"] = {
                    k: v for k, v in settings["hooks"].items() if v
                }
                if not settings["hooks"]:
                    del settings["hooks"]

                settings_file.write_text(json.dumps(settings, indent=2))
                if verbose:
                    print(f"Updated: {settings_file}")
        except (json.JSONDecodeError, KeyError) as e:
            pass  # Invalid settings, skip

    if verbose:
        if removed_items:
            print(f"\nRemoved:")
            for item in removed_items:
                print(f"  {item}")
        else:
            print("Nothing to remove.")
        print("\nEriRPG removed from Claude Code.")

    return True


def _create_default_commands(commands_dir: Path, verbose: bool = True) -> None:
    """Create default slash commands if source doesn't exist."""

    execute_cmd = '''# /eri:execute - Execute EriRPG workflow

Run the EriRPG agent loop for the current task.

## Usage

When the user wants to make code changes, use this workflow:

1. **Start a run**: `eri-rpg goal-plan <project> "<goal>"`
2. **Execute steps**: Follow the generated spec
3. **Complete**: `eri-rpg goal-status <project>`

## Quick Fix Mode

For simple single-file edits:

```bash
eri-rpg quick <project> <file> "<description>"
# Make edits...
eri-rpg quick-done <project>
```
'''

    quick_cmd = '''# /eri:quick - Quick fix mode

Start a quick fix for a single file.

## Usage

```bash
eri-rpg quick <project> <file> "<description>"
```

Then edit the file. When done:

```bash
eri-rpg quick-done <project>
```

To cancel and restore:

```bash
eri-rpg quick-cancel <project>
```
'''

    status_cmd = '''# /eri:status - Show EriRPG status

Check current EriRPG state.

## Commands

```bash
# Show registered projects
eri-rpg list

# Show runs for a project
eri-rpg runs <project>

# Show quick fix status
eri-rpg quick-status <project>

# Cleanup old runs
eri-rpg cleanup <project> --prune
```
'''

    (commands_dir / "execute.md").write_text(execute_cmd)
    (commands_dir / "quick.md").write_text(quick_cmd)
    (commands_dir / "status.md").write_text(status_cmd)

    if verbose:
        print("  Created: /eri:execute")
        print("  Created: /eri:quick")
        print("  Created: /eri:status")


def install_commands(verbose: bool = True) -> bool:
    """
    Install/sync only slash commands (no hooks).

    Copies commands from repo's commands/eri/ to ~/.claude/commands/eri/

    Returns:
        True if successful
    """
    home = Path.home()
    commands_dir = home / ".claude" / "commands" / "eri"
    erirpg_root = get_erirpg_root()
    src_commands = erirpg_root / "commands" / "eri"

    if not src_commands.exists():
        if verbose:
            print(f"Source not found: {src_commands}")
        return False

    # Create target directory
    commands_dir.mkdir(parents=True, exist_ok=True)

    commands_installed = []

    # Copy top-level commands
    for cmd in src_commands.glob("*.md"):
        shutil.copy(cmd, commands_dir / cmd.name)
        commands_installed.append(f"/eri:{cmd.stem}")
        if verbose:
            print(f"  Synced: /eri:{cmd.stem}")

    # Copy help subdirectory
    src_help = src_commands / "help"
    if src_help.exists():
        dest_help = commands_dir / "help"
        dest_help.mkdir(parents=True, exist_ok=True)
        for cmd in src_help.glob("*.md"):
            shutil.copy(cmd, dest_help / cmd.name)
            commands_installed.append(f"/eri:help:{cmd.stem}")
            if verbose:
                print(f"  Synced: /eri:help:{cmd.stem}")

    if verbose:
        print(f"\nSynced {len(commands_installed)} commands to {commands_dir}")

    return True


def check_installation() -> dict:
    """
    Check current installation status.

    Returns:
        Dict with installation status
    """
    home = Path.home()
    claude_dir = home / ".claude"
    commands_dir = claude_dir / "commands" / "eri"
    settings_file = claude_dir / "settings.json"

    status = {
        "commands_installed": False,
        "commands": [],
        "hooks_installed": False,
        "hooks": [],
    }

    # Check commands
    if commands_dir.exists():
        cmds = list(commands_dir.glob("*.md"))
        if cmds:
            status["commands_installed"] = True
            status["commands"] = [f"/eri:{c.stem}" for c in cmds]

    # Check hooks
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            hooks = settings.get("hooks", {})

            for hook_type in ["PreToolUse", "PreCompact", "SessionStart"]:
                if hook_type in hooks:
                    for h in hooks[hook_type]:
                        cmd = h.get("hooks", [{}])[0].get("command", "")
                        if "erirpg" in cmd:
                            status["hooks_installed"] = True
                            status["hooks"].append(hook_type)
        except (json.JSONDecodeError, KeyError) as e:
            pass  # Invalid settings, skip

    return status


# CLI integration
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python install.py [install|uninstall|status]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "install":
        install_claude_code()
    elif cmd == "uninstall":
        uninstall_claude_code()
    elif cmd == "status":
        status = check_installation()
        print("EriRPG Installation Status:")
        print(f"  Commands: {status['commands'] if status['commands_installed'] else 'Not installed'}")
        print(f"  Hooks: {status['hooks'] if status['hooks_installed'] else 'Not installed'}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
