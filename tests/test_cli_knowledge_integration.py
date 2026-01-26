"""
Integration tests for CLI knowledge commands (learn, recall, relearn).

These tests verify that:
- The learn command persists knowledge to v2 knowledge.json
- Knowledge survives reindexing
- The recall command retrieves knowledge from v2 storage
- The relearn command removes from v2 storage
- Context generation properly hydrates code from refs
- Token estimation accounts for code refs
"""

import os
import json
import time
import pytest
from datetime import datetime

from erirpg.memory import KnowledgeStore, StoredLearning, load_knowledge, save_knowledge, get_knowledge_path
from erirpg.refs import CodeRef
from erirpg.registry import Project
from erirpg.graph import Graph, Module
from erirpg.ops import Feature, TransplantPlan
from erirpg.context import generate_context, estimate_tokens


class TestKnowledgePersistence:
    """Tests for knowledge store persistence."""

    def test_learning_stored_in_knowledge_json(self, tmp_path):
        """Learning should be stored in knowledge.json."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "module.py").write_text("def foo(): pass")

        eri_dir = project_dir / ".eri-rpg"
        eri_dir.mkdir()

        # Create and save a learning
        store = KnowledgeStore(project="test")
        ref = CodeRef.from_file(str(project_dir), "module.py")

        learning = StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="Test summary",
            purpose="Test purpose",
            key_functions={"foo": "Does something"},
            gotchas=["Watch out"],
            source_ref=ref,
        )

        store.add_learning(learning)
        save_knowledge(str(project_dir), store)

        # Verify knowledge.json was created
        knowledge_path = eri_dir / "knowledge.json"
        assert knowledge_path.exists()

        # Load and verify content
        loaded = load_knowledge(str(project_dir), "test")
        loaded_learning = loaded.get_learning("module.py")

        assert loaded_learning is not None
        assert loaded_learning.summary == "Test summary"
        assert loaded_learning.purpose == "Test purpose"
        assert "foo" in loaded_learning.key_functions
        assert "Watch out" in loaded_learning.gotchas
        assert loaded_learning.source_ref is not None

    def test_coderef_tracks_file_changes(self, tmp_path):
        """CodeRef should detect when source file changes."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        module_path = project_dir / "module.py"
        module_path.write_text("def foo(): pass")

        # Create ref
        ref = CodeRef.from_file(str(project_dir), "module.py")

        # Initially not stale
        assert not ref.is_stale(str(project_dir))

        # Small delay to ensure mtime changes
        time.sleep(0.01)

        # Modify file with different content (different hash)
        module_path.write_text("def foo(): return 'modified_content_here'")

        # Now stale (content changed)
        assert ref.is_stale(str(project_dir))

    def test_learning_staleness_detection(self, tmp_path):
        """Learning should report staleness when source changes."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        module_path = project_dir / "module.py"
        module_path.write_text("def foo(): pass")

        ref = CodeRef.from_file(str(project_dir), "module.py")
        learning = StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="Summary",
            purpose="Purpose",
            source_ref=ref,
        )

        # Not stale initially
        assert not learning.is_stale(str(project_dir))

        # Small delay to ensure mtime changes
        time.sleep(0.01)

        # Modify file with different content
        module_path.write_text("def foo(): return 'changed_content_here'")

        # Now stale
        assert learning.is_stale(str(project_dir))


class TestKnowledgeSurvivesReindex:
    """Tests for knowledge persistence across operations."""

    def test_knowledge_survives_separate_graph(self, tmp_path):
        """Knowledge in knowledge.json survives graph operations."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "module.py").write_text("def foo(): pass")

        eri_dir = project_dir / ".eri-rpg"
        eri_dir.mkdir()

        # Save knowledge
        store = KnowledgeStore(project="test")
        store.add_learning(StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="Should survive",
            purpose="Purpose",
        ))
        save_knowledge(str(project_dir), store)

        # Create and save graph (simulating reindex)
        graph = Graph(project="test")
        graph.add_module(Module(path="module.py", lang="python"))
        graph.save(str(eri_dir / "graph.json"))

        # Knowledge should still be there
        loaded = load_knowledge(str(project_dir), "test")
        assert loaded.has_learning("module.py")
        assert loaded.get_learning("module.py").summary == "Should survive"


