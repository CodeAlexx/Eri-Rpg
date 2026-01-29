#!/usr/bin/env python3
"""
EriRPG Status Line for Claude Code.

Reads project state and outputs a formatted status line.
Configure in Claude Code with: /statusline

Usage:
    echo '{"context_window":{"used_percentage":45}}' | python3 statusline.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Default settings
DEFAULT_SETTINGS = {
    "statusline": {
        "enabled": True,
        "elements": {
            "persona": True,
            "phase": True,
            "context": True,
            "task": True,
            "time": False
        }
    }
}

# Default persona when nothing else applies
DEFAULT_PERSONA = "analyzer"

# Persona defaults for each phase
# Maps EriRPG phases to SuperClaude personas
PHASE_PERSONA_DEFAULTS = {
    "idle": "analyzer",
    "extracting": "analyzer",
    "planning": "architect",
    "context_ready": "analyzer",
    "implementing": "backend",
    "verifying": "qa",
    "documenting": "scribe",
    "researching": "analyzer",
    "designing": "architect",
    "testing": "qa",
    "refactoring": "refactorer",
    "optimizing": "performance",
    "securing": "security",
}

# Action-based persona overrides (takes precedence over phase)
ACTION_PERSONA_DEFAULTS = {
    "extract": "analyzer",
    "plan": "architect",
    "context": "analyzer",
    "take": "architect",
    "work": "backend",
    "implement": "backend",
    "done": "analyzer",
    "decision": "architect",
    "learn": "analyzer",
    "verify": "qa",
    "test": "qa",
    "document": "scribe",
    "research": "analyzer",
    "quick": "backend",
    "quick-done": "analyzer",
}

def load_settings() -> dict:
    """Load settings from ~/.eri-rpg/settings.json"""
    settings_path = Path.home() / ".eri-rpg" / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_SETTINGS


def load_global_state() -> dict:
    """Load global state from ~/.eri-rpg/state.json"""
    state_path = Path.home() / ".eri-rpg" / "state.json"
    if state_path.exists():
        try:
            with open(state_path) as f:
                return json.load(f)
        except:
            pass
    return {}


def get_active_persona(global_state: dict) -> str:
    """Determine active persona from state.

    Priority:
    1. Explicitly set persona in state
    2. Last action's default persona
    3. Current phase's default persona
    4. Global default
    """
    # Check for explicit persona override
    if global_state.get("persona"):
        return global_state["persona"]

    # Check last action in history
    history = global_state.get("history", [])
    if history:
        last_action = history[-1].get("action", "")
        if last_action in ACTION_PERSONA_DEFAULTS:
            return ACTION_PERSONA_DEFAULTS[last_action]

    # Check current phase
    phase = global_state.get("phase", "idle")
    if phase in PHASE_PERSONA_DEFAULTS:
        return PHASE_PERSONA_DEFAULTS[phase]

    return DEFAULT_PERSONA

def find_state_file() -> Path | None:
    """Find STATE.md in current or parent directories."""
    cwd = Path.cwd()

    # Check common locations
    candidates = [
        cwd / "STATE.md",
        cwd / ".eri-rpg" / "STATE.md",
    ]

    # Also check parent dirs
    for parent in [cwd] + list(cwd.parents)[:3]:
        candidates.append(parent / "STATE.md")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

def parse_state_file(state_path: Path) -> dict:
    """Parse STATE.md for phase info."""
    result = {
        "phase_current": None,
        "phase_total": None,
        "phase_name": None,
        "project": None
    }

    try:
        content = state_path.read_text()

        for line in content.split('\n'):
            line = line.strip()

            # Parse: Phase: 3 of 6 - Frontend
            if line.startswith("Phase:"):
                parts = line.replace("Phase:", "").strip()
                # "3 of 6 - Frontend"
                if " of " in parts:
                    num_part, rest = parts.split(" of ", 1)
                    result["phase_current"] = int(num_part.strip())
                    if " - " in rest:
                        total, name = rest.split(" - ", 1)
                        result["phase_total"] = int(total.strip())
                        result["phase_name"] = name.strip()
                    else:
                        result["phase_total"] = int(rest.strip())

            # Parse: **Project:** name
            elif "**Project:**" in line:
                result["project"] = line.split("**Project:**")[1].strip()

    except Exception:
        pass

    return result

def format_statusline(state: dict, context_pct: int | None, settings: dict, persona: str | None) -> str:
    """Format the status line based on settings."""
    elements = settings.get("statusline", {}).get("elements", {})
    parts = []

    # Persona element (always first when enabled)
    if elements.get("persona", True) and persona:
        parts.append(f"🎭 {persona}")

    # Phase element
    if elements.get("phase", True) and state.get("phase_current"):
        phase_str = f"📍 {state['phase_current']}/{state['phase_total']}"
        parts.append(phase_str)

    # Context element
    if elements.get("context", True) and context_pct is not None:
        ctx_str = f"🔄 {context_pct}%"
        parts.append(ctx_str)

    # Task/phase name element
    if elements.get("task", True) and state.get("phase_name"):
        # Truncate long names
        name = state["phase_name"][:12]
        parts.append(f"🎯 {name}")

    # Time element (placeholder - would need session start time)
    # if elements.get("time", False):
    #     parts.append("⏱️ --m")

    if not parts:
        return ""

    return " | ".join(parts)

def main():
    """Main entry point."""
    settings = load_settings()

    if not settings.get("statusline", {}).get("enabled", True):
        print("")
        return

    # Read input from Claude Code (JSON with context_window info)
    context_pct = None
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            if input_data.strip():
                data = json.loads(input_data)
                context_pct = data.get("context_window", {}).get("used_percentage")
    except:
        pass

    # Find and parse state file (project-level)
    state_path = find_state_file()
    state = {}
    if state_path:
        state = parse_state_file(state_path)

    # Load global state for persona
    global_state = load_global_state()
    persona = get_active_persona(global_state)

    # Format and output
    statusline = format_statusline(state, context_pct, settings, persona)
    print(statusline)

if __name__ == "__main__":
    main()
