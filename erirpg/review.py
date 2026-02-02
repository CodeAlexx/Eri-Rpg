"""
CRITIC-based code review with structured output.

Applies CRITIC persona to files and extracts:
- [RISK] Security holes, failure modes, edge cases
- [CONTRACT] APIs, interfaces, expected behaviors
- [DEBT] Technical debt, shortcuts, TODOs
- [DECISION] Architecture choices, tradeoffs

Token discipline:
- MAX_INPUT_TOKENS = 8000 (what CRITIC sees)
- MAX_OUTPUT_TOKENS = 4000 (output budget)
- Uses learnings by default, --full for raw source
- Hash-based caching to skip unchanged files
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib
import json
import os
import glob

# Try to import from context, but provide fallbacks if tiktoken unavailable
try:
    from erirpg.context import count_tokens, truncate_code, get_fence_language
except ImportError:
    # Fallback implementations when tiktoken is not available
    def count_tokens(text: str) -> int:
        """Estimate tokens using ~4 chars per token heuristic."""
        if not text:
            return 0
        return len(text) // 4
    
    def truncate_code(code: str, max_tokens: int, file_path: str = "") -> tuple:
        """Simple truncation based on estimated tokens."""
        if not code:
            return "", 0, False
        
        current_tokens = count_tokens(code)
        if current_tokens <= max_tokens:
            return code, current_tokens, False
        
        # Truncate by lines
        lines = code.split('\n')
        max_chars = max_tokens * 4
        result_lines = []
        char_count = 0
        
        for line in lines:
            if char_count + len(line) > max_chars:
                break
            result_lines.append(line)
            char_count += len(line) + 1
        
        result_lines.append("")
        result_lines.append(f"# ... [truncated to fit {max_tokens} token budget]")
        if file_path:
            result_lines.append(f"# Full source: {file_path}")
        
        truncated = '\n'.join(result_lines)
        return truncated, count_tokens(truncated), True
    
    def get_fence_language(file_path: str) -> str:
        """Get the appropriate code fence language for a file path."""
        from pathlib import Path
        ext_map = {".py": "python", ".rs": "rust", ".go": "go", ".js": "javascript",
                   ".ts": "typescript", ".c": "c", ".cpp": "cpp", ".java": "java"}
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "text")
from erirpg.persona import Persona, get_persona, PERSONAS
from erirpg.workflow import Stage, STAGE_PERSONA


# ═══════════════════════════════════════════════════════════════════════════════
# TOKEN LIMITS (per user spec)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_INPUT_TOKENS = 8000   # What CRITIC actually sees
MAX_OUTPUT_TOKENS = 4000  # Output budget


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class ReviewItemType(Enum):
    """Types of review findings."""
    RISK = "RISK"          # Security, failure modes, edge cases
    CONTRACT = "CONTRACT"  # APIs, interfaces, expected behaviors
    DEBT = "DEBT"          # Technical debt, shortcuts, TODOs
    DECISION = "DECISION"  # Architecture choices, tradeoffs


@dataclass
class ReviewItem:
    """A single finding from CRITIC review."""
    type: ReviewItemType
    file: str
    line: Optional[int]
    description: str
    severity: str = "medium"  # high/medium/low
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "file": self.file,
            "line": self.line,
            "description": self.description,
            "severity": self.severity,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "ReviewItem":
        return cls(
            type=ReviewItemType(d["type"]),
            file=d["file"],
            line=d.get("line"),
            description=d["description"],
            severity=d.get("severity", "medium"),
        )
    
    def format_line(self) -> str:
        """Format as tagged line for output."""
        loc = f":{self.line}" if self.line else ""
        sev = f" ({self.severity})" if self.severity != "medium" else ""
        return f"[{self.type.value}] {self.file}{loc}{sev}: {self.description}"


@dataclass
class ReviewResult:
    """Complete review result for a path."""
    path: str
    hash: str
    items: List[ReviewItem] = field(default_factory=list)
    timestamp: str = ""
    tokens_used: int = 0
    skipped_unchanged: bool = False
    files_reviewed: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "hash": self.hash,
            "items": [item.to_dict() for item in self.items],
            "timestamp": self.timestamp,
            "tokens_used": self.tokens_used,
            "skipped_unchanged": self.skipped_unchanged,
            "files_reviewed": self.files_reviewed,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "ReviewResult":
        return cls(
            path=d["path"],
            hash=d["hash"],
            items=[ReviewItem.from_dict(i) for i in d.get("items", [])],
            timestamp=d.get("timestamp", ""),
            tokens_used=d.get("tokens_used", 0),
            skipped_unchanged=d.get("skipped_unchanged", False),
            files_reviewed=d.get("files_reviewed", []),
        )
    
    def to_markdown(self) -> str:
        """Format as structured markdown output."""
        lines = []
        
        # Header with CRITIC persona
        critic = PERSONAS[Persona.CRITIC]
        lines.append(f"# CRITIC Review: `{self.path}`")
        lines.append("")
        lines.append(f"**Persona**: {critic.identity}")
        lines.append(f"**Focus**: {critic.focus}")
        lines.append(f"**Timestamp**: {self.timestamp}")
        lines.append(f"**Tokens used**: {self.tokens_used}")
        lines.append("")
        
        if self.skipped_unchanged:
            lines.append("*Skipped - file unchanged since last review*")
            return "\n".join(lines)
        
        if not self.items:
            lines.append("✓ No issues found. **Health: A**")
            return "\n".join(lines)
        
        # Calculate health score
        from erirpg.review import calculate_health_score
        score, grade = calculate_health_score(self.items)
        
        # Health score header
        grade_emoji = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⛔"}.get(grade, "")
        lines.append(f"**Health**: {grade_emoji} **{grade}** (score: {score})")
        lines.append("")
        
        # Group by type
        by_type: Dict[ReviewItemType, List[ReviewItem]] = {}
        for item in self.items:
            by_type.setdefault(item.type, []).append(item)
        
        # Output each type
        type_order = [ReviewItemType.RISK, ReviewItemType.CONTRACT, 
                      ReviewItemType.DEBT, ReviewItemType.DECISION]
        
        for item_type in type_order:
            items = by_type.get(item_type, [])
            if items:
                lines.append(f"## [{item_type.value}] ({len(items)})")
                lines.append("")
                for item in items:
                    sev = f" **{item.severity.upper()}**" if item.severity == "high" else ""
                    loc = f":{item.line}" if item.line else ""
                    lines.append(f"- `{item.file}{loc}`{sev}: {item.description}")
                lines.append("")
        
        # Summary
        lines.append("---")
        lines.append(f"**Total**: {len(self.items)} items across {len(self.files_reviewed)} file(s)")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# HASHING & CACHING
# ═══════════════════════════════════════════════════════════════════════════════

def compute_file_hash(path: str) -> str:
    """Compute SHA256 hash of file contents."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ""


