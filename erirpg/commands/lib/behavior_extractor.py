"""
Behavior Extractor - Extract actual behavior from source code.

Uses Python AST to extract:
- Class hierarchies and their methods
- Function signatures with type hints
- Import dependencies
- Docstrings and comments
- Constants and configuration
"""

import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class ExtractedFunction:
    """Extracted function with full signature."""
    name: str
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    is_async: bool
    line_start: int
    line_end: int
    body_summary: str  # First 3 lines of body
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "args": self.args,
            "returns": self.returns,
            "docstring": self.docstring[:200] if self.docstring else None,
            "decorators": self.decorators,
            "is_async": self.is_async,
            "lines": f"{self.line_start}-{self.line_end}"
        }


@dataclass
class ExtractedClass:
    """Extracted class with methods and inheritance."""
    name: str
    bases: List[str]
    methods: List[ExtractedFunction]
    class_vars: Dict[str, str]
    docstring: Optional[str]
    line_start: int
    line_end: int
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bases": self.bases,
            "methods": [m.to_dict() for m in self.methods],
            "class_vars": self.class_vars,
            "docstring": self.docstring[:200] if self.docstring else None,
            "lines": f"{self.line_start}-{self.line_end}"
        }


@dataclass
class ExtractedModule:
    """Full module extraction."""
    path: str
    imports: List[str]
    from_imports: Dict[str, List[str]]
    classes: List[ExtractedClass]
    functions: List[ExtractedFunction]
    constants: Dict[str, Any]
    docstring: Optional[str]
    line_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "imports": self.imports,
            "from_imports": self.from_imports,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "constants": self.constants,
            "docstring": self.docstring[:200] if self.docstring else None,
            "line_count": self.line_count
        }


class BehaviorExtractor:
    """Extract behavior specifications from source code."""
    
    def extract_file(self, file_path: Path) -> ExtractedModule:
        """Extract all behaviors from a Python file."""
        try:
            source = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            source = file_path.read_text(encoding='latin-1')
        
        line_count = len(source.splitlines())
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            # Return empty module for files with syntax errors
            return ExtractedModule(
                path=str(file_path),
                imports=[],
                from_imports={},
                classes=[],
                functions=[],
                constants={},
                docstring=f"PARSE ERROR: {e}",
                line_count=line_count
            )
        
        return ExtractedModule(
            path=str(file_path),
            imports=self._extract_imports(tree),
            from_imports=self._extract_from_imports(tree),
            classes=self._extract_classes(tree, source),
            functions=self._extract_top_level_functions(tree, source),
            constants=self._extract_constants(tree),
            docstring=ast.get_docstring(tree),
            line_count=line_count
        )
    
    def _extract_classes(self, tree: ast.AST, source: str) -> List[ExtractedClass]:
        """Extract all class definitions."""
        classes = []
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                class_vars = {}
                
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(self._extract_function(item, source))
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                try:
                                    class_vars[target.id] = ast.unparse(item.value)[:100]
                                except:
                                    class_vars[target.id] = "<complex>"
                    elif isinstance(item, ast.AnnAssign) and item.target:
                        if isinstance(item.target, ast.Name):
                            try:
                                val = ast.unparse(item.value)[:100] if item.value else "None"
                                class_vars[item.target.id] = val
                            except:
                                class_vars[item.target.id] = "<complex>"
                
                classes.append(ExtractedClass(
                    name=node.name,
                    bases=self._extract_bases(node.bases),
                    methods=methods,
                    class_vars=class_vars,
                    docstring=ast.get_docstring(node),
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno
                ))
        
        return classes
    
    def _extract_bases(self, bases: List[ast.expr]) -> List[str]:
        """Extract base class names."""
        result = []
        for base in bases:
            try:
                result.append(ast.unparse(base))
            except:
                if isinstance(base, ast.Name):
                    result.append(base.id)
                elif isinstance(base, ast.Attribute):
                    result.append(base.attr)
                else:
                    result.append("<complex>")
        return result
    
    def _extract_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], source: str) -> ExtractedFunction:
        """Extract function signature and summary."""
        args = []
        
        # Regular args
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        
        # **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        returns = None
        if node.returns:
            try:
                returns = ast.unparse(node.returns)
            except:
                returns = "<complex>"
        
        # Get first 3 lines of body (excluding docstring)
        body_lines = []
        for stmt in node.body[:5]:
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)):
                try:
                    line = ast.unparse(stmt)[:80]
                    body_lines.append(line)
                except:
                    body_lines.append("<complex statement>")
            if len(body_lines) >= 3:
                break
        
        decorators = []
        for d in node.decorator_list:
            try:
                decorators.append(ast.unparse(d))
            except:
                if isinstance(d, ast.Name):
                    decorators.append(d.id)
                else:
                    decorators.append("<decorator>")
        
        return ExtractedFunction(
            name=node.name,
            args=args,
            returns=returns,
            docstring=ast.get_docstring(node),
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            body_summary="\n".join(body_lines)
        )
    
    def _extract_top_level_functions(self, tree: ast.AST, source: str) -> List[ExtractedFunction]:
        """Extract top-level function definitions only."""
        functions = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._extract_function(node, source))
        return functions
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements."""
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
        return imports
    
    def _extract_from_imports(self, tree: ast.AST) -> Dict[str, List[str]]:
        """Extract from-import statements."""
        from_imports = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                if module in from_imports:
                    from_imports[module].extend(names)
                else:
                    from_imports[module] = names
        return from_imports
    
    def _extract_constants(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract module-level constants."""
        constants = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        try:
                            constants[target.id] = ast.literal_eval(node.value)
                        except:
                            try:
                                constants[target.id] = ast.unparse(node.value)[:100]
                            except:
                                constants[target.id] = "<complex>"
        return constants


