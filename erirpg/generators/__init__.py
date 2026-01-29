"""
Generators module for automatic documentation.

Generates CONTEXT.md and STATUS.md from SQLite session data.
"""

from erirpg.generators.context_md import generate_context_md
from erirpg.generators.status_md import generate_status_md

__all__ = ["generate_context_md", "generate_status_md"]
