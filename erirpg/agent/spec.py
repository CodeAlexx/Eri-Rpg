"""
Spec file parsing for agent-driven workflows.

DEPRECATED: This module re-exports from erirpg.spec for backward compatibility.
Use erirpg.spec directly for new code.
"""

# Re-export everything from the canonical spec module
from erirpg.spec import Spec, SpecStep, Step, generate_spec_id

__all__ = ["Spec", "SpecStep", "Step", "generate_spec_id"]
