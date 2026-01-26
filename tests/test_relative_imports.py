"""
Test P1-002: Resolve relative imports for Python indexing.

Verifies that relative imports (from . import, from .. import) are correctly
resolved to internal module paths based on the importing module's location.
"""

import pytest

from erirpg.parsers.python import (
    resolve_import_to_module,
    _resolve_relative_import,
)


# Fixture: Project module paths for a typical package structure
@pytest.fixture
def project_modules():
    """Simulated project with nested package structure."""
    return [
        "pkg/__init__.py",
        "pkg/core.py",
        "pkg/utils.py",
        "pkg/sub/__init__.py",
        "pkg/sub/module.py",
        "pkg/sub/helper.py",
        "pkg/other/__init__.py",
        "pkg/other/stuff.py",
    ]


class TestRelativeImportResolution:
    """Tests for _resolve_relative_import helper."""

    def test_single_dot_same_package(self, project_modules):
        """from . import utils -> pkg/utils.py when in pkg/core.py"""
        result = _resolve_relative_import(
            module="utils",
            level=1,
            current_module="pkg/core.py",
            project_modules=project_modules,
        )
        assert result == "pkg/utils.py"

    def test_single_dot_subpackage(self, project_modules):
        """from .helper import x -> pkg/sub/helper.py when in pkg/sub/module.py"""
        result = _resolve_relative_import(
            module="helper",
            level=1,
            current_module="pkg/sub/module.py",
            project_modules=project_modules,
        )
        assert result == "pkg/sub/helper.py"

    def test_double_dot_parent_package(self, project_modules):
        """from .. import core -> pkg/core.py when in pkg/sub/module.py"""
        result = _resolve_relative_import(
            module="core",
            level=2,
            current_module="pkg/sub/module.py",
            project_modules=project_modules,
        )
        assert result == "pkg/core.py"

    def test_double_dot_sibling_package(self, project_modules):
        """from ..other import stuff -> pkg/other/stuff.py when in pkg/sub/module.py"""
        result = _resolve_relative_import(
            module="other.stuff",
            level=2,
            current_module="pkg/sub/module.py",
            project_modules=project_modules,
        )
        assert result == "pkg/other/stuff.py"

    def test_single_dot_package_init(self, project_modules):
        """from . import sub -> pkg/sub/__init__.py when in pkg/__init__.py"""
        result = _resolve_relative_import(
            module="sub",
            level=1,
            current_module="pkg/__init__.py",
            project_modules=project_modules,
        )
        assert result == "pkg/sub/__init__.py"

    def test_empty_module_imports_init(self, project_modules):
        """from . import -> pkg/sub/__init__.py when in pkg/sub/module.py"""
        result = _resolve_relative_import(
            module="",
            level=1,
            current_module="pkg/sub/module.py",
            project_modules=project_modules,
        )
        assert result == "pkg/sub/__init__.py"

    def test_too_many_dots_returns_none(self, project_modules):
        """from .... import x -> None (can't go above root)"""
        result = _resolve_relative_import(
            module="something",
            level=4,
            current_module="pkg/sub/module.py",
            project_modules=project_modules,
        )
        assert result is None

    def test_no_current_module_returns_none(self, project_modules):
        """Can't resolve relative import without knowing current module."""
        result = _resolve_relative_import(
            module="utils",
            level=1,
            current_module="",
            project_modules=project_modules,
        )
        assert result is None

    def test_nonexistent_module_returns_none(self, project_modules):
        """from .nonexistent import x -> None"""
        result = _resolve_relative_import(
            module="nonexistent",
            level=1,
            current_module="pkg/core.py",
            project_modules=project_modules,
        )
        assert result is None


class TestResolveImportToModuleWithRelative:
    """Tests for resolve_import_to_module with relative imports."""

    def test_relative_import_resolved(self, project_modules):
        """Relative imports are resolved when current_module is provided."""
        import_info = {
            "type": "from",
            "module": "utils",
            "names": ["helper_func"],
            "level": 1,
        }
        result = resolve_import_to_module(
            import_info,
            project_modules,
            project_name="pkg",
            current_module="pkg/core.py",
        )
        assert result == "pkg/utils.py"

    def test_relative_import_without_context_returns_none(self, project_modules):
        """Relative imports return None without current_module context."""
        import_info = {
            "type": "from",
            "module": "utils",
            "names": ["helper_func"],
            "level": 1,
        }
        # No current_module provided
        result = resolve_import_to_module(
            import_info,
            project_modules,
            project_name="pkg",
            current_module="",
        )
        assert result is None

    def test_absolute_import_still_works(self, project_modules):
        """Absolute imports still resolve correctly."""
        import_info = {
            "type": "from",
            "module": "pkg.utils",
            "names": ["helper_func"],
            "level": 0,
        }
        result = resolve_import_to_module(
            import_info,
            project_modules,
            project_name="pkg",
            current_module="pkg/core.py",
        )
        assert result == "pkg/utils.py"

    def test_deep_relative_import(self, project_modules):
        """from ..other.stuff import x in pkg/sub/module.py"""
        import_info = {
            "type": "from",
            "module": "other.stuff",
            "names": ["x"],
            "level": 2,
        }
        result = resolve_import_to_module(
            import_info,
            project_modules,
            project_name="pkg",
            current_module="pkg/sub/module.py",
        )
        assert result == "pkg/other/stuff.py"


class TestIntegrationWithParser:
    """Integration test: parser extracts imports, resolver resolves them."""

    def test_full_workflow(self, project_modules, tmp_path):
        """Parse a file with relative imports and verify resolution."""
        from erirpg.parsers.python import parse_python_file

        # Create a test file with relative imports
        # Note: 'from ..other import stuff' imports 'stuff' from pkg/other/__init__.py
        # To import from pkg/other/stuff.py, use 'from ..other.stuff import x'
        test_file = tmp_path / "pkg" / "sub" / "module.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("""
from . import helper
from .. import core
from ..other.stuff import something

def my_function():
    pass
""")

        # Parse the file
        parsed = parse_python_file(str(test_file))

        # Verify imports were extracted
        assert len(parsed["imports"]) == 3

        # Resolve each import
        resolved = []
        for imp in parsed["imports"]:
            result = resolve_import_to_module(
                imp,
                project_modules,
                project_name="pkg",
                current_module="pkg/sub/module.py",
            )
            if result:
                resolved.append(result)

        # Verify all relative imports resolved correctly
        assert "pkg/sub/helper.py" in resolved
        assert "pkg/core.py" in resolved
        assert "pkg/other/stuff.py" in resolved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
