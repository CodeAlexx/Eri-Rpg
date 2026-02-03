"""
Tests for language-specific parsers.

Each parser should:
- Extract imports/dependencies
- Extract interfaces (classes, functions, exports)
- Extract module docstrings/summaries
- Handle errors gracefully
"""

import tempfile
import pytest
from pathlib import Path

from erirpg.parsers import get_parser_for_file, detect_language
from erirpg.parsers.python import parse_python_file, resolve_import_to_module, classify_external_package
from erirpg.parsers.rust import parse_rust_file, resolve_use_to_module, classify_external_crate
from erirpg.parsers.c import parse_c_file, resolve_include_to_module
from erirpg.parsers.mojo import parse_mojo_file, is_mojo_file, resolve_import_to_module as resolve_mojo_import, classify_external_package as classify_mojo_package


# ============================================================================
# Infrastructure Tests
# ============================================================================

def test_get_parser_for_file():
    """Test parser detection for different file types."""
    assert get_parser_for_file("test.py") == parse_python_file
    assert get_parser_for_file("test.rs") == parse_rust_file
    assert get_parser_for_file("test.c") == parse_c_file
    assert get_parser_for_file("test.h") == parse_c_file
    assert get_parser_for_file("test.cpp") == parse_c_file
    assert get_parser_for_file("test.hpp") == parse_c_file
    assert get_parser_for_file("test.mojo") == parse_mojo_file
    assert get_parser_for_file("test.🔥") == parse_mojo_file
    assert get_parser_for_file("test.txt") is None
    assert get_parser_for_file("test.js") is None


def test_detect_language():
    """Test language detection from file extension."""
    assert detect_language("test.py") == "python"
    assert detect_language("test.rs") == "rust"
    assert detect_language("test.c") == "c"
    assert detect_language("test.h") == "c"
    assert detect_language("test.cpp") == "c"
    assert detect_language("test.mojo") == "mojo"
    assert detect_language("test.🔥") == "mojo"
    assert detect_language("test.txt") == "unknown"


# ============================================================================
# Python Parser Tests
# ============================================================================

def test_python_parse_module():
    """Test parsing a Python module with docstring, imports, classes, functions."""
    source = '''"""Module docstring for testing."""
import os
import sys
from typing import Dict, List
from pathlib import Path

class MyClass:
    """Class docstring."""
    def method1(self):
        pass

    def method2(self, x: int) -> str:
        pass

def my_function(a: int, b: str = "default") -> bool:
    """Function docstring."""
    return True

async def async_func():
    """Async function."""
    pass

CONSTANT = 42
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_python_file(f.name)

        # Check docstring
        assert result["docstring"] == "Module docstring for testing."

        # Check imports
        assert len(result["imports"]) == 4
        assert {"type": "import", "name": "os", "asname": None} in result["imports"]
        assert {"type": "import", "name": "sys", "asname": None} in result["imports"]

        # Check from imports
        typing_import = next(imp for imp in result["imports"] if imp.get("module") == "typing")
        assert typing_import["type"] == "from"
        assert "Dict" in typing_import["names"]
        assert "List" in typing_import["names"]

        # Check class
        classes = [i for i in result["interfaces"] if i["type"] == "class"]
        assert len(classes) == 1
        assert classes[0]["name"] == "MyClass"
        assert "method1" in classes[0]["methods"]
        assert "method2" in classes[0]["methods"]

        # Check functions
        funcs = [i for i in result["interfaces"] if i["type"] == "function"]
        assert len(funcs) == 1
        assert funcs[0]["name"] == "my_function"
        assert "int" in funcs[0]["signature"]

        # Check async function
        async_funcs = [i for i in result["interfaces"] if i["type"] == "async_function"]
        assert len(async_funcs) == 1
        assert async_funcs[0]["name"] == "async_func"

        # Check constant
        consts = [i for i in result["interfaces"] if i["type"] == "const"]
        assert len(consts) == 1
        assert consts[0]["name"] == "CONSTANT"

        # Cleanup
        Path(f.name).unlink()


def test_python_handle_syntax_error():
    """Test that parser handles syntax errors gracefully."""
    source = '''
