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

__version__ = "0.55.0-alpha"
__author__ = "Alex"

# NOTE: Hooks are NOT auto-installed on import anymore.
# They are installed when Agent is created, or manually via install_hooks().

from erirpg.graph import Graph, Module, Interface, Edge
from erirpg.registry import Registry, Project

__all__ = [
    "Graph",
    "Module",
    "Interface",
    "Edge",
    "Registry",
    "Project",
]
