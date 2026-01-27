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

HARD ENFORCEMENT:
When EriRPG is imported, file write hooks are automatically installed.
Any attempt to write files without going through EriRPG will be BLOCKED.
This ensures all code changes follow the EriRPG workflow:
    1. Create an Agent
    2. Run preflight()
    3. Use agent.edit_file() or agent.write_file()
"""

__version__ = "0.1.0"
__author__ = "Alex"

# Install hard enforcement hooks FIRST
from erirpg.hooks import install_hooks
install_hooks()

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
