#!/usr/bin/env python3
"""
EriRPG PreToolUse Hook - HARD ENFORCEMENT

This hook is called by Claude Code BEFORE any Edit/Write/Bash tool executes.
It checks if there's an active EriRPG run with preflight completed.

For Edit/Write/MultiEdit: Blocks without preflight.
For Bash: Detects file-writing commands (cat >, echo >, tee, etc.) and enforces same rules.

If not: BLOCKS the operation.
If yes: Allows but only for preflighted files.

To install, add to ~/.claude/settings.json:
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m erirpg.hooks.pretooluse",
            "timeout": 5
          }
        ]
      }
    ]
  }
}

Or with explicit path (set ERIRPG_ROOT env var):
  "command": "ERIRPG_ROOT=/path/to/eri-rpg python3 ${ERIRPG_ROOT}/erirpg/hooks/pretooluse.py"
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Portable path resolution - use Path(__file__).parent
HOOK_DIR = Path(__file__).parent.resolve()
ERIRPG_ROOT = os.environ.get('ERIRPG_ROOT', str(HOOK_DIR.parent.parent))
LOG_FILE = "/tmp/erirpg-hook.log"


def log(msg: str):
    """Log to file for debugging."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)  # Can't log, ignore


def get_active_run_state(project_path: str) -> dict:
    """Check for active EriRPG run in project."""
    run_dir = Path(project_path) / ".eri-rpg" / "runs"
    if not run_dir.exists():
        return None

    # Find most recent run
    runs = list(run_dir.glob("*.json"))
    if not runs:
        return None

    # Get latest by mtime
    latest = max(runs, key=lambda p: p.stat().st_mtime)

    try:
        with open(latest) as f:
            run_state = json.load(f)

        # Check if run is still in progress
        if run_state.get("completed_at") is None:
            return run_state
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr)

    return None


def get_preflight_state(project_path: str) -> dict:
    """Check for active preflight state."""
    preflight_file = Path(project_path) / ".eri-rpg" / "preflight_state.json"
    if not preflight_file.exists():
        return None

    try:
        with open(preflight_file) as f:
            return json.load(f)
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr); return None


def get_quick_fix_state(project_path: str) -> dict:
    """Check for active quick fix state."""
    quick_fix_file = Path(project_path) / ".eri-rpg" / "quick_fix_state.json"
    if not quick_fix_file.exists():
        return None

    try:
        with open(quick_fix_file) as f:
            return json.load(f)
    except Exception as e:
        import sys; print(f"[EriRPG] {e}", file=sys.stderr); return None


def get_project_mode(project_path: str) -> str:
    """Get the operational mode for a project.

    Returns "bootstrap" (no enforcement) or "maintain" (full enforcement).
    Handles migration: projects with learnings default to maintain.
    """
    config_file = Path(project_path) / ".eri-rpg" / "config.json"

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