class TestFormatForContext:
    """Tests for format_for_context method."""

    def test_format_for_context_basic(self):
        """Format should include summary and purpose."""
        learning = StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="Test summary",
            purpose="Test purpose",
        )

        output = learning.format_for_context()

        assert "Test summary" in output
        assert "Test purpose" in output

    def test_format_for_context_with_staleness_warning(self, tmp_path):
        """Format should show warning when stale."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        module_path = project_dir / "module.py"
        module_path.write_text("def foo(): pass")

        ref = CodeRef.from_file(str(project_dir), "module.py")
        learning = StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="Summary",
            purpose="Purpose",
            source_ref=ref,
        )

        # Small delay to ensure mtime changes
        time.sleep(0.01)

        # Modify source with different content
        module_path.write_text("def foo(): return 'changed_content_here'")

        # Format with project_path should show warning
        output = learning.format_for_context(project_path=str(project_dir))
        assert "WARNING" in output


class TestContextHydration:
    """Tests for context generation with code hydration."""

    def test_context_hydrates_code_from_refs(self, tmp_path):
        """Context generation should hydrate code from refs."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "module.py").write_text("def feature_code():\n    return 'hello'")

        source_eri = source_dir / ".eri-rpg"
        source_eri.mkdir()

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        target_eri = target_dir / ".eri-rpg"
        target_eri.mkdir()

        # Create feature with CodeRef (not snapshot)
        source_ref = CodeRef.from_file(str(source_dir), "module.py")
        feature = Feature(
            name="test_feature",
            source_project="source",
            components=["module.py"],
            code_refs={"module.py": source_ref},
            code_snapshots={},  # Empty - using refs
        )

        plan = TransplantPlan(
            source_project="source",
            target_project="target",
            feature_name="test_feature",
            mappings=[],
            wiring=[],
        )

        source_project = Project(name="source", path=str(source_dir), lang="python")
        target_project = Project(name="target", path=str(target_dir), lang="python")

        source_graph = Graph(project="source")
        target_graph = Graph(project="target")

        # Generate context with source_project
        context_path = generate_context(
            feature, plan, source_graph, target_graph, target_project,
            source_project=source_project,
            use_learnings=False
        )

        # Verify the generated context contains the hydrated code
        with open(context_path) as f:
            content = f.read()

        assert "feature_code" in content
        assert "hello" in content


class TestTokenEstimation:
    """Tests for token estimation with code refs."""

    def test_estimate_tokens_hydrates_refs(self, tmp_path):
        """Token estimate should hydrate refs when source_project provided."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        # Create a file with known content
        code_content = "x" * 4000  # 4000 chars = ~1000 tokens
        (source_dir / "module.py").write_text(code_content)

        # Create feature with CodeRef
        source_ref = CodeRef.from_file(str(source_dir), "module.py")
        feature = Feature(
            name="test",
            source_project="source",
            components=["module.py"],
            code_refs={"module.py": source_ref},
            code_snapshots={},  # Empty
        )

        plan = TransplantPlan(
            source_project="source",
            target_project="target",
            feature_name="test",
            mappings=[],
            wiring=[],
        )

        source_project = Project(name="source", path=str(source_dir), lang="python")

        # With source_project - should hydrate and count actual chars
        tokens_with_project = estimate_tokens(feature, plan, source_project=source_project)

        # Without source_project - should estimate based on file count
        tokens_without_project = estimate_tokens(feature, plan, source_project=None)

        # With hydration we should get accurate count (~1000 tokens for 4000 chars)
        assert tokens_with_project > 800  # At least 800 tokens
        assert tokens_with_project < 1500  # Not too high

        # Without hydration, uses fallback estimate (~2000 chars per file = 500 tokens)
        assert tokens_without_project > 0

    def test_estimate_tokens_fallback_for_refs(self, tmp_path):
        """Token estimate should fallback gracefully when can't hydrate."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "module.py").write_text("x" * 1000)

        # Create ref then delete file
        source_ref = CodeRef.from_file(str(source_dir), "module.py")
        os.remove(source_dir / "module.py")

        feature = Feature(
            name="test",
            source_project="source",
            components=["module.py"],
            code_refs={"module.py": source_ref},
            code_snapshots={},
        )

        plan = TransplantPlan(
            source_project="source",
            target_project="target",
            feature_name="test",
            mappings=[],
            wiring=[],
        )

        source_project = Project(name="source", path=str(source_dir), lang="python")

        # Should not crash, should use fallback estimate
        tokens = estimate_tokens(feature, plan, source_project=source_project)
        assert tokens > 0  # Should have some estimate


class TestSpecIdDeterminism:
    """Tests for deterministic spec IDs."""

    def test_spec_id_is_deterministic(self):
        """Same inputs should produce same spec ID."""
        from erirpg.specs import _generate_spec_id

        id1 = _generate_spec_id("task", "extract-feature")
        id2 = _generate_spec_id("task", "extract-feature")

        assert id1 == id2, "Same inputs should produce same ID"

    def test_different_names_produce_different_ids(self):
        """Different names should produce different IDs."""
        from erirpg.specs import _generate_spec_id

        id1 = _generate_spec_id("task", "extract-feature")
        id2 = _generate_spec_id("task", "implement-feature")

        assert id1 != id2, "Different names should produce different IDs"

    def test_different_types_produce_different_ids(self):
        """Different types should produce different IDs."""
        from erirpg.specs import _generate_spec_id

        id1 = _generate_spec_id("task", "my-spec")
        id2 = _generate_spec_id("project", "my-spec")

        assert id1 != id2, "Different types should produce different IDs"


class TestLearningRemoval:
    """Tests for learning removal from v2 storage."""

    def test_remove_learning_from_store(self, tmp_path):
        """Remove learning should update knowledge.json."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        eri_dir = project_dir / ".eri-rpg"
        eri_dir.mkdir()

        # Create store with learning
        store = KnowledgeStore(project="test")
        store.add_learning(StoredLearning(
            module_path="module.py",
            learned_at=datetime.now(),
            summary="To be removed",
            purpose="Purpose",
        ))
        save_knowledge(str(project_dir), store)

        # Verify it exists
        loaded = load_knowledge(str(project_dir), "test")
        assert loaded.has_learning("module.py")

        # Remove it
        loaded.remove_learning("module.py")
        save_knowledge(str(project_dir), loaded)

        # Verify it's gone
        reloaded = load_knowledge(str(project_dir), "test")
        assert not reloaded.has_learning("module.py")
