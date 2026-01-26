"""
Test P1-004: Language-aware context fences.

Verifies that context files use the correct code fence language for each file type.
"""

import pytest

from erirpg.context import get_fence_language, EXTENSION_TO_FENCE


class TestGetFenceLanguage:
    """Tests for get_fence_language helper."""

    def test_python_files(self):
        """Python files should use 'python' fence."""
        assert get_fence_language("src/module.py") == "python"
        assert get_fence_language("types.pyi") == "python"
        assert get_fence_language("/home/user/project/test.py") == "python"

    def test_rust_files(self):
        """Rust files should use 'rust' fence."""
        assert get_fence_language("src/main.rs") == "rust"
        assert get_fence_language("lib.rs") == "rust"

    def test_c_files(self):
        """C files should use 'c' fence."""
        assert get_fence_language("src/main.c") == "c"
        assert get_fence_language("include/header.h") == "c"

    def test_cpp_files(self):
        """C++ files should use 'cpp' fence."""
        assert get_fence_language("src/main.cpp") == "cpp"
        assert get_fence_language("include/header.hpp") == "cpp"
        assert get_fence_language("module.cc") == "cpp"
        assert get_fence_language("types.hh") == "cpp"

    def test_javascript_files(self):
        """JavaScript files should use 'javascript' fence."""
        assert get_fence_language("src/app.js") == "javascript"
        assert get_fence_language("components/Button.jsx") == "javascript"

    def test_typescript_files(self):
        """TypeScript files should use 'typescript' fence."""
        assert get_fence_language("src/app.ts") == "typescript"
        assert get_fence_language("components/Button.tsx") == "typescript"

    def test_config_files(self):
        """Config files should use appropriate fences."""
        assert get_fence_language("config.yaml") == "yaml"
        assert get_fence_language("config.yml") == "yaml"
        assert get_fence_language("package.json") == "json"
        assert get_fence_language("Cargo.toml") == "toml"

    def test_unknown_extension(self):
        """Unknown extensions should fall back to 'text'."""
        assert get_fence_language("file.unknown") == "text"
        assert get_fence_language("data.dat") == "text"
        assert get_fence_language("config.ini") == "text"

    def test_case_insensitive(self):
        """Extension matching should be case-insensitive."""
        assert get_fence_language("file.PY") == "python"
        assert get_fence_language("file.Rs") == "rust"
        assert get_fence_language("file.CPP") == "cpp"

    def test_nested_paths(self):
        """Should work with deeply nested paths."""
        assert get_fence_language("a/b/c/d/e/file.py") == "python"
        assert get_fence_language("/absolute/path/to/file.rs") == "rust"

    def test_no_extension(self):
        """Files without extension should return 'text'."""
        assert get_fence_language("Makefile") == "text"
        assert get_fence_language("Dockerfile") == "text"


class TestExtensionMapping:
    """Tests for the extension mapping dictionary."""

    def test_supported_languages_have_fences(self):
        """All indexer-supported languages should have fence mappings."""
        # Python
        assert ".py" in EXTENSION_TO_FENCE
        # Rust
        assert ".rs" in EXTENSION_TO_FENCE
        # C
        assert ".c" in EXTENSION_TO_FENCE
        assert ".h" in EXTENSION_TO_FENCE

    def test_common_web_extensions(self):
        """Common web development extensions should be mapped."""
        assert ".js" in EXTENSION_TO_FENCE
        assert ".ts" in EXTENSION_TO_FENCE
        assert ".json" in EXTENSION_TO_FENCE


class TestContextGeneration:
    """Integration test for context generation with correct fences."""

    def test_context_uses_fence_for_python(self, tmp_path):
        """Context generation should use 'python' fence for .py files."""
        from erirpg.context import generate_context
        from erirpg.ops import Feature, TransplantPlan, Mapping
        from erirpg.graph import Graph

        # Create a minimal feature with Python code
        feature = Feature(
            name="test_feature",
            source_project="source",
            primary_module="src/module.py",
            components=["src/module.py"],
            provides=[],
            requires=[],
            code_snapshots={"src/module.py": "def hello(): pass"},
        )

        plan = TransplantPlan(
            feature_name="test_feature",
            source_project="source",
            target_project="target",
            mappings=[],
            wiring=[],
            generation_order=["src/module.py"],
        )

        target_graph = Graph(project="target")

        class MockProject:
            name = "target"
            path = str(tmp_path)

        output = generate_context(
            feature=feature,
            plan=plan,
            source_graph=None,
            target_graph=target_graph,
            target_project=MockProject(),
            source_project=None,
            output_dir=str(tmp_path),
            use_learnings=False,
        )

        # Read the generated file
        with open(output) as f:
            content = f.read()

        # Should use ```python fence
        assert "```python" in content
        assert "def hello(): pass" in content

    def test_context_uses_fence_for_rust(self, tmp_path):
        """Context generation should use 'rust' fence for .rs files."""
        from erirpg.context import generate_context
        from erirpg.ops import Feature, TransplantPlan
        from erirpg.graph import Graph

        feature = Feature(
            name="test_feature",
            source_project="source",
            primary_module="src/main.rs",
            components=["src/main.rs"],
            provides=[],
            requires=[],
            code_snapshots={"src/main.rs": "fn main() {}"},
        )

        plan = TransplantPlan(
            feature_name="test_feature",
            source_project="source",
            target_project="target",
            mappings=[],
            wiring=[],
            generation_order=["src/main.rs"],
        )

        target_graph = Graph(project="target")

        class MockProject:
            name = "target"
            path = str(tmp_path)

        output = generate_context(
            feature=feature,
            plan=plan,
            source_graph=None,
            target_graph=target_graph,
            target_project=MockProject(),
            source_project=None,
            output_dir=str(tmp_path),
            use_learnings=False,
        )

        with open(output) as f:
            content = f.read()

        assert "```rust" in content
        assert "fn main() {}" in content

    def test_context_uses_fence_for_c(self, tmp_path):
        """Context generation should use 'c' fence for .c files."""
        from erirpg.context import generate_context
        from erirpg.ops import Feature, TransplantPlan
        from erirpg.graph import Graph

        feature = Feature(
            name="test_feature",
            source_project="source",
            primary_module="src/main.c",
            components=["src/main.c"],
            provides=[],
            requires=[],
            code_snapshots={"src/main.c": "int main() { return 0; }"},
        )

        plan = TransplantPlan(
            feature_name="test_feature",
            source_project="source",
            target_project="target",
            mappings=[],
            wiring=[],
            generation_order=["src/main.c"],
        )

        target_graph = Graph(project="target")

        class MockProject:
            name = "target"
            path = str(tmp_path)

        output = generate_context(
            feature=feature,
            plan=plan,
            source_graph=None,
            target_graph=target_graph,
            target_project=MockProject(),
            source_project=None,
            output_dir=str(tmp_path),
            use_learnings=False,
        )

        with open(output) as f:
            content = f.read()

        assert "```c" in content
        assert "int main()" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
