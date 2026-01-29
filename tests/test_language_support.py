"""
Test P1-003: Align CLI language support with indexer.

Verifies that CLI and new mode only offer languages that the indexer supports.
"""

import pytest
import click

from erirpg.modes.new import QUESTIONS, get_structure_for
from erirpg.registry import detect_project_language


# Languages with full indexer support (parsers exist)
SUPPORTED_LANGUAGES = {"python", "rust", "c", "mojo"}


class TestCLILanguageSupport:
    """Tests for CLI language option alignment with indexer."""

    def test_cli_add_command_languages(self):
        """Verify add command only allows supported languages."""
        from erirpg.cli import cli

        add = cli.commands['add']
        # Get the --lang option from the add command
        lang_option = None
        for param in add.params:
            if param.name == "lang":
                lang_option = param
                break

        assert lang_option is not None, "add command should have --lang option"

        # Check that it's a Choice with only supported languages
        assert isinstance(lang_option.type, click.Choice)
        cli_languages = set(lang_option.type.choices)
        assert cli_languages == SUPPORTED_LANGUAGES, \
            f"CLI languages {cli_languages} should match supported {SUPPORTED_LANGUAGES}"


class TestNewModeLanguageSupport:
    """Tests for new mode language options alignment with indexer."""

    def test_new_mode_language_question(self):
        """Verify new mode only offers supported languages."""
        language_question = None
        for q in QUESTIONS:
            if q.id == "language":
                language_question = q
                break

        assert language_question is not None, "new mode should have language question"
        assert language_question.options is not None, "language question should have options"

        new_mode_languages = set(language_question.options)
        assert new_mode_languages == SUPPORTED_LANGUAGES, \
            f"New mode languages {new_mode_languages} should match supported {SUPPORTED_LANGUAGES}"

    def test_get_structure_for_supported_languages(self):
        """Verify get_structure_for handles all supported languages."""
        for lang in SUPPORTED_LANGUAGES:
            dirs, files = get_structure_for(lang, None)
            assert isinstance(dirs, (list, tuple)), f"{lang} should return dirs"
            assert isinstance(files, (list, tuple)), f"{lang} should return files"
            assert len(dirs) > 0, f"{lang} should have at least one directory"
            assert len(files) > 0, f"{lang} should have at least one file"

    def test_get_structure_for_unsupported_languages(self):
        """Verify get_structure_for falls back gracefully for unsupported languages."""
        # Should not crash, just return default
        dirs, files = get_structure_for("cobol", None)
        assert dirs is not None
        assert files is not None


class TestLanguageDetection:
    """Tests for auto-detection returning only supported languages."""

    def test_detect_returns_supported_or_unknown(self, tmp_path):
        """Auto-detection should only return supported languages or 'unknown'."""
        # Test python detection
        (tmp_path / "pyproject.toml").write_text("[project]")
        assert detect_project_language(str(tmp_path)) == "python"

        # Clean up
        (tmp_path / "pyproject.toml").unlink()

        # Test rust detection
        (tmp_path / "Cargo.toml").write_text("[package]")
        assert detect_project_language(str(tmp_path)) == "rust"

        # Clean up
        (tmp_path / "Cargo.toml").unlink()

        # Test c detection
        (tmp_path / "main.c").write_text("int main() {}")
        assert detect_project_language(str(tmp_path)) == "c"

        # Clean up
        (tmp_path / "main.c").unlink()

        # Test unknown detection
        (tmp_path / "file.txt").write_text("text")
        result = detect_project_language(str(tmp_path))
        assert result in SUPPORTED_LANGUAGES | {"unknown"}, \
            f"Detection should return supported language or 'unknown', got '{result}'"


class TestIndexerLanguageSupport:
    """Tests for indexer language support."""

    def test_indexer_supports_claimed_languages(self):
        """Verify indexer actually supports the languages we claim."""
        from erirpg.indexer import index_project
        from erirpg.registry import Project
        import tempfile
        import os

        for lang in SUPPORTED_LANGUAGES:
            # Create minimal project
            with tempfile.TemporaryDirectory() as tmpdir:
                project = Project(
                    name=f"test_{lang}",
                    path=tmpdir,
                    lang=lang,
                )

                # Create a minimal file for each language
                if lang == "python":
                    with open(os.path.join(tmpdir, "main.py"), "w") as f:
                        f.write("def main(): pass\n")
                elif lang == "rust":
                    with open(os.path.join(tmpdir, "main.rs"), "w") as f:
                        f.write("fn main() {}\n")
                elif lang == "c":
                    with open(os.path.join(tmpdir, "main.c"), "w") as f:
                        f.write("int main() { return 0; }\n")

                # Should not raise NotImplementedError
                try:
                    graph = index_project(project, verbose=False)
                    # If we get here, the language is actually supported
                    assert True
                except NotImplementedError as e:
                    pytest.fail(f"Indexer claims to support {lang} but raised: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