def extract_module_behavior(
    source_path: Path,
    skip_dirs: Optional[set] = None
) -> Dict[str, ExtractedModule]:
    """Extract behavior from all Python files in a module."""
    if skip_dirs is None:
        skip_dirs = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".eggs"}
    
    extractor = BehaviorExtractor()
    modules = {}
    
    if source_path.is_file():
        modules[source_path.name] = extractor.extract_file(source_path)
        return modules
    
    for py_file in source_path.rglob("*.py"):
        rel_path = py_file.relative_to(source_path)
        
        # Skip excluded directories
        if any(skip in rel_path.parts for skip in skip_dirs):
            continue
        
        try:
            modules[str(rel_path)] = extractor.extract_file(py_file)
        except Exception as e:
            # Log but continue on errors
            modules[str(rel_path)] = ExtractedModule(
                path=str(py_file),
                imports=[],
                from_imports={},
                classes=[],
                functions=[],
                constants={},
                docstring=f"EXTRACTION ERROR: {e}",
                line_count=0
            )
    
    return modules


def generate_behavior_markdown(
    program: str,
    section: str,
    extracted: Dict[str, ExtractedModule],
    description: str = ""
) -> str:
    """Generate behavior spec markdown from extracted code."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    lines = [
        "---",
        f"program: {program}",
        f"section: {section}",
        "type: behavior-spec",
        "portable: true",
        "extracted: true",
        f"created: {today}",
        f"updated: {today}",
        "---",
        "",
        f"# {section.replace('/', ' / ').title()} - Behavior Spec",
        "",
        "> **Extracted from source code** - This is actual extracted behavior, not a template.",
        "",
    ]
    
    if description:
        lines.extend([
            "## Purpose",
            "",
            description,
            "",
        ])
    
    # Summary statistics
    total_classes = sum(len(m.classes) for m in extracted.values())
    total_functions = sum(len(m.functions) for m in extracted.values())
    total_lines = sum(m.line_count for m in extracted.values())
    
    lines.extend([
        "## Summary",
        "",
        f"- **Files:** {len(extracted)}",
        f"- **Classes:** {total_classes}",
        f"- **Functions:** {total_functions}",
        f"- **Lines:** {total_lines:,}",
        "",
    ])
    
    # Add extracted classes
    if total_classes > 0:
        lines.extend(["## Classes", ""])
        for file_path, module in sorted(extracted.items()):
            for cls in module.classes:
                bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"### `{cls.name}{bases_str}`")
                lines.append(f"- **File:** `{file_path}`")
                lines.append(f"- **Lines:** {cls.line_start}-{cls.line_end}")
                if cls.docstring:
                    doc_first_line = cls.docstring.split('\n')[0][:100]
                    lines.append(f"- **Purpose:** {doc_first_line}")
                
                if cls.methods:
                    lines.append("- **Methods:**")
                    for method in cls.methods:
                        args_str = ", ".join(method.args[:5])
                        if len(method.args) > 5:
                            args_str += ", ..."
                        ret_str = f" -> {method.returns}" if method.returns else ""
                        lines.append(f"  - `{method.name}({args_str}){ret_str}`")
                
                lines.append("")
    
    # Add extracted functions (top-level only, limit display)
    public_functions = []
    for file_path, module in sorted(extracted.items()):
        for func in module.functions:
            if not func.name.startswith("_"):
                public_functions.append((file_path, func))
    
    if public_functions:
        lines.extend(["## Functions", ""])
        for file_path, func in public_functions[:50]:  # Limit to 50
            args_str = ", ".join(func.args[:4])
            if len(func.args) > 4:
                args_str += ", ..."
            ret_str = f" -> {func.returns}" if func.returns else ""
            lines.append(f"- `{func.name}({args_str}){ret_str}` - `{file_path}`")
        
        if len(public_functions) > 50:
            lines.append(f"- ... and {len(public_functions) - 50} more functions")
        lines.append("")
    
    # Add imports (dependencies)
    all_imports = set()
    for module in extracted.values():
        all_imports.update(module.imports)
        all_imports.update(module.from_imports.keys())
    
    external_imports = sorted([
        imp for imp in all_imports 
        if imp and not imp.startswith(".") and not imp.startswith("erirpg")
    ])
    
    if external_imports:
        lines.extend(["## Dependencies", ""])
        for imp in external_imports[:30]:
            lines.append(f"- `{imp}`")
        if len(external_imports) > 30:
            lines.append(f"- ... and {len(external_imports) - 30} more")
        lines.append("")
    
    # Add constants
    all_constants = {}
    for module in extracted.values():
        all_constants.update(module.constants)
    
    if all_constants:
        lines.extend(["## Constants", ""])
        for name, value in sorted(all_constants.items())[:20]:
            val_str = str(value)[:50]
            lines.append(f"- `{name}` = `{val_str}`")
        if len(all_constants) > 20:
            lines.append(f"- ... and {len(all_constants) - 20} more")
        lines.append("")
    
    return "\n".join(lines)