def compute_path_hash(paths: List[str]) -> str:
    """Compute combined hash for multiple files."""
    combined = ""
    for p in sorted(paths):
        combined += compute_file_hash(p)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def get_reviews_dir(project_path: str = ".") -> str:
    """Get path to reviews directory.
    
    If .eri-rpg exists in project_path, use it.
    Otherwise, fall back to /tmp/eri-rpg/reviews to avoid polluting non-projects.
    """
    local_dir = os.path.join(project_path, ".eri-rpg")
    # If the user explicitly has a .eri-rpg folder, use it
    if os.path.isdir(local_dir):
        return os.path.join(local_dir, "reviews")
    
    # Otherwise fallback to temp to avoid creating .eri-rpg in random dirs
    return os.path.join("/tmp", "eri-rpg", "reviews")


def load_cached_review(path: str, current_hash: str, project_path: str = ".") -> Optional[ReviewResult]:
    """Load cached review if hash matches."""
    reviews_dir = get_reviews_dir(project_path)
    if not os.path.exists(reviews_dir):
        return None
    
    # Find most recent review for this path
    for filename in sorted(os.listdir(reviews_dir), reverse=True):
        if not filename.endswith(".json"):
            continue
        
        filepath = os.path.join(reviews_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
                if data.get("path") == path and data.get("hash") == current_hash:
                    return ReviewResult.from_dict(data)
        except Exception:
            continue
    
    return None


def save_review(result: ReviewResult, project_path: str = ".") -> str:
    """Save review result to .eri-rpg/reviews/."""
    reviews_dir = get_reviews_dir(project_path)
    Path(reviews_dir).mkdir(parents=True, exist_ok=True)
    
    # Timestamp-based filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_path = result.path.replace("/", "_").replace("\\", "_")
    filename = f"{ts}_{safe_path[:30]}.json"
    
    filepath = os.path.join(reviews_dir, filename)
    with open(filepath, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    
    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY & READING
# ═══════════════════════════════════════════════════════════════════════════════

def expand_path(path: str) -> List[str]:
    """Expand path to list of files (handles file, directory, or glob)."""
    path = os.path.expanduser(path)
    
    # Glob pattern
    if "*" in path or "?" in path:
        return sorted(glob.glob(path, recursive=True))
    
    # Single file
    if os.path.isfile(path):
        return [path]
    
    # Directory - find code files
    if os.path.isdir(path):
        files = []
        code_extensions = {".py", ".rs", ".go", ".js", ".ts", ".c", ".cpp", ".h", ".java", ".rb"}
        for root, _, filenames in os.walk(path):
            # Skip hidden and common non-code dirs
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", "venv", ".venv") 
                   for p in root.split(os.sep)):
                continue
            for fn in filenames:
                if Path(fn).suffix.lower() in code_extensions:
                    files.append(os.path.join(root, fn))
        return sorted(files)
    
    return []


def read_file_content(path: str, use_full: bool = False) -> str:
    """Read file content, optionally using learnings instead of raw source."""
    # For now, always read raw source
    # TODO: Integrate with memory system for learnings
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading file: {e}]"


# ═══════════════════════════════════════════════════════════════════════════════
# AST-BASED ANALYSIS (stdlib ast only)
# ═══════════════════════════════════════════════════════════════════════════════

import ast
from typing import Set, Tuple


# Severity scores for health calculation
SEVERITY_SCORES = {"high": 3, "medium": 2, "low": 1}


