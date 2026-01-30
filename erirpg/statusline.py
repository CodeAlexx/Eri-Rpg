#!/usr/bin/env python3
"""
EriRPG Status Line for Claude Code.

Two-line status display:
  Line 1: Project | Phase | Persona | Context%
  Line 2: Branch | Tier | Knowledge | Tests | Tokens

Usage:
    echo '{"context_window":{"used_percentage":45,"used_tokens":50000}}' | python3 statusline.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Default persona when nothing else applies
DEFAULT_PERSONA = "analyzer"

# Persona defaults for each phase
PHASE_PERSONA_DEFAULTS = {
    "idle": "analyzer",
    "extracting": "analyzer",
    "planning": "architect",
    "context_ready": "architect",  # Ready to plan/design
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

# Action-based persona overrides
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


def load_global_state() -> dict:
    """Load global state from ~/.eri-rpg/state.json"""
    state_path = Path.home() / ".eri-rpg" / "state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except:
            pass
    return {}


def load_registry() -> dict:
    """Load project registry from ~/.eri-rpg/registry.json"""
    registry_path = Path.home() / ".eri-rpg" / "registry.json"
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text())
            # Registry has "projects" key containing the actual projects
            return data.get("projects", {})
        except:
            pass
    return {}


def get_active_persona(global_state: dict) -> str:
    """Determine active persona from state."""
    if global_state.get("persona"):
        return global_state["persona"]

    history = global_state.get("history", [])
    if history:
        last_action = history[-1].get("action", "")
        if last_action in ACTION_PERSONA_DEFAULTS:
            return ACTION_PERSONA_DEFAULTS[last_action]

    phase = global_state.get("phase", "idle")
    if phase in PHASE_PERSONA_DEFAULTS:
        return PHASE_PERSONA_DEFAULTS[phase]

    return DEFAULT_PERSONA


def get_git_branch() -> Optional[str]:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def get_project_tier(project_path: str) -> str:
    """Get tier from project config."""
    config_path = Path(project_path) / ".eri-rpg" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            return data.get("tier", "lite")
        except:
            pass
    return "lite"


def get_model_provider_info(project_path: str) -> Tuple[str, str]:
    """Get model provider and display name from project config.

    Returns:
        Tuple of (provider: "claude"|"local", display_name)
    """
    config_path = Path(project_path) / ".eri-rpg" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            eri = data.get("eri", {})
            provider = eri.get("model_provider", "claude")
            if provider == "local":
                local_model = eri.get("local_model", {})
                model = local_model.get("model", "local")
                # Extract short name from path
                if "/" in model:
                    model = model.split("/")[-1]
                return "local", model
            else:
                profile = eri.get("model_profile", "balanced")
                return "claude", profile
        except:
            pass
    return "claude", "balanced"


def get_project_info(registry: dict, cwd: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Get project name, path, and tier from registry based on cwd."""
    for name, info in registry.items():
        proj_path = info.get("path", "")
        if cwd.startswith(proj_path) or proj_path.startswith(cwd):
            tier = get_project_tier(proj_path)
            return name, proj_path, tier
    return None, None, None


def get_knowledge_count(project_path: Optional[str]) -> int:
    """Count learned modules from knowledge.json"""
    if not project_path:
        return 0

    knowledge_path = Path(project_path) / ".eri-rpg" / "knowledge.json"
    if knowledge_path.exists():
        try:
            data = json.loads(knowledge_path.read_text())
            return len(data.get("modules", {}))
        except:
            pass
    return 0


def get_last_test_status(project_path: Optional[str]) -> Optional[str]:
    """Get last test status from verification state."""
    if not project_path:
        return None

    verify_path = Path(project_path) / ".eri-rpg" / "verification.json"
    if verify_path.exists():
        try:
            data = json.loads(verify_path.read_text())
            return "✓" if data.get("last_passed", False) else "✗"
        except:
            pass
    return None


def get_project_state(project_path: Optional[str]) -> dict:
    """Load project-specific state from <project>/.eri-rpg/state.json"""
    if not project_path:
        return {}

    state_path = Path(project_path) / ".eri-rpg" / "state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except:
            pass
    return {}


