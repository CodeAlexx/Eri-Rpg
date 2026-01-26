"""
Test P1-001: Fix mapping provenance in transplant plans.

Verifies that plan_transplant uses actual source modules for interfaces,
not components[0] (which is topo-sorted and may be a dependency).
"""

import pytest
from datetime import datetime

from erirpg.ops import Feature, plan_transplant, Mapping
from erirpg.graph import Graph, Module, Interface
from erirpg.registry import Project


class MockProject:
    """Mock project for testing."""
    def __init__(self, name: str, path: str = "/mock"):
        self.name = name
        self.path = path


def test_mapping_uses_source_module_provenance():
    """Test that mappings use source_module from provides, not components[0].

    Scenario:
    - Feature has components: ["dep/utils.py", "main/feature.py"] (topo-sorted)
    - components[0] is "dep/utils.py" (a dependency)
    - primary_module is "main/feature.py" (what matched the query)
    - Interface "FeatureClass" comes from "main/feature.py"

    Bug (before fix): Mapping would have source_module="dep/utils.py"
    Fix: Mapping should have source_module="main/feature.py"
    """
    # Create feature with proper provenance
    feature = Feature(
        name="test_feature",
        source_project="source_proj",
        primary_module="main/feature.py",
        components=["dep/utils.py", "main/feature.py"],  # Topo-sorted: dep first
        provides=[
            {
                "name": "FeatureClass",
                "type": "class",
                "signature": "class FeatureClass",
                "source_module": "main/feature.py",  # Actual defining module
            },
            {
                "name": "UtilityHelper",
                "type": "class",
                "signature": "class UtilityHelper",
                "source_module": "dep/utils.py",  # From dependency
            }
        ],
        requires=[],
    )

    # Create empty target graph
    target_graph = Graph(project="target_proj")
    target_project = MockProject("target_proj")

    # Generate plan
    plan = plan_transplant(feature, target_graph, target_project)

    # Verify mappings use correct source modules
    assert len(plan.mappings) == 2

    # Find the FeatureClass mapping
    feature_mapping = next(m for m in plan.mappings if m.source_interface == "FeatureClass")
    assert feature_mapping.source_module == "main/feature.py", \
        f"Expected 'main/feature.py', got '{feature_mapping.source_module}' - BUG: using components[0]!"

    # Find the UtilityHelper mapping
    utility_mapping = next(m for m in plan.mappings if m.source_interface == "UtilityHelper")
    assert utility_mapping.source_module == "dep/utils.py", \
        f"Expected 'dep/utils.py', got '{utility_mapping.source_module}'"


def test_mapping_falls_back_to_primary_module():
    """Test fallback to primary_module when source_module not in provides."""
    feature = Feature(
        name="test_feature",
        source_project="source_proj",
        primary_module="main/feature.py",
        components=["dep/utils.py", "main/feature.py"],
        provides=[
            {
                "name": "OldInterface",
                "type": "class",
                "signature": "class OldInterface",
                # No source_module - simulates old feature format
            }
        ],
        requires=[],
    )

    target_graph = Graph(project="target_proj")
    target_project = MockProject("target_proj")

    plan = plan_transplant(feature, target_graph, target_project)

    # Should fall back to primary_module, not components[0]
    assert len(plan.mappings) == 1
    assert plan.mappings[0].source_module == "main/feature.py", \
        "Should fall back to primary_module, not components[0]"


def test_mapping_last_resort_fallback():
    """Test last resort fallback when no primary_module or source_module."""
    feature = Feature(
        name="test_feature",
        source_project="source_proj",
        primary_module="",  # Empty - old format
        components=["only/module.py"],
        provides=[
            {
                "name": "SomeClass",
                "type": "class",
                "signature": "class SomeClass",
            }
        ],
        requires=[],
    )

    target_graph = Graph(project="target_proj")
    target_project = MockProject("target_proj")

    plan = plan_transplant(feature, target_graph, target_project)

    # Last resort: use components[0]
    assert plan.mappings[0].source_module == "only/module.py"


def test_feature_save_load_preserves_provenance():
    """Test that save/load round-trips preserve provenance fields."""
    import tempfile
    import os

    feature = Feature(
        name="test_feature",
        source_project="source_proj",
        primary_module="main/feature.py",
        components=["dep/utils.py", "main/feature.py"],
        provides=[
            {
                "name": "FeatureClass",
                "type": "class",
                "signature": "class FeatureClass",
                "source_module": "main/feature.py",
            }
        ],
        requires=[],
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        feature.save(temp_path)
        loaded = Feature.load(temp_path)

        assert loaded.primary_module == "main/feature.py"
        assert loaded.provides[0]["source_module"] == "main/feature.py"
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
