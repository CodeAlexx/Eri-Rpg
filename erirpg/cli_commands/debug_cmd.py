"""
Debug Persona Commands - Triage-first debugging workflow.

The debug persona is distinct from analyzer - it's interactive and asks
smart questions upfront before diving into diagnosis.

Triage questions (universal debugging practice):
1. Is this code internal or ported/integrated from external source?
2. What's the symptom? (What's happening vs expected?)
3. What changed recently?

If user mentions known external tools, flags as integration debugging
and prompts to compare implementations.
"""

import json
import os
import click
from pathlib import Path

# Universal triage questions - hardcoded because they're universal
TRIAGE_QUESTIONS = [
    {
        "id": "origin",
        "question": "Is this code internal or ported/integrated from an external source?",
        "options": ["internal", "external/ported", "mixed/unclear"],
    },
    {
        "id": "symptom",
        "question": "What's the symptom? Describe what's happening vs what you expected.",
        "options": None,  # Free text
    },
    {
        "id": "changed",
        "question": "What changed recently? (code, deps, config, environment)",
        "options": None,  # Free text
    },
]

# Default known externals - can be overridden in project config
DEFAULT_KNOWN_EXTERNALS = [
    "onetrainer",
    "simpletuner",
    "ai-toolkit",
    "kohya",
    "diffusers",
    "transformers",
    "accelerate",
    "pytorch",
    "torch",
]


def get_known_externals(project_path: str = None) -> list[str]:
    """Get known external tools from project config or defaults."""
    if project_path:
        config_path = Path(project_path) / ".eri-rpg" / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                if "known_externals" in config:
                    return config["known_externals"]
            except:
                pass
    return DEFAULT_KNOWN_EXTERNALS


def detect_external_mention(text: str, known_externals: list[str]) -> list[str]:
    """Check if text mentions any known external tools."""
    text_lower = text.lower()
    return [ext for ext in known_externals if ext.lower() in text_lower]


def set_debug_persona():
    """Set persona to debug in state."""
    state_path = Path.home() / ".eri-rpg" / "state.json"
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except:
            pass
    state["persona"] = "debug"
    state["persona_auto"] = False  # Explicitly set, not auto-detected
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))


def register(cli):
    """Register debug commands with CLI."""

    @cli.command(name="debug")
    @click.argument("description", required=False)
    @click.option("--triage", "-t", is_flag=True, help="Run full triage flow")
    @click.option("--external", "-e", multiple=True, help="Known external tools involved")
    def debug_cmd(description: str = None, triage: bool = False, external: tuple = None):
        """Start debug persona with triage-first approach.

        The debug persona asks smart questions upfront:
        1. Is this internal code or external/ported?
        2. What's the symptom?
        3. What changed?

        If external tools are mentioned, flags as integration debugging.

        \b
        Examples:
            eri-rpg debug "training crashes at step 100"
            eri-rpg debug --triage
            eri-rpg debug "diffusers pipeline fails" --external diffusers
        """
        # Set persona
        set_debug_persona()

        project_path = os.getcwd()
        known_externals = get_known_externals(project_path)

        # Check for external tool mentions in description
        mentioned_externals = []
        if description:
            mentioned_externals = detect_external_mention(description, known_externals)
        if external:
            mentioned_externals.extend(list(external))
        mentioned_externals = list(set(mentioned_externals))  # Dedupe

        # Output triage structure for Claude to use
        output = {
            "persona": "debug",
            "mode": "triage",
            "triage_questions": TRIAGE_QUESTIONS,
            "known_externals": known_externals,
        }

        if description:
            output["initial_description"] = description

        if mentioned_externals:
            output["integration_debug"] = True
            output["external_tools"] = mentioned_externals
            output["integration_prompt"] = (
                f"External tool(s) detected: {', '.join(mentioned_externals)}. "
                "Compare their implementation vs ours. Check: "
                "(1) API usage matches their docs, "
                "(2) Version compatibility, "
                "(3) Our wrapper/adapter logic."
            )

        # Output as JSON for Claude to consume
        click.echo(json.dumps(output, indent=2))

        # Also human-readable summary
        click.echo("\n---")
        click.echo("Debug persona activated. Triage checklist:")
        click.echo("  1. Origin: Internal or external/ported code?")
        click.echo("  2. Symptom: What's happening vs expected?")
        click.echo("  3. Changed: What changed recently?")

        if mentioned_externals:
            click.echo(f"\n  Integration debugging flagged: {', '.join(mentioned_externals)}")
            click.echo("  Compare our implementation vs their docs/examples.")

    @cli.command(name="debug-config")
    @click.option("--add", "-a", multiple=True, help="Add external tool to known list")
    @click.option("--remove", "-r", multiple=True, help="Remove external tool from list")
    @click.option("--list", "-l", "list_all", is_flag=True, help="List known externals")
    def debug_config_cmd(add: tuple = None, remove: tuple = None, list_all: bool = False):
        """Configure debug persona for this project.

        Manages the known_externals list - tools that trigger
        integration debugging mode.

        \b
        Examples:
            eri-rpg debug-config --list
            eri-rpg debug-config --add comfyui --add sdwebui
            eri-rpg debug-config --remove pytorch
        """
        project_path = os.getcwd()
        config_path = Path(project_path) / ".eri-rpg" / "config.json"

        # Load existing config
        config = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
            except:
                pass

        # Get current externals (from config or defaults)
        externals = config.get("known_externals", DEFAULT_KNOWN_EXTERNALS.copy())

        if list_all:
            click.echo("Known external tools (triggers integration debugging):")
            for ext in externals:
                click.echo(f"  - {ext}")
            if "known_externals" not in config:
                click.echo("\n(Using defaults. Run --add to customize.)")
            return

        modified = False

        if add:
            for tool in add:
                if tool.lower() not in [e.lower() for e in externals]:
                    externals.append(tool.lower())
                    click.echo(f"Added: {tool}")
                    modified = True
                else:
                    click.echo(f"Already exists: {tool}")

        if remove:
            for tool in remove:
                matches = [e for e in externals if e.lower() == tool.lower()]
                for m in matches:
                    externals.remove(m)
                    click.echo(f"Removed: {m}")
                    modified = True

        if modified:
            config["known_externals"] = externals
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, indent=2))
            click.echo(f"\nSaved to {config_path}")
