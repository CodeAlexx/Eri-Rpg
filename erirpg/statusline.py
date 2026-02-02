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


def get_active_edited_project(global_state: dict, registry: dict) -> tuple:
    """Get actively edited project from state (set by PostToolUse hook).

    Returns (project_name, project_path, tier) or (None, None, None).
    Expires after 30 minutes of no edits.
    """
    from datetime import datetime, timedelta

    edited_at = global_state.get("active_edited_at")
    if not edited_at:
        return None, None, None

    # Check if stale (>30 minutes since last edit)
    try:
        last_edit = datetime.fromisoformat(edited_at)
        if datetime.now() - last_edit > timedelta(minutes=30):
            return None, None, None
    except:
        return None, None, None

    project_name = global_state.get("active_edited_project")
    project_path = global_state.get("active_edited_path")

    if not project_name or not project_path:
        return None, None, None

    # Get tier from project config
    tier = get_project_tier(project_path) if project_path else None

    return project_name, project_path, tier


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
    """Get project name, path, and tier from registry based on cwd.

    Only matches if cwd is inside the project path (not the reverse).
    Finds the most specific (longest) matching project path.
    """
    best_match = (None, None, None)
    best_len = 0

    for name, info in registry.items():
        proj_path = info.get("path", "")
        # Only match if cwd is inside this project (cwd starts with proj_path)
        # NOT the reverse (that was the bug - matching any project containing cwd as prefix)
        if proj_path and cwd.startswith(proj_path):
            # Prefer longer (more specific) matches
            if len(proj_path) > best_len:
                tier = get_project_tier(proj_path)
                best_match = (name, proj_path, tier)
                best_len = len(proj_path)

    return best_match


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


def get_coder_phase_info(cwd: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Get coder phase info from .planning/STATE.md in cwd or parent dirs.

    Returns:
        Tuple of (current_phase, total_phases, status) or (None, None, None)
    """
    import re

    # Search from cwd upward for .planning/STATE.md
    search_path = Path(cwd)
    for _ in range(5):  # Max 5 levels up
        state_file = search_path / ".planning" / "STATE.md"
        if state_file.exists():
            try:
                content = state_file.read_text()
                # Parse "Phase: X of Y" pattern
                match = re.search(r'\*\*Phase:\*\*\s*(\d+)\s+of\s+(\d+)', content)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    # Check if complete
                    if "ALL COMPLETE" in content or "Ready" in content:
                        status = "done"
                    else:
                        status = "active"
                    return current, total, status
            except:
                pass
            break
        search_path = search_path.parent
        if search_path == search_path.parent:  # Hit root
            break

    return None, None, None


def get_coder_project_name(cwd: str) -> Optional[str]:
    """Get project name for unregistered coder projects (have .planning/ but no registry entry).

    Uses directory name - don't parse document titles as project names.

    Returns:
        Project name (directory name) or None if no .planning/ found
    """
    search_path = Path(cwd)
    for _ in range(5):  # Max 5 levels up
        planning_dir = search_path / ".planning"
        if planning_dir.exists():
            # Use directory name - simple and reliable
            return search_path.name

        search_path = search_path.parent
        if search_path == search_path.parent:  # Hit root
            break

    return None


def format_progress_bar(current: int, total: int, width: int = 10) -> str:
    """Format a progress bar like [████░░░░░░] 40%"""
    if total <= 0:
        return ""
    pct = min(100, int((current / total) * 100))
    filled = int((current / total) * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {pct}%"


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

    cwd = input_cwd or os.getcwd()

    # Project detection - check if this is an eri-rpg project
    project_root = None
    check = cwd
    while check != '/':
        if os.path.isdir(os.path.join(check, '.eri-rpg')):
            project_root = check
            break
        check = os.path.dirname(check)

    if project_root is None:
        # Not an eri-rpg project. Show minimal status.
        line1_parts = []
        line2_parts = []

        if model_name:
            line1_parts.append(f"🤖 {model_name}")

        if context_pct is not None:
            line1_parts.append(f"🔄 {context_pct}%")

        branch = get_git_branch()
        if branch:
            branch_display = branch[:15] + "…" if len(branch) > 15 else branch
            line2_parts.append(f"🌿 {branch_display}")

        if tokens_used:
            line2_parts.append(f"📊 {format_tokens(tokens_used)}")

        line1 = " | ".join(line1_parts) if line1_parts else ""
        line2 = " | ".join(line2_parts) if line2_parts else ""

        if line1 and line2:
            print(f"{line1}\n{line2}")
        elif line1:
            print(line1)
        elif line2:
            print(line2)
        return

    # Load state (only for eri-rpg projects)
    global_state = load_global_state()
    registry = load_registry()

    # HIGHEST PRIORITY: coder project in cwd (.planning/ directory)
    # When cd'd into a directory with .planning/, show that project
    project_name, project_path, tier = None, None, None
    coder_name = get_coder_project_name(cwd)
    if coder_name:
        project_name = coder_name
        # Find actual path where .planning/ exists
        search_path = Path(cwd)
        for _ in range(5):
            if (search_path / ".planning").exists():
                project_path = str(search_path)
                break
            search_path = search_path.parent
        else:
            project_path = cwd
        tier = get_project_tier(project_path) if (Path(project_path) / ".eri-rpg").exists() else None

    # SECOND: cwd-based detection from registry
    if not project_name:
        project_name, project_path, tier = get_project_info(registry, cwd)

    # THIRD: Active edited project (set by PostToolUse hook)
    # Fallback when cwd isn't in a project
    if not project_name:
        project_name, project_path, tier = get_active_edited_project(global_state, registry)

    # LAST RESORT: active_project from state
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

    # Get coder phase info (from .planning/STATE.md)
    coder_current, coder_total, coder_status = get_coder_phase_info(cwd)

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

    # Show coder phase with progress bar (takes priority over eri phase)
    if coder_current is not None and coder_total is not None:
        progress = format_progress_bar(coder_current, coder_total, width=8)
        if coder_status == "done":
            line1_parts.append(f"✅ Phase {coder_current}/{coder_total} {progress}")
        else:
            line1_parts.append(f"🔨 Phase {coder_current}/{coder_total} {progress}")
    elif phase and phase != "idle":
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
