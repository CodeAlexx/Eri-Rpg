#!/usr/bin/env python3
"""
EriRPG Persona Auto-Detection Hook

Runs on EVERY tool use to detect what type of work is happening
and automatically update the persona in state.json.

This is a lightweight, non-blocking hook - it never blocks operations,
just updates persona state for the status line.

Detection rules:
- Read/Grep/Glob on code → analyzer
- Edit/Write on .py/.js/.ts/.go/.rs → backend
- Edit/Write on .jsx/.tsx/.vue/.css/.html → frontend
- Bash with test/pytest/jest → qa
- Bash with git → devops
- Edit on .md/docs/ → scribe
- Task/planning operations → architect
- Files with security/auth/crypto → security

Install in ~/.claude/settings.json:
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/erirpg/hooks/persona_detect.py",
            "timeout": 2
          }
        ]
      }
    ]
  }
}
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

STATE_FILE = Path.home() / ".eri-rpg" / "state.json"
LOG_FILE = Path("/tmp/erirpg-persona.log")

# File extension to persona mapping
BACKEND_EXTENSIONS = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.php', '.c', '.cpp', '.h'}
FRONTEND_EXTENSIONS = {'.jsx', '.tsx', '.vue', '.svelte', '.css', '.scss', '.sass', '.less', '.html'}
DOC_EXTENSIONS = {'.md', '.rst', '.txt', '.adoc'}

# Security-related patterns in file paths
SECURITY_PATTERNS = ['auth', 'security', 'crypto', 'password', 'token', 'secret', 'permission', 'acl']


def log(msg: str):
    """Log for debugging (disabled by default)."""
    if os.environ.get("ERIRPG_PERSONA_DEBUG"):
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        except:
            pass


def load_state() -> dict:
    """Load current state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {}


def save_state(state: dict):
    """Save state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_persona(tool_name: str, tool_input: dict) -> Optional[str]:
    """Detect persona based on tool usage. Returns None if no change needed."""

    file_path = tool_input.get("file_path", "") or tool_input.get("path", "") or ""
    command = tool_input.get("command", "")
    pattern = tool_input.get("pattern", "")

    # Normalize file path
    file_lower = file_path.lower()
    ext = Path(file_path).suffix.lower() if file_path else ""

    log(f"Detecting: tool={tool_name}, file={file_path}, ext={ext}, cmd={command[:50]}")

    # Security detection (highest priority)
    if any(sec in file_lower for sec in SECURITY_PATTERNS):
        return "security"

    # Tool-specific detection
    if tool_name in ["Read", "Grep", "Glob"]:
        # Check what we're reading to infer context
        if ext in DOC_EXTENSIONS or "/docs/" in file_lower or "readme" in file_lower:
            return "scribe"
        if "test" in file_lower or "spec" in file_lower:
            return "qa"
        if ext in FRONTEND_EXTENSIONS:
            return "frontend"
        if ext in BACKEND_EXTENSIONS:
            return "backend"
        # Default: analyzing
        return "analyzer"

    if tool_name in ["Edit", "Write", "MultiEdit"]:
        # Check file type
        if ext in FRONTEND_EXTENSIONS:
            return "frontend"
        if ext in BACKEND_EXTENSIONS:
            return "backend"
        if ext in DOC_EXTENSIONS or "/docs/" in file_lower or "readme" in file_lower:
            return "scribe"
        # Default for edits
        return "backend"

    if tool_name == "Bash":
        cmd_lower = command.lower()

        # Test commands
        if any(t in cmd_lower for t in ["pytest", "jest", "npm test", "yarn test", "cargo test", "go test", "rspec", "unittest"]):
            return "qa"

        # Git commands
        if cmd_lower.startswith("git ") or "git " in cmd_lower:
            return "devops"

        # Build/deploy commands
        if any(t in cmd_lower for t in ["docker", "kubectl", "terraform", "ansible", "deploy", "build"]):
            return "devops"

        # Lint/format (quality)
        if any(t in cmd_lower for t in ["ruff", "eslint", "prettier", "black", "mypy", "tsc"]):
            return "refactorer"

    if tool_name == "Task":
        # Task agent = planning/architecture
        return "architect"

    if tool_name == "WebSearch" or tool_name == "WebFetch":
        # Research
        return "analyzer"

    # No specific detection
    return None


def main():
    """Main hook entry point."""
    try:
        # Read input
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({}))
            sys.exit(0)

        input_data = json.loads(raw_input)
        cwd = input_data.get("cwd", os.getcwd())

        # Project detection - early exit if not an eri-rpg project
        project_root = None
        check = cwd
        while check != '/':
            if os.path.isdir(os.path.join(check, '.eri-rpg')):
                project_root = check
                break
            check = os.path.dirname(check)

        if project_root is None:
            # Not an eri-rpg project. Output empty and exit.
            print(json.dumps({}))
            sys.exit(0)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        log(f"Hook called: {tool_name}")

        # Detect persona
        detected = detect_persona(tool_name, tool_input)

        if detected:
            state = load_state()
            current = state.get("persona")

            # Only update if different (avoid excessive writes)
            if current != detected:
                log(f"Updating persona: {current} -> {detected}")
                state["persona"] = detected
                state["persona_auto"] = True  # Mark as auto-detected
                state["persona_updated"] = datetime.now().isoformat()
                save_state(state)

        # Never block - always return empty
        print(json.dumps({}))
        sys.exit(0)

    except Exception as e:
        log(f"Error: {e}")
        # Never block on errors
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
