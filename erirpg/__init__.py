"""
EriRPG - Cross-project feature transplant tool.

A lean CLI tool for:
- Registering external projects with paths
- Indexing codebases to build dependency graphs
- Finding capabilities in code via local search
- Extracting features as self-contained units
- Planning transplants between projects
- Generating minimal context for Claude Code

No LLM calls. Pure Python. Claude Code is the LLM.

ENFORCEMENT:
File write hooks are installed when an Agent is created (opt-in).
Claude Code hooks (pretooluse.py) enforce workflow at the tool level.
"""

__version__ = "0.60.0"
__author__ = "Alex"

# NOTE: Hooks are NOT auto-installed on import anymore.
# They are installed when Agent is created, or manually via install_hooks().

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg.registry import Registry, Project
from erirpg.persona import Persona, PersonaConfig, get_persona, detect_persona_from_input
from erirpg.workflow import Stage, get_persona_for_stage, get_stage_description
from erirpg.commands import parse_command, is_command, get_help_text

__all__ = [
    # Graph
    "Graph",
    "Module",
    "Interface",
    "Edge",
    # Registry
    "Registry",
    "Project",
    # Persona system
    "Persona",
    "PersonaConfig",
    "get_persona",
    "detect_persona_from_input",
    # Workflow
    "Stage",
    "get_persona_for_stage",
    "get_stage_description",
    # Commands
    "parse_command",
    "is_command",
    "get_help_text",
]