class ComplexityVisitor(ast.NodeVisitor):
    """Calculate cyclomatic complexity of a function."""
    
    def __init__(self):
        self.complexity = 1  # Base complexity
    
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_comprehension(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        # and/or add branches
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
    
    def visit_IfExp(self, node):
        # Ternary operator
        self.complexity += 1
        self.generic_visit(node)


def calculate_complexity(func_node: ast.FunctionDef) -> int:
    """Calculate cyclomatic complexity of a function."""
    visitor = ComplexityVisitor()
    visitor.visit(func_node)
    return visitor.complexity


def get_function_lines(func_node: ast.FunctionDef) -> int:
    """Get the number of lines in a function."""
    if hasattr(func_node, 'end_lineno') and func_node.end_lineno:
        return func_node.end_lineno - func_node.lineno + 1
    # Fallback: count body nodes (rough estimate)
    return len(func_node.body) * 3


def get_function_name(node: ast.FunctionDef, parents: List[str] = None) -> str:
    """Get fully qualified function name."""
    if parents:
        return ".".join(parents + [node.name])
    return node.name


def find_used_names(node: ast.AST) -> Set[str]:
    """Find all Name nodes used in an AST subtree."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names


def analyze_function_returns(func_node: ast.FunctionDef) -> Tuple[bool, bool]:
    """Check if function has mixed return patterns.
    
    Returns: (has_value_return, has_bare_return)
    """
    has_value_return = False
    has_bare_return = False
    
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return):
            if node.value is None:
                has_bare_return = True
            elif isinstance(node.value, ast.Constant) and node.value.value is None:
                has_bare_return = True
            else:
                has_value_return = True
    
    return has_value_return, has_bare_return


def extract_ast_items(file_path: str, content: str) -> List[ReviewItem]:
    """
    AST-based extraction of review items.
    
    Detects:
    - Cyclomatic complexity >10 → [RISK]
    - Functions >50 lines → [DEBT]
    - Classes with no __init__ validation → [CONTRACT]
    - Mutable module-level containers → [RISK]
    - Bare return None with other returns → [RISK]
    - Nested functions >2 levels → [DEBT]
    - Star imports → [DEBT]
    - Unused parameters → [DEBT]
    """
    items = []
    
    # Only process Python files
    if not file_path.endswith('.py'):
        return items
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        items.append(ReviewItem(
            type=ReviewItemType.RISK,
            file=file_path,
            line=e.lineno,
            description=f"Syntax error: {e.msg}",
            severity="high",
        ))
        return items
    
    # Track nesting for functions
    def analyze_node(node: ast.AST, depth: int = 0, parents: List[str] = None):
        """Recursively analyze AST nodes."""
        if parents is None:
            parents = []
        
        # Star imports → [DEBT]
        if isinstance(node, ast.ImportFrom) and node.names:
            for alias in node.names:
                if alias.name == '*':
                    items.append(ReviewItem(
                        type=ReviewItemType.DEBT,
                        file=file_path,
                        line=node.lineno,
                        description=f"Star import: from {node.module} import *",
                        severity="medium",
                    ))
        
        # Mutable module-level containers → [RISK]
        if isinstance(node, ast.Assign) and depth == 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if assigned value is mutable container
                    if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                        items.append(ReviewItem(
                            type=ReviewItemType.RISK,
                            file=file_path,
                            line=node.lineno,
                            description=f"Mutable module-level container: {target.id} - shared state risk",
                            severity="medium",
                        ))
        
        # Function analysis
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = get_function_name(node, parents if parents else None)
            
            # Cyclomatic complexity >10 → [RISK]
            complexity = calculate_complexity(node)
            if complexity > 10:
                severity = "high" if complexity > 20 else "medium"
                items.append(ReviewItem(
                    type=ReviewItemType.RISK,
                    file=file_path,
                    line=node.lineno,
                    description=f"High complexity ({complexity}): {func_name}",
                    severity=severity,
                ))
            
            # Functions >50 lines → [DEBT]
            num_lines = get_function_lines(node)
            if num_lines > 50:
                severity = "medium" if num_lines > 100 else "low"
                items.append(ReviewItem(
                    type=ReviewItemType.DEBT,
                    file=file_path,
                    line=node.lineno,
                    description=f"Long function ({num_lines} lines): {func_name}",
                    severity=severity,
                ))
            
            # Nested functions >2 levels → [DEBT]
            if depth > 2:
                items.append(ReviewItem(
                    type=ReviewItemType.DEBT,
                    file=file_path,
                    line=node.lineno,
                    description=f"Deeply nested function (depth {depth}): {func_name}",
                    severity="medium",
                ))
            
            # Bare return None with other returns → [RISK]
            has_value, has_bare = analyze_function_returns(node)
            if has_value and has_bare:
                items.append(ReviewItem(
                    type=ReviewItemType.RISK,
                    file=file_path,
                    line=node.lineno,
                    description=f"Mixed return patterns (value and None): {func_name}",
                    severity="low",
                ))
            
            # Unused parameters → [DEBT]
            param_names = set()
            for arg in node.args.args:
                if arg.arg != 'self' and arg.arg != 'cls':
                    param_names.add(arg.arg)
            for arg in node.args.kwonlyargs:
                param_names.add(arg.arg)
            if node.args.vararg:
                param_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                param_names.add(node.args.kwarg.arg)
            
            # Find used names in function body
            used_names = find_used_names(node)
            unused = param_names - used_names
            
            for param in unused:
                items.append(ReviewItem(
                    type=ReviewItemType.DEBT,
                    file=file_path,
                    line=node.lineno,
                    description=f"Unused parameter '{param}' in {func_name}",
                    severity="low",
                ))
            
            # Recurse into function body with incremented depth
            new_parents = parents + [node.name] if parents else [node.name]
            for child in ast.iter_child_nodes(node):
                analyze_node(child, depth + 1, new_parents)
            return  # Don't double-visit children
        
        # Class analysis
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            
            # Check for __init__ with validation
            has_init = False
            init_has_validation = False
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    has_init = True
                    # Check if __init__ has any validation (if/assert/raise)
                    for child in ast.walk(item):
                        if isinstance(child, (ast.If, ast.Assert, ast.Raise)):
                            init_has_validation = True
                            break
            
            if has_init and not init_has_validation:
                items.append(ReviewItem(
                    type=ReviewItemType.CONTRACT,
                    file=file_path,
                    line=node.lineno,
                    description=f"__init__ has no input validation: {class_name}",
                    severity="low",
                ))
            
            # Record class definition
            items.append(ReviewItem(
                type=ReviewItemType.CONTRACT,
                file=file_path,
                line=node.lineno,
                description=f"Class definition: {class_name}",
                severity="low",
            ))
            
            # Recurse into class body
            for child in node.body:
                analyze_node(child, depth, [class_name])
            return
        
        # Recurse into other nodes
        for child in ast.iter_child_nodes(node):
            analyze_node(child, depth, parents)
    
    # Start analysis from module level
    analyze_node(tree, depth=0)
    
    return items


def extract_string_items(file_path: str, content: str) -> List[ReviewItem]:
    """
    String-based extraction of review items (original logic).
    
    Detects:
    - TODO/FIXME/HACK markers → [DEBT]
    - eval/exec usage → [RISK]
    - pickle.load → [RISK]
    - Hardcoded passwords → [RISK]
    - Bare except → [RISK]
    - Assert in non-test → [RISK]
    - Configuration constants → [DECISION]
    """
    items = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        stripped = line.strip()
        
        if not stripped:
            continue
        
        # [DEBT] - TODO/FIXME/HACK markers
        if any(marker in line_lower for marker in ("todo", "fixme", "hack", "xxx", "workaround")):
            items.append(ReviewItem(
                type=ReviewItemType.DEBT,
                file=file_path,
                line=i,
                description=stripped[:200],
                severity="low",
            ))
        
        # [RISK] - Bare except
        if "except:" in line and "except Exception" not in line:
            items.append(ReviewItem(
                type=ReviewItemType.RISK,
                file=file_path,
                line=i,
                description="Bare except clause - catches all exceptions including KeyboardInterrupt",
                severity="medium",
            ))
        
        # [RISK] - eval/exec
        if "eval(" in line or "exec(" in line:
            items.append(ReviewItem(
                type=ReviewItemType.RISK,
                file=file_path,
                line=i,
                description="eval/exec usage - potential code injection risk",
                severity="high",
            ))
        
        # [RISK] - pickle
        if "pickle.load" in line_lower or "pickle.loads" in line_lower:
            items.append(ReviewItem(
                type=ReviewItemType.RISK,
                file=file_path,
                line=i,
                description="pickle.load - arbitrary code execution from untrusted data",
                severity="high",
            ))
        
        # [RISK] - passwords
        if "password" in line_lower and ("=" in line or ":" in line):
            if "password_hash" not in line_lower and "get_password" not in line_lower:
                items.append(ReviewItem(
                    type=ReviewItemType.RISK,
                    file=file_path,
                    line=i,
                    description="Possible hardcoded or logged password",
                    severity="high",
                ))
        
        # [RISK] - assert in non-test
        if stripped.startswith("assert ") and "/test" not in file_path and "test_" not in file_path:
            items.append(ReviewItem(
                type=ReviewItemType.RISK,
                file=file_path,
                line=i,
                description="Assert in non-test code - disabled with python -O",
                severity="low",
            ))
        
        # [DECISION] - Configuration constants
        if any(p in stripped for p in ("MAX_", "MIN_", "DEFAULT_", "TIMEOUT", "LIMIT")):
            if "=" in stripped and not stripped.startswith("#"):
                items.append(ReviewItem(
                    type=ReviewItemType.DECISION,
                    file=file_path,
                    line=i,
                    description=f"Configuration constant: {stripped[:80]}",
                    severity="low",
                ))
    
    return items


def extract_review_items(file_path: str, content: str) -> List[ReviewItem]:
    """
    Extract review items using both AST and string-based analysis.
    
    AST catches structural issues (complexity, nesting, unused params).
    String matching catches patterns (TODO, eval, passwords).
    """
    items = []
    
    # AST-based analysis (Python files only)
    if file_path.endswith('.py'):
        items.extend(extract_ast_items(file_path, content))
    
    # String-based analysis (all files)
    items.extend(extract_string_items(file_path, content))
    
    # Deduplicate by (type, file, line)
    seen = set()
    unique_items = []
    for item in items:
        key = (item.type, item.file, item.line, item.description[:50])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    return unique_items


def calculate_health_score(items: List[ReviewItem]) -> Tuple[int, str]:
    """
    Calculate health score from severity.
    
    Returns: (raw_score, grade)
    Grade: A (0-5), B (6-15), C (16-30), D (31-50), F (>50)
    """
    score = sum(SEVERITY_SCORES.get(item.severity, 1) for item in items)
    
    if score <= 5:
        grade = "A"
    elif score <= 15:
        grade = "B"
    elif score <= 30:
        grade = "C"
    elif score <= 50:
        grade = "D"
    else:
        grade = "F"
    
    return score, grade


# ═══════════════════════════════════════════════════════════════════════════════
# CLONE REVIEW MODE (enhanced with --focus support)
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import re

# Standard library modules (for categorization)
STDLIB_MODULES = {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'bisect', 'collections',
    'contextlib', 'copy', 'csv', 'dataclasses', 'datetime', 'decimal', 'difflib',
    'enum', 'errno', 'fnmatch', 'functools', 'gc', 'getpass', 'glob', 'gzip',
    'hashlib', 'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io',
    'itertools', 'json', 'logging', 'math', 'mimetypes', 'multiprocessing', 'os',
    'pathlib', 'pickle', 'platform', 'pprint', 'queue', 're', 'random', 'secrets',
    'shlex', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl', 'stat', 'statistics',
    'string', 'struct', 'subprocess', 'sys', 'tarfile', 'tempfile', 'textwrap',
    'threading', 'time', 'timeit', 'traceback', 'typing', 'unittest', 'urllib',
    'uuid', 'warnings', 'weakref', 'xml', 'zipfile', 'zlib', 'types', 'operator',
    'codecs', 'locale', 'calendar', 'numbers', 'fractions', 'cmath', 'keyword',
    'token', 'tokenize', 'symbol', 'parser', 'dis', 'pickletools', 'dbm', 'shelve',
    'marshal', 'atexit', 'tracemalloc', 'linecache', 'symtable', 'compileall',
    'concurrent', 'email', 'mailbox', 'mimetypes', 'binascii', 'quopri', 'uu',
    'bz2', 'lzma', 'zipimport', 'pkgutil', 'modulefinder', 'runpy', 'builtins',
}

# Framework patterns for coupling detection
FRAMEWORK_PATTERNS = {
    "torch": ("PyTorch", "high"),
    "tensorflow": ("TensorFlow", "high"),
    "keras": ("Keras", "high"),
    "jax": ("JAX", "high"),
    "diffusers": ("Diffusers", "high"),
    "transformers": ("HuggingFace Transformers", "medium"),
    "accelerate": ("HuggingFace Accelerate", "medium"),
    "flask": ("Flask", "medium"),
    "django": ("Django", "high"),
    "fastapi": ("FastAPI", "medium"),
    "click": ("Click CLI", "low"),
    "typer": ("Typer CLI", "low"),
    "pydantic": ("Pydantic", "low"),
    "sqlalchemy": ("SQLAlchemy", "medium"),
    "celery": ("Celery", "medium"),
    "redis": ("Redis", "medium"),
    "boto3": ("AWS SDK", "medium"),
    "google": ("Google Cloud", "medium"),
    "azure": ("Azure SDK", "medium"),
}

# Internal project patterns (customize per source project)
INTERNAL_PATTERNS = {'erirpg', 'eri', 'toolkit', 'eritrainer'}


def find_available_symbols(tree: ast.AST) -> List[str]:
    """Find all top-level symbols in an AST."""
    symbols = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.append(target.id)
    return symbols


def find_symbol_node(tree: ast.AST, symbol: str) -> Optional[ast.AST]:
    """Find a specific symbol node in the AST."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == symbol:
            return node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == symbol:
                    return node
    return None


def get_imports_for_node(tree: ast.AST, node: ast.AST) -> Set[str]:
    """Find which module names are used by a specific node."""
    # Get all names used in the node
    used_names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            used_names.add(child.id)
        elif isinstance(child, ast.Attribute):
            # Get root of attribute chain
            root = child
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used_names.add(root.id)
    
    # Find which imports provide these names
    needed_imports = set()
    for import_node in ast.walk(tree):
        if isinstance(import_node, ast.Import):
            for alias in import_node.names:
                name = alias.asname or alias.name.split('.')[0]
                if name in used_names:
                    needed_imports.add(alias.name)
        elif isinstance(import_node, ast.ImportFrom):
            for alias in import_node.names:
                name = alias.asname or alias.name
                if name in used_names:
                    module = import_node.module or ''
                    needed_imports.add(f"{module}.{alias.name}" if module else alias.name)
    
    return needed_imports


def format_function_signature(node: ast.FunctionDef) -> str:
    """Format a function signature with params and return type."""
    params = []
    for arg in node.args.args:
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        params.append(param)
    
    sig = f"def {node.name}({', '.join(params)})"
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def categorize_import(module: str, level: int = 0) -> str:
    """Categorize an import as stdlib/third-party/internal."""
    if level > 0:
        return "internal"
    
    root = module.split('.')[0] if module else ''
    
    if root in STDLIB_MODULES:
        return "stdlib"
    elif root in INTERNAL_PATTERNS:
        return "internal"
    else:
        return "third-party"


def extract_clone_items_v2(
    file_path: str, 
    content: str, 
    target_project: str = "",
    focus_symbol: str = "",
) -> Tuple[List[ReviewItem], Optional[str]]:
    """
    Enhanced clone review with --focus support.
    
    Returns: (items, error_message)
    """
    items = []
    lines = content.split("\n")
    
    if not file_path.endswith('.py'):
        return [ReviewItem(
            type=ReviewItemType.RISK,
            file=file_path,
            line=None,
            description="Clone review only supports Python files",
            severity="high",
        )], None
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [ReviewItem(
            type=ReviewItemType.RISK,
            file=file_path,
            line=e.lineno,
            description=f"Syntax error: {e.msg}",
            severity="high",
        )], None
    
    # Handle --focus symbol
    focus_node = None
    if focus_symbol:
        focus_node = find_symbol_node(tree, focus_symbol)
        if focus_node is None:
            available = find_available_symbols(tree)
            return [], f"Symbol '{focus_symbol}' not found. Available: {', '.join(available)}"
    
    # Analyze scope - either focused node or whole file
    scope_nodes = [focus_node] if focus_node else list(ast.iter_child_nodes(tree))
    scope_name = focus_symbol if focus_symbol else os.path.basename(file_path)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # [CONTRACT] - IMPORTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    stdlib_imports = []
    thirdparty_imports = []
    internal_imports = []
    framework_imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                root = module.split('.')[0]
                
                if root in FRAMEWORK_PATTERNS:
                    fw_name, severity = FRAMEWORK_PATTERNS[root]
                    framework_imports.append((node.lineno, module, fw_name, severity))
                elif root in STDLIB_MODULES:
                    stdlib_imports.append((node.lineno, module))
                elif root in INTERNAL_PATTERNS:
                    internal_imports.append((node.lineno, module, []))
                else:
                    thirdparty_imports.append((node.lineno, module))
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            root = module.split('.')[0] if module else ''
            names = [a.name for a in node.names]
            
            if node.level > 0:  # relative import
                internal_imports.append((node.lineno, f"{'.' * node.level}{module}", names))
            elif root in FRAMEWORK_PATTERNS:
                fw_name, severity = FRAMEWORK_PATTERNS[root]
                framework_imports.append((node.lineno, module, fw_name, severity))
            elif root in STDLIB_MODULES:
                stdlib_imports.append((node.lineno, module))
            elif root in INTERNAL_PATTERNS:
                internal_imports.append((node.lineno, module, names))
            else:
                thirdparty_imports.append((node.lineno, module))
    
    # Report framework coupling as RISK
    for lineno, module, fw_name, severity in framework_imports:
        items.append(ReviewItem(
            type=ReviewItemType.RISK,
            file=file_path,
            line=lineno,
            description=f"Framework: {fw_name} ({module}) - verify target has this",
            severity=severity,
        ))
    
    # Report internal dependencies as CONTRACT
    for lineno, module, names in internal_imports:
        name_str = f" import {', '.join(names[:3])}{'...' if len(names) > 3 else ''}" if names else ""
        items.append(ReviewItem(
            type=ReviewItemType.CONTRACT,
            file=file_path,
            line=lineno,
            description=f"Internal: from {module}{name_str} - map to target equivalent",
            severity="medium",
        ))
    
    # Report third-party as CONTRACT (need to verify exists in target)
    for lineno, module in thirdparty_imports:
        items.append(ReviewItem(
            type=ReviewItemType.CONTRACT,
            file=file_path,
            line=lineno,
            description=f"Third-party: {module} - ensure target has dependency",
            severity="low",
        ))
    
    # Stdlib is safe - no item needed
    
    # ═══════════════════════════════════════════════════════════════════════════
    # [CONTRACT] - FUNCTION SIGNATURES & CLASS INTERFACES
    # ═══════════════════════════════════════════════════════════════════════════
    
    for node in scope_nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                sig = format_function_signature(node)
                items.append(ReviewItem(
                    type=ReviewItemType.CONTRACT,
                    file=file_path,
                    line=node.lineno,
                    description=f"Export: {sig}",
                    severity="low",
                ))
        
        elif isinstance(node, ast.ClassDef):
            # Class definition
            bases = [ast.unparse(b) for b in node.bases] if node.bases else []
            base_str = f"({', '.join(bases)})" if bases else ""
            items.append(ReviewItem(
                type=ReviewItemType.CONTRACT,
                file=file_path,
                line=node.lineno,
                description=f"Class: {node.name}{base_str}",
                severity="low",
            ))
            
            # If inheriting from something, flag it
            for base in node.bases:
                base_name = ast.unparse(base)
                if '.' in base_name or base_name[0].isupper():
                    items.append(ReviewItem(
                        type=ReviewItemType.CONTRACT,
                        file=file_path,
                        line=node.lineno,
                        description=f"Inherits: {base_name} - find target equivalent",
                        severity="medium",
                    ))
            
            # Public methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not item.name.startswith('_') or item.name in ('__init__', '__call__'):
                        sig = format_function_signature(item)
                        items.append(ReviewItem(
                            type=ReviewItemType.CONTRACT,
                            file=file_path,
                            line=item.lineno,
                            description=f"Method: {node.name}.{sig[4:]}",  # strip 'def '
                            severity="low",
                        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # [RISK] - HARDCODED PATHS, GLOBAL STATE, MONKEY-PATCHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Hardcoded paths and URLs
    path_patterns = [
        (r'["\']/?(?:home|usr|var|etc|tmp|opt)/\w+', "Unix path"),
        (r'["\'][A-Z]:\\', "Windows path"),
        (r'[\"\']\.eri-rpg/', "project path"),
        (r'["\']localhost[:\d]*', "localhost"),
        (r'["\']127\.0\.0\.1', "localhost IP"),
        (r'https?://[^"\'\s]{10,}', "hardcoded URL"),
    ]
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        
        for pattern, desc in path_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                items.append(ReviewItem(
                    type=ReviewItemType.RISK,
                    file=file_path,
                    line=i,
                    description=f"Hardcoded {desc}: {stripped[:60]}",
                    severity="medium",
                ))
                break
    
    # Global/module state
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Mutable module-level state
                    if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                        if not target.id.isupper():  # Not a CONSTANT
                            items.append(ReviewItem(
                                type=ReviewItemType.RISK,
                                file=file_path,
                                line=node.lineno,
                                description=f"Mutable global: {target.id} - shared state risk",
                                severity="medium",
                            ))
    
    # Monkey-patching / dynamic attribute access
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in ('setattr', 'getattr', 'delattr'):
                    items.append(ReviewItem(
                        type=ReviewItemType.RISK,
                        file=file_path,
                        line=node.lineno,
                        description=f"Dynamic attribute: {func.id}() - may not work in target",
                        severity="medium",
                    ))
            elif isinstance(func, ast.Attribute):
                if func.attr == '__setattr__':
                    items.append(ReviewItem(
                        type=ReviewItemType.RISK,
                        file=file_path,
                        line=node.lineno,
                        description="Monkey-patching: __setattr__ - verify compatibility",
                        severity="high",
                    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # [DECISION] - CONSTANTS, DTYPE, DEVICE, BUFFER SIZES
    # ═══════════════════════════════════════════════════════════════════════════
    
    decision_patterns = [
        (r'torch\.(float16|float32|bfloat16|float64)', "dtype"),
        (r'torch\.device\s*\(', "device"),
        (r'\.to\s*\(\s*["\']cuda', "device"),
        (r'\.cuda\s*\(', "device"),
        (r'batch_size\s*=', "batch dimension"),
        (r'num_workers\s*=', "worker count"),
        (r'channels?\s*=\s*\d+', "channel count"),
    ]
    
    for i, line in enumerate(lines, 1):
        for pattern, desc in decision_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                stripped = line.strip()
                items.append(ReviewItem(
                    type=ReviewItemType.DECISION,
                    file=file_path,
                    line=i,
                    description=f"{desc.title()}: {stripped[:60]}",
                    severity="low",
                ))
                break
    
    # ALL_CAPS constants
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name.isupper() and len(name) > 2:
                        line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        items.append(ReviewItem(
                            type=ReviewItemType.DECISION,
                            file=file_path,
                            line=node.lineno,
                            description=f"Constant: {line.strip()[:70]}",
                            severity="low",
                        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SORT BY PRIORITY
    # ═══════════════════════════════════════════════════════════════════════════
    
    severity_order = {"high": 0, "medium": 1, "low": 2}
    type_order = {ReviewItemType.RISK: 0, ReviewItemType.CONTRACT: 1, ReviewItemType.DECISION: 2, ReviewItemType.DEBT: 3}
    items.sort(key=lambda x: (severity_order.get(x.severity, 2), type_order.get(x.type, 3)))
    
    return items, None


@dataclass
class CloneReviewResult:
    """Result of clone preparation review."""
    source_file: str
    target_project: str
    focus_symbol: str = ""
    items: List[ReviewItem] = field(default_factory=list)
    timestamp: str = ""
    error: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "target_project": self.target_project,
            "focus_symbol": self.focus_symbol,
            "items": [item.to_dict() for item in self.items],
            "timestamp": self.timestamp,
            "error": self.error,
        }
    
    def to_markdown(self) -> str:
        """Format as pre-clone checklist with priority sections."""
        lines = []
        
        # Header
        symbol_str = f" ({self.focus_symbol})" if self.focus_symbol else ""
        target_str = f" → {self.target_project}" if self.target_project else ""
        lines.append(f"# Clone Review: `{os.path.basename(self.source_file)}`{symbol_str}{target_str}")
        lines.append("")
        
        if self.error:
            lines.append(f"**Error**: {self.error}")
            return "\n".join(lines)
        
        lines.append(f"**Source**: {self.source_file}")
        if self.target_project:
            lines.append(f"**Target**: {self.target_project}")
        lines.append(f"**Timestamp**: {self.timestamp}")
        lines.append("")
        
        if not self.items:
            lines.append("✅ **No clone blockers.** Safe to port directly.")
            return "\n".join(lines)
        
        # Calculate health
        score, grade = calculate_health_score(self.items)
        grade_emoji = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⛔"}.get(grade, "")
        lines.append(f"**Clone Risk**: {grade_emoji} **{grade}** (score: {score})")
        lines.append("")
        
        # Group by severity first, then type
        high_items = [i for i in self.items if i.severity == "high"]
        medium_items = [i for i in self.items if i.severity == "medium"]
        low_items = [i for i in self.items if i.severity == "low"]
        
        if high_items:
            lines.append("## 🚨 Must resolve before cloning")
            lines.append("")
            for item in high_items:
                loc = f":{item.line}" if item.line else ""
                lines.append(f"- [{item.type.value}] {item.description}")
            lines.append("")
        
        if medium_items:
            lines.append("## ⚠️ Likely needs attention")
            lines.append("")
            for item in medium_items:
                loc = f":{item.line}" if item.line else ""
                lines.append(f"- [{item.type.value}] `L{item.line}` {item.description}" if item.line else f"- [{item.type.value}] {item.description}")
            lines.append("")
        
        if low_items:
            lines.append("## ✅ Safe to port (verify only)")
            lines.append("")
            for item in low_items[:10]:  # Limit to 10 for readability
                lines.append(f"- [{item.type.value}] {item.description}")
            if len(low_items) > 10:
                lines.append(f"- ... and {len(low_items) - 10} more")
            lines.append("")
        
        # Summary
        lines.append("---")
        by_type = {}
        for item in self.items:
            by_type[item.type.value] = by_type.get(item.type.value, 0) + 1
        type_summary = ", ".join(f"{v} {k}" for k, v in sorted(by_type.items()))
        lines.append(f"**Total**: {len(self.items)} items ({type_summary})")
        
        return "\n".join(lines)


def review_for_clone(
    source_file: str,
    target_project: str = "",
    focus_symbol: str = "",
    project_path: str = ".",
) -> CloneReviewResult:
    """
    Review a single file for cloning to another project.
    
    Args:
        source_file: File to clone
        target_project: Name of target project (for context)
        focus_symbol: If provided, only analyze this symbol
        project_path: Project root
    
    Returns:
        CloneReviewResult with pre-clone checklist
    """
    # Resolve path
    source_path = os.path.join(project_path, source_file) if not os.path.isabs(source_file) else source_file
    
    if not os.path.isfile(source_path):
        return CloneReviewResult(
            source_file=source_file,
            target_project=target_project,
            focus_symbol=focus_symbol,
            error=f"File not found: {source_path}",
        )
    
    # Read content
    try:
        with open(source_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return CloneReviewResult(
            source_file=source_file,
            target_project=target_project,
            focus_symbol=focus_symbol,
            error=f"Cannot read file: {e}",
        )
    
    # Extract clone-relevant items
    items, error = extract_clone_items_v2(source_file, content, target_project, focus_symbol)
    
    if error:
        return CloneReviewResult(
            source_file=source_file,
            target_project=target_project,
            focus_symbol=focus_symbol,
            error=error,
        )
    
    # Save result
    result = CloneReviewResult(
        source_file=source_file,
        target_project=target_project,
        focus_symbol=focus_symbol,
        items=items,
    )
    
    # Save to file
    reviews_dir = get_reviews_dir(project_path)
    Path(reviews_dir).mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_source = os.path.basename(source_file).replace('.', '_')
    safe_target = target_project.replace('/', '_').replace('\\', '_') if target_project else "unknown"
    filename = f"clone-{safe_source}-to-{safe_target}-{ts}.json"
    
    filepath = os.path.join(reviews_dir, filename)
    with open(filepath, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    
    return result


def review_file(file_path: str, content: str, budget: int) -> List[ReviewItem]:
    """Review a single file within token budget."""
    # Truncate if over budget
    truncated, tokens, was_truncated = truncate_code(content, budget, file_path)
    
    # Extract items from (possibly truncated) content
    items = extract_review_items(file_path, truncated)
    
    # Add truncation warning if applicable
    if was_truncated:
        items.insert(0, ReviewItem(
            type=ReviewItemType.DEBT,
            file=file_path,
            line=None,
            description=f"File truncated to {budget} tokens - some issues may be missed",
            severity="low",
        ))
    
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def review_path(
    path: str,
    use_full: bool = False,
    skip_cache: bool = False,
    project_path: str = ".",
) -> ReviewResult:
    """
    Review a path with CRITIC persona.
    
    Args:
        path: File, directory, or glob pattern
        use_full: If True, use raw source; else use learnings when available
        skip_cache: If True, force re-review even if unchanged
        project_path: Project root for .eri-rpg/reviews/
    
    Returns:
        ReviewResult with structured items
    """
    # Expand to file list
    files = expand_path(path)
    
    if not files:
        return ReviewResult(
            path=path,
            hash="",
            items=[ReviewItem(
                type=ReviewItemType.RISK,
                file=path,
                line=None,
                description=f"Path not found or no code files: {path}",
                severity="high",
            )],
        )
    
    # Compute hash for cache check
    current_hash = compute_path_hash(files)
    
    # Check cache
    if not skip_cache:
        cached = load_cached_review(path, current_hash, project_path)
        if cached:
            cached.skipped_unchanged = True
            return cached
    
    # Calculate per-file budget
    total_budget = MAX_INPUT_TOKENS
    per_file_budget = max(500, total_budget // len(files))
    
    # Review each file
    all_items: List[ReviewItem] = []
    tokens_used = 0
    
    for file_path in files:
        content = read_file_content(file_path, use_full)
        file_tokens = count_tokens(content)
        
        # Apply budget
        file_budget = min(per_file_budget, total_budget - tokens_used)
        if file_budget < 100:
            # Out of budget - note and skip
            all_items.append(ReviewItem(
                type=ReviewItemType.DEBT,
                file=file_path,
                line=None,
                description="Skipped - token budget exhausted",
                severity="low",
            ))
            continue
        
        items = review_file(file_path, content, file_budget)
        all_items.extend(items)
        tokens_used += min(file_tokens, file_budget)
    
    # Build result
    result = ReviewResult(
        path=path,
        hash=current_hash,
        items=all_items,
        tokens_used=tokens_used,
        files_reviewed=files,
    )
    
    # Save to cache
    save_review(result, project_path)
    
    return result
