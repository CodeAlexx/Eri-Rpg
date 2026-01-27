"""
Backward compatibility - re-exports from erirpg.spec.

Use erirpg.spec directly for new code.
"""
from erirpg.spec import Spec, SpecStep, Step, generate_spec_id

__all__ = ["Spec", "SpecStep", "Step", "generate_spec_id"]