def broken_function(
    # Missing closing paren and body
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_python_file(f.name)

        # Should return error without crashing
        assert "error" in result
        assert "SyntaxError" in result["error"]
        assert result["imports"] == []
        assert result["interfaces"] == []

        # Cleanup
        Path(f.name).unlink()


def test_python_resolve_import():
    """Test resolving imports to project modules."""
    project_modules = [
        "myproject/utils.py",
        "myproject/core/__init__.py",
        "myproject/core/engine.py",
        "tests/test_utils.py",
    ]

    # Test absolute import
    imp = {"type": "import", "name": "myproject.utils", "asname": None}
    assert resolve_import_to_module(imp, project_modules) == "myproject/utils.py"

    # Test from import
    imp = {"type": "from", "module": "myproject.core", "names": ["engine"], "level": 0}
    assert resolve_import_to_module(imp, project_modules) == "myproject/core/__init__.py"

    # Test external import (should return None)
    imp = {"type": "import", "name": "numpy", "asname": None}
    assert resolve_import_to_module(imp, project_modules) is None

    # Test relative import
    imp = {"type": "from", "module": "utils", "names": ["helper"], "level": 1}
    result = resolve_import_to_module(imp, project_modules, current_module="myproject/core/engine.py")
    assert result == "myproject/core/utils.py" or result is None  # May not exist


def test_python_classify_external_package():
    """Test extracting external package names."""
    # Regular import
    imp = {"type": "import", "name": "numpy.array"}
    assert classify_external_package(imp) == "numpy"

    # From import
    imp = {"type": "from", "module": "torch.nn", "names": ["Module"], "level": 0}
    assert classify_external_package(imp) == "torch"

    # Relative import (should return None)
    imp = {"type": "from", "module": "utils", "names": ["helper"], "level": 1}
    assert classify_external_package(imp) is None


# ============================================================================
# Rust Parser Tests
# ============================================================================

def test_rust_parse_module():
    """Test parsing a Rust module."""
    source = '''//! Module documentation
//! Second line

use std::collections::HashMap;
use serde::{Serialize, Deserialize};

pub mod utils;

/// Function documentation
pub fn my_function(x: i32, y: &str) -> Result<String, Error> {
    Ok(format!("{}: {}", x, y))
}

/// Struct documentation
pub struct MyStruct {
    name: String,
    count: usize,
}

pub enum Status {
    Active,
    Inactive,
    Pending,
}

pub trait MyTrait {
    fn do_something(&self);
}

pub const MAX_SIZE: usize = 1024;
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_rust_file(f.name)

        # Check docstring
        assert "Module documentation" in result["docstring"]

        # Check imports
        use_imports = [i for i in result["imports"] if i["type"] == "use"]
        assert len(use_imports) >= 2
        assert any("HashMap" in i["name"] for i in use_imports)

        # Check mod declarations
        mod_imports = [i for i in result["imports"] if i["type"] == "mod"]
        assert len(mod_imports) == 1
        assert mod_imports[0]["name"] == "utils"

        # Check functions
        funcs = [i for i in result["interfaces"] if i["type"] == "function"]
        assert len(funcs) >= 1
        func = next(f for f in funcs if f["name"] == "my_function")
        assert "i32" in func["signature"]
        assert "Result" in func["signature"]

        # Check structs
        structs = [i for i in result["interfaces"] if i["type"] == "struct"]
        assert len(structs) >= 1
        struct = next(s for s in structs if s["name"] == "MyStruct")
        assert "name" in struct["methods"]  # Fields stored as methods
        assert "count" in struct["methods"]

        # Check enums
        enums = [i for i in result["interfaces"] if i["type"] == "enum"]
        assert len(enums) >= 1
        enum = next(e for e in enums if e["name"] == "Status")
        assert "Active" in enum["methods"]  # Variants stored as methods

        # Check traits
        traits = [i for i in result["interfaces"] if i["type"] == "trait"]
        assert len(traits) >= 1
        trait = next(t for t in traits if t["name"] == "MyTrait")

        # Check constants
        consts = [i for i in result["interfaces"] if i["type"] == "const"]
        assert len(consts) >= 1
        const = next(c for c in consts if c["name"] == "MAX_SIZE")

        # Cleanup
        Path(f.name).unlink()


def test_rust_resolve_use():
    """Test resolving use statements to project modules."""
    project_modules = [
        "src/utils.rs",
        "src/core/mod.rs",
        "src/core/engine.rs",
    ]

    # Test mod declaration
    use_info = {"type": "mod", "name": "utils"}
    assert resolve_use_to_module(use_info, project_modules) == "src/utils.rs"

    # Test external crate (should return None)
    use_info = {"type": "use", "name": "serde::Serialize", "crate": "serde"}
    assert resolve_use_to_module(use_info, project_modules) is None


def test_rust_classify_external_crate():
    """Test extracting external crate names."""
    # External crate
    use_info = {"type": "use", "name": "serde::Serialize", "crate": "serde"}
    assert classify_external_crate(use_info) == "serde"

    # Internal crate
    use_info = {"type": "use", "name": "crate::utils::helper", "crate": "crate"}
    assert classify_external_crate(use_info) is None

    # Mod declaration
    use_info = {"type": "mod", "name": "utils"}
    assert classify_external_crate(use_info) is None


# ============================================================================
# C Parser Tests
# ============================================================================

def test_c_parse_module():
    """Test parsing a C file."""
    source = '''/*
 * File documentation
 */

#include <stdio.h>
#include "myheader.h"

#define MAX_SIZE 1024
#define MIN(a, b) ((a) < (b) ? (a) : (b))

typedef struct {
    char name[100];
    int age;
} Person;

struct Point {
    int x;
    int y;
};

enum Color {
    RED,
    GREEN,
    BLUE
};

/* Function documentation */
int my_function(int x, char *y) {
    return x + strlen(y);
}

void helper(void) {
    printf("Hello\\n");
}
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_c_file(f.name)

        # Check docstring
        assert "File documentation" in result["docstring"]

        # Check includes
        includes = [i for i in result["imports"] if i["type"] == "include"]
        assert len(includes) == 2
        assert any(i["name"] == "stdio.h" and i["is_system"] for i in includes)
        assert any(i["name"] == "myheader.h" and not i["is_system"] for i in includes)

        # Check functions
        funcs = [i for i in result["interfaces"] if i["type"] == "function"]
        assert len(funcs) >= 2
        func = next((f for f in funcs if f["name"] == "my_function"), None)
        assert func is not None
        assert "int" in func["signature"]

        # Check structs
        structs = [i for i in result["interfaces"] if i["type"] == "struct"]
        assert len(structs) >= 2
        # Either Person or Point
        assert any(s["name"] in ["Person", "Point"] for s in structs)

        # Check enums
        enums = [i for i in result["interfaces"] if i["type"] == "enum"]
        assert len(enums) >= 1
        assert any(e["name"] == "Color" for e in enums)

        # Check macros (but not include guards)
        macros = [i for i in result["interfaces"] if i["type"] == "macro"]
        assert len(macros) >= 1
        assert any(m["name"] == "MAX_SIZE" for m in macros)

        # Cleanup
        Path(f.name).unlink()


def test_c_resolve_include():
    """Test resolving include statements to project headers."""
    project_headers = [
        "include/myheader.h",
        "src/utils.h",
        "src/core/engine.h",
    ]

    # Test project header
    inc = {"type": "include", "name": "myheader.h", "is_system": False}
    assert resolve_include_to_module(inc, project_headers) == "include/myheader.h"

    # Test system header (should return None)
    inc = {"type": "include", "name": "stdio.h", "is_system": True}
    assert resolve_include_to_module(inc, project_headers) is None


# ============================================================================
# Mojo Parser Tests
# ============================================================================

def test_mojo_is_mojo_file():
    """Test Mojo file detection."""
    assert is_mojo_file("test.mojo")
    assert is_mojo_file("test.🔥")
    assert not is_mojo_file("test.py")
    assert not is_mojo_file("test.rs")


def test_mojo_parse_module():
    """Test parsing a Mojo module."""
    source = '''"""Module docstring."""

import math
from collections import Dict, List

fn my_function[T: AnyType](x: Int, y: String) -> Bool:
    """Function docstring."""
    return True

def dynamic_function(a, b):
    """Dynamic function."""
    return a + b

@value
struct MyStruct[T: AnyType]:
    """Struct docstring."""
    var data: T

    fn method(self) -> Int:
        return 42

trait MyTrait:
    """Trait docstring."""
    fn do_something(self)

alias MyInt = Int32

let CONSTANT: Int = 100
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.mojo', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_mojo_file(f.name)

        # Check docstring
        assert "Module docstring" in result["docstring"]

        # Check imports
        imports = [i for i in result["imports"] if i["type"] == "import"]
        assert len(imports) >= 1
        assert any(i["name"] == "math" for i in imports)

        # Check from imports
        from_imports = [i for i in result["imports"] if i["type"] == "from"]
        assert len(from_imports) >= 1
        assert any("Dict" in i["names"] for i in from_imports)

        # Check fn functions
        fns = [i for i in result["interfaces"] if i["type"] == "fn"]
        assert len(fns) >= 1
        fn = next((f for f in fns if f["name"] == "my_function"), None)
        assert fn is not None
        assert "Int" in fn["signature"]
        assert "Bool" in fn["signature"]

        # Check def functions
        defs = [i for i in result["interfaces"] if i["type"] == "def"]
        assert len(defs) >= 1
        def_func = next((d for d in defs if d["name"] == "dynamic_function"), None)
        assert def_func is not None

        # Check structs
        structs = [i for i in result["interfaces"] if i["type"] == "struct"]
        assert len(structs) >= 1
        struct = next((s for s in structs if s["name"] == "MyStruct"), None)
        assert struct is not None
        assert "data" in struct.get("fields", [])
        assert "method" in struct.get("methods", [])

        # Check traits
        traits = [i for i in result["interfaces"] if i["type"] == "trait"]
        assert len(traits) >= 1
        trait = next((t for t in traits if t["name"] == "MyTrait"), None)
        assert trait is not None

        # Check aliases
        aliases = [i for i in result["interfaces"] if i["type"] == "alias"]
        assert len(aliases) >= 1
        alias = next((a for a in aliases if a["name"] == "MyInt"), None)
        assert alias is not None

        # Cleanup
        Path(f.name).unlink()


def test_mojo_handle_fire_emoji_extension():
    """Test that Mojo parser handles .🔥 extension."""
    source = '''fn test() -> Int:
    return 42
'''

    # Create file with fire emoji extension
    with tempfile.NamedTemporaryFile(mode='w', suffix='.🔥', delete=False) as f:
        f.write(source)
        f.flush()

        result = parse_mojo_file(f.name)

        # Should parse successfully
        fns = [i for i in result["interfaces"] if i["type"] == "fn"]
        assert len(fns) == 1
        assert fns[0]["name"] == "test"

        # Cleanup
        Path(f.name).unlink()


def test_mojo_resolve_import():
    """Test resolving Mojo imports to project modules."""
    project_modules = [
        "myproject/utils.mojo",
        "myproject/core/__init__.mojo",
        "myproject/core/engine.mojo",
    ]

    # Test import
    imp = {"type": "import", "name": "myproject.utils"}
    assert resolve_mojo_import(imp, project_modules) == "myproject/utils.mojo"

    # Test from import
    imp = {"type": "from", "module": "myproject.core"}
    result = resolve_mojo_import(imp, project_modules)
    assert result in ["myproject/core/__init__.mojo", None]

    # Test external import
    imp = {"type": "import", "name": "external"}
    assert resolve_mojo_import(imp, project_modules) is None


def test_mojo_classify_external_package():
    """Test extracting external package names."""
    # Regular import
    imp = {"type": "import", "name": "math.vector"}
    assert classify_mojo_package(imp) == "math"

    # From import
    imp = {"type": "from", "module": "collections.dict"}
    assert classify_mojo_package(imp) == "collections"

    # Python interop
    imp = {"type": "python_interop", "name": "numpy"}
    assert classify_mojo_package(imp) == "python:numpy"


# ============================================================================
# Integration Tests
# ============================================================================

def test_all_parsers_return_standard_format():
    """Test that all parsers return the same dict structure."""
    required_keys = {"docstring", "imports", "interfaces", "lines"}

    # Python
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('"""Test."""\n')
        f.flush()
        result = parse_python_file(f.name)
        assert set(result.keys()) >= required_keys
        Path(f.name).unlink()

    # Rust
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
        f.write('//! Test\n')
        f.flush()
        result = parse_rust_file(f.name)
        assert set(result.keys()) >= required_keys
        Path(f.name).unlink()

    # C
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write('/* Test */\n')
        f.flush()
        result = parse_c_file(f.name)
        assert set(result.keys()) >= required_keys
        Path(f.name).unlink()

    # Mojo
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mojo', delete=False) as f:
        f.write('"""Test."""\n')
        f.flush()
        result = parse_mojo_file(f.name)
        assert set(result.keys()) >= required_keys
        Path(f.name).unlink()


def test_parsers_handle_empty_files():
    """Test that parsers handle empty files without crashing."""
    # Python
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('')
        f.flush()
        result = parse_python_file(f.name)
        assert result["imports"] == []
        assert result["interfaces"] == []
        Path(f.name).unlink()

    # Rust
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
        f.write('')
        f.flush()
        result = parse_rust_file(f.name)
        assert result["imports"] == []
        assert result["interfaces"] == []
        Path(f.name).unlink()

    # C
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write('')
        f.flush()
        result = parse_c_file(f.name)
        assert result["imports"] == []
        assert result["interfaces"] == []
        Path(f.name).unlink()

    # Mojo
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mojo', delete=False) as f:
        f.write('')
        f.flush()
        result = parse_mojo_file(f.name)
        assert result["imports"] == []
        assert result["interfaces"] == []
        Path(f.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