def format_tokens(tokens: Optional[int]) -> str:
    """Format token count in human-readable form."""
    if tokens is None:
        return ""
    if tokens >= 1000:
        return f"{tokens // 1000}k"
    return str(tokens)


def main():
    """Main entry point."""
    # Read input from Claude Code
    context_pct = None
    tokens_used = None
    model_name = None
    input_cwd = None
    try:
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            if input_data.strip():
                data = json.loads(input_data)
                # Context window info
                cw = data.get("context_window", {})
                context_pct = cw.get("used_percentage")
                # Calculate total tokens used
                total_input = cw.get("total_input_tokens", 0)
                total_output = cw.get("total_output_tokens", 0)
                if total_input or total_output:
                    tokens_used = total_input + total_output
                # Model info
                model_info = data.get("model", {})
                model_name = model_info.get("display_name") or model_info.get("id")
                # Workspace cwd (more reliable than os.getcwd)
                workspace = data.get("workspace", {})
                input_cwd = workspace.get("current_dir") or workspace.get("project_dir")
    except:
        pass

    # Load state
    global_state = load_global_state()
    registry = load_registry()
    cwd = input_cwd or os.getcwd()

    # Get project info - PRIORITIZE cwd-based detection over stale state
    project_name, project_path, tier = get_project_info(registry, cwd)

    # Only use active_project from state if cwd detection failed
    if not project_name:
        state_project = global_state.get("active_project")
        if state_project and state_project in registry:
            project_name = state_project
            project_path = registry[state_project].get("path")
            tier = get_project_tier(project_path) if project_path else "lite"

    # Gather all info
    persona = get_active_persona(global_state)
    phase = global_state.get("phase", "idle")
    branch = get_git_branch()
    knowledge = get_knowledge_count(project_path)
    test_status = get_last_test_status(project_path)

    # Get project-specific state for current_task
    project_state = get_project_state(project_path)

    # Get model provider info for the project
    model_provider, model_display = "claude", "balanced"
    if project_path:
        model_provider, model_display = get_model_provider_info(project_path)

    # === LINE 1: Model | Phase | Persona | Context | Task ===
    line1_parts = []

    # Show model with appropriate icon
    # 🤖 = Claude/Anthropic, 🏠 = local model
    if model_provider == "local":
        line1_parts.append(f"🏠 {model_display}")
    elif model_name:
        line1_parts.append(f"🤖 {model_name}")

    if phase and phase != "idle":
        line1_parts.append(f"📍 {phase}")

    line1_parts.append(f"🎭 {persona}")

    if context_pct is not None:
        line1_parts.append(f"🔄 {context_pct}%")

    # Current task/section - from PROJECT state, not global
    current_task = project_state.get("current_task")
    if current_task:
        # Truncate long task names
        task_display = current_task[:30] + "…" if len(current_task) > 30 else current_task
        line1_parts.append(f"🎯 {task_display}")

    # === LINE 2: Branch | Tier | Project | Knowledge | Tests | Tokens ===
    line2_parts = []

    if branch:
        # Truncate long branch names
        branch_display = branch[:15] + "…" if len(branch) > 15 else branch
        line2_parts.append(f"🌿 {branch_display}")

    if tier:
        tier_icons = {"lite": "⚡", "standard": "⚡⚡", "full": "⚡⚡⚡"}
        line2_parts.append(f"{tier_icons.get(tier, '⚡')} {tier}")

    # Bold white project name (ANSI: \033[1;37m = bold white, \033[0m = reset)
    if project_name:
        line2_parts.append(f"\033[1;37mProject: {project_name}\033[0m")

    if knowledge > 0:
        line2_parts.append(f"🧠 {knowledge}")

    if test_status:
        line2_parts.append(f"🧪 {test_status}")

    if tokens_used:
        line2_parts.append(f"📊 {format_tokens(tokens_used)}")

    # Output
    line1 = " | ".join(line1_parts) if line1_parts else ""
    line2 = " | ".join(line2_parts) if line2_parts else ""

    if line1 and line2:
        print(f"{line1}\n{line2}")
    elif line1:
        print(line1)
    elif line2:
        print(line2)


if __name__ == "__main__":
    main()