def detect_bash_file_write(command: str) -> str:
    """Detect if a Bash command writes to a file. Returns the file path or None."""
    import re

    # Patterns that indicate file writing
    patterns = [
        # cat/echo with redirection: cat > file, echo "x" > file, cat >> file
        r'(?:cat|echo|printf)\s+.*?[>]{1,2}\s*["\']?([^"\'>\s|&;]+)',
        # Here-doc: cat > file << 'EOF', cat << EOF > file
        r'cat\s+[>]{1,2}\s*([^\s<]+)\s*<<',
        r'cat\s+<<.*?[>]{1,2}\s*([^\s]+)',
        # tee command: tee file, tee -a file
        r'tee\s+(?:-a\s+)?["\']?([^"\'>\s|&;]+)',
        # cp/mv to specific file (not dir)
        r'(?:cp|mv)\s+\S+\s+([^/\s]+\.[a-zA-Z]+)$',
        # Python/ruby one-liners writing files
        r'python[3]?\s+.*?open\s*\(\s*["\']([^"\']+)["\'].*?["\']w',
        r'python[3]?\s+-c\s+.*?[>]{1,2}\s*([^\s]+)',
        # sed -i (in-place edit)
        r'sed\s+-i[^\s]*\s+.*?\s+([^\s]+)$',
        # Direct write via dd
        r'dd\s+.*?of=([^\s]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def main():
    """Main hook entry point."""
    # Toggle check - allow disabling hooks via env var or file flag
    # See docs/INSTALL.md for usage
    if os.environ.get("ERIRPG_HOOKS_DISABLED"):
        print(json.dumps({}))
        sys.exit(0)

    hooks_disabled_file = Path.home() / ".eri-rpg" / ".hooks_disabled"
    if hooks_disabled_file.exists():
        print(json.dumps({}))
        sys.exit(0)

    log("=" * 50)
    log("HOOK INVOKED")
    try:
        # Read input from Claude Code
        raw_input = sys.stdin.read()
        log(f"Raw stdin: {raw_input[:500]}")
        input_data = json.loads(raw_input)
        log(f"Parsed input keys: {list(input_data.keys())}")

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        cwd = input_data.get("cwd", os.getcwd())
        log(f"tool_name={tool_name}, cwd={cwd}")

        # Check for Bash commands that write files
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            log(f"Bash command: {command[:200]}")

            detected_file = detect_bash_file_write(command)
            if detected_file:
                log(f"Detected Bash file write to: {detected_file}")
                # Treat this like an Edit/Write - set file_path and continue checks
                tool_input["file_path"] = detected_file
                tool_name = "Write"  # Treat as Write for enforcement
            else:
                # No file write detected, allow
                log(f"Bash command does not write files, allowing")
                print(json.dumps({}))
                sys.exit(0)

        # Only check Edit/Write/MultiEdit
        if tool_name not in ["Edit", "Write", "MultiEdit"]:
            # Allow other tools
            log(f"Tool {tool_name} not in watch list, allowing")
            print(json.dumps({}))
            sys.exit(0)

        # Get file path from tool input
        file_path = tool_input.get("file_path", "")
        log(f"file_path from input: {file_path}")
        if not file_path:
            # No file path, allow (will fail anyway)
            print(json.dumps({}))
            sys.exit(0)

        # Resolve to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.join(cwd, file_path)
        file_path = os.path.abspath(file_path)

        # Always allow writes to .eri-rpg directory
        if "/.eri-rpg/" in file_path or file_path.endswith("/.eri-rpg"):
            print(json.dumps({}))
            sys.exit(0)

        # Always allow temp files
        if file_path.startswith("/tmp/") or file_path.startswith("/var/tmp/"):
            print(json.dumps({}))
            sys.exit(0)

        # Always allow Claude Code system files (~/.claude/)
        home = os.path.expanduser("~")
        claude_dir = os.path.join(home, ".claude")
        if file_path.startswith(claude_dir):
            log(f"Allowing Claude Code system file: {file_path}")
            print(json.dumps({}))
            sys.exit(0)

        # Find project root (look for .eri-rpg directory)
        # IMPORTANT: Find ALL .eri-rpg directories going up, then use the OUTERMOST one
        # This handles nested .eri-rpg directories (e.g., /project/erirpg/.eri-rpg vs /project/.eri-rpg)
        project_path = cwd
        found_eri_rpg_paths = []
        check_path = Path(file_path).parent
        home_dir = os.path.expanduser("~")
        log(f"Looking for .eri-rpg starting from: {check_path}")
        while check_path != check_path.parent:
            # Stop at home directory - not a project root
            if str(check_path) == home_dir:
                log(f"Reached home dir, stopping search")
                break
            if (check_path / ".eri-rpg").exists():
                found_eri_rpg_paths.append(str(check_path))
                log(f"Found .eri-rpg at: {check_path}")
            check_path = check_path.parent

        if found_eri_rpg_paths:
            # First, prefer paths that have quick_fix_state.json (active quick fix)
            for candidate in reversed(found_eri_rpg_paths):
                qf_path = Path(candidate) / ".eri-rpg" / "quick_fix_state.json"
                if qf_path.exists():
                    project_path = candidate
                    log(f"Using path with quick_fix_state: {project_path}")
                    break
            else:
                # No quick_fix_state found, use outermost .eri-rpg
                project_path = found_eri_rpg_paths[-1]
                log(f"Using outermost project path: {project_path}")
        else:
            log(f"No .eri-rpg found, using cwd: {project_path}")

        # ================================================================
        # BOOTSTRAP MODE CHECK - No enforcement in bootstrap mode
        # ================================================================
        mode = get_project_mode(project_path)
        log(f"Project mode: {mode}")

        if mode == "bootstrap":
            # Bootstrap mode = pass through, no enforcement
            log(f"ALLOWING (bootstrap mode): enforcement disabled")
            print(json.dumps({}))
            sys.exit(0)

        # ================================================================
        # MAINTAIN MODE - Full enforcement below
        # ================================================================

        # Check for quick fix mode FIRST (lightweight mode, no full run required)
        log(f"Checking for quick fix in: {project_path}")
        quick_fix = get_quick_fix_state(project_path)
        if quick_fix and quick_fix.get("quick_fix_active"):
            target_file = quick_fix.get("target_file", "")
            rel_path = os.path.relpath(file_path, project_path)
            # Normalize paths for comparison
            rel_path = os.path.normpath(rel_path)
            target_file = os.path.normpath(target_file)
            log(f"Quick fix active: target={target_file}, rel_path={rel_path}")

            if rel_path == target_file or file_path == target_file:
                # File matches quick fix target - ALLOW
                log(f"ALLOWING (quick fix): {rel_path}")
                output = {"decision": "allow"}
                output_str = json.dumps(output)
                log(f"OUTPUT: {output_str}")
                print(output_str)
                sys.exit(0)
            else:
                # Wrong file for quick fix
                log(f"BLOCKING: {rel_path} not quick fix target {target_file}")
                output = {
                    "decision": "block",
                    "reason": (
                        f"ERI-RPG ENFORCEMENT: Quick fix is for a different file.\n"
                        f"Requested: {rel_path}\n"
                        f"Quick fix target: {target_file}\n\n"
                        f"Complete current quick fix first:\n"
                        f"  eri-rpg quick-done <project>\n\n"
                        f"Or start a new quick fix:\n"
                        f"  eri-rpg quick <project> {rel_path} \"description\""
                    )
                }
                output_str = json.dumps(output)
                log(f"OUTPUT: {output_str}")
                print(output_str)
                sys.exit(0)

        # Check for active run
        log(f"Checking for active run in: {project_path}")
        run_state = get_active_run_state(project_path)
        log(f"Run state: {run_state.get('id') if run_state else None}")
        if not run_state:
            # No active run - BLOCK
            log(f"BLOCKING: No active run")
            output = {
                "decision": "block",
                "reason": (
                    f"ERI-RPG ENFORCEMENT: No active run.\n"
                    f"File: {os.path.basename(file_path)}\n\n"
                    f"Start an EriRPG run first:\n"
                    f"  from erirpg.agent import Agent\n"
                    f"  agent = Agent.from_goal('task', project_path='{project_path}')\n"
                    f"  agent.preflight(['{os.path.relpath(file_path, project_path)}'], 'modify')\n\n"
                    f"Or use quick fix for single-file edits:\n"
                    f"  eri-rpg quick <project> {os.path.relpath(file_path, project_path)} \"description\""
                )
            }
            output_str = json.dumps(output)
            log(f"OUTPUT: {output_str}")
            print(output_str)
            sys.exit(0)

        # Check for preflight state
        log(f"Checking preflight state")
        preflight = get_preflight_state(project_path)
        log(f"Preflight: ready={preflight.get('ready') if preflight else None}, targets={preflight.get('target_files') if preflight else None}")
        if not preflight or not preflight.get("ready"):
            # No preflight - BLOCK
            log(f"BLOCKING: No preflight or not ready")
            output = {
                "decision": "block",
                "reason": (
                    f"ERI-RPG ENFORCEMENT: Preflight required.\n"
                    f"File: {os.path.basename(file_path)}\n\n"
                    f"Run preflight first:\n"
                    f"  agent.preflight(['{os.path.relpath(file_path, project_path)}'], 'modify')"
                )
            }
            output_str = json.dumps(output)
            log(f"OUTPUT: {output_str}")
            print(output_str)
            sys.exit(0)

        # Check if file is in preflight targets
        allowed_files = preflight.get("target_files", [])
        rel_path = os.path.relpath(file_path, project_path)
        # Normalize paths for comparison
        rel_path = os.path.normpath(rel_path)
        normalized_allowed = [os.path.normpath(f) for f in allowed_files]
        log(f"Checking file: rel_path={rel_path}, allowed={normalized_allowed}")

        if rel_path not in normalized_allowed and file_path not in allowed_files:
            log(f"BLOCKING: {rel_path} not in {allowed_files}")
            # File not in preflight - BLOCK
            output = {
                "decision": "block",
                "reason": (
                    f"ERI-RPG ENFORCEMENT: File not in preflight.\n"
                    f"File: {rel_path}\n"
                    f"Allowed: {allowed_files}\n\n"
                    f"Re-run preflight with this file:\n"
                    f"  agent.preflight(['{rel_path}'], 'modify')"
                )
            }
            output_str = json.dumps(output)
            log(f"OUTPUT: {output_str}")
            print(output_str)
            sys.exit(0)

        # All checks passed - ALLOW (auto-approve, no prompt)
        log(f"ALLOWING: {rel_path} is in preflight targets")
        output = {
            "decision": "allow"
        }
        output_str = json.dumps(output)
        log(f"OUTPUT: {output_str}")
        print(output_str)
        sys.exit(0)

    except Exception as e:
        # On error, ALLOW (fail open for safety)
        # But warn about the error
        log(f"EXCEPTION: {str(e)}")
        log(f"TRACEBACK: {traceback.format_exc()}")
        output = {
            "systemMessage": f"EriRPG hook error (allowing): {str(e)}"
        }
        print(json.dumps(output))
        sys.exit(0)


if __name__ == "__main__":
    main()
