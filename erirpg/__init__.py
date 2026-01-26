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
"""

__version__ = "0.1.0"
__author__ = "Alex"

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
