"""
File Parity Tracker - Track which files exist in source vs target.

Provides accurate file-level tracking between source and cloned projects,
replacing the module-only tracking that led to 57 -> 5 file loss.
"""

from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import json


@dataclass
class FileParityReport:
    """Report of file parity between source and target."""
    source_files: Set[str]
    target_files: Set[str]
    matched: Set[str]
    missing_in_target: Set[str]
    extra_in_target: Set[str]
    parity_score: float
    
    def to_dict(self) -> dict:
        return {
            "source_count": len(self.source_files),
            "target_count": len(self.target_files),
            "matched_count": len(self.matched),
            "missing_count": len(self.missing_in_target),
            "extra_count": len(self.extra_in_target),
            "missing_files": sorted(self.missing_in_target)[:20],  # Limit for readability
            "missing_files_truncated": len(self.missing_in_target) > 20,
            "extra_files": sorted(self.extra_in_target)[:20],
            "extra_files_truncated": len(self.extra_in_target) > 20,
            "parity_score": round(self.parity_score, 3)
        }
    
    def __str__(self) -> str:
        return (
            f"Parity: {self.parity_score:.1%} "
            f"({len(self.matched)}/{len(self.source_files)} files matched, "
            f"{len(self.missing_in_target)} missing)"
        )


DEFAULT_SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules",
    ".eggs", ".tox", ".pytest_cache", ".mypy_cache", 
    ".ruff_cache", "htmlcov", "coverage", "build", "dist",
    ".egg-info", "site-packages"
}


def get_python_files(
    path: Path, 
    skip_dirs: Optional[Set[str]] = None,
    extensions: Optional[Set[str]] = None
) -> Set[str]:
    """Get all Python files in a directory.
    
    Args:
        path: Directory to scan
        skip_dirs: Directories to skip (defaults to common cache/build dirs)
        extensions: File extensions to include (defaults to .py only)
    
    Returns:
        Set of relative file paths
    """
    if skip_dirs is None:
        skip_dirs = DEFAULT_SKIP_DIRS
    
    if extensions is None:
        extensions = {".py"}
    
    if not path.exists():
        return set()
    
    if path.is_file():
        return {path.name}
    
    files = set()
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        
        if file_path.suffix not in extensions:
            continue
        
        rel_path = file_path.relative_to(path)
        
        # Skip excluded directories
        if any(skip in rel_path.parts for skip in skip_dirs):
            continue
        
        files.add(str(rel_path))
    
    return files


def compute_file_parity(
    source_path: Path,
    target_path: Path,
    module_name: Optional[str] = None,
    skip_dirs: Optional[Set[str]] = None
) -> FileParityReport:
    """Compute file parity between source and target.
    
    Args:
        source_path: Path to source project root
        target_path: Path to target project root
        module_name: Optional subdirectory to compare (e.g., "toolkit")
        skip_dirs: Directories to skip
    
    Returns:
        FileParityReport with detailed comparison
    """
    # If module_name specified, look in that subdirectory
    if module_name:
        source_dir = source_path / module_name
        target_dir = target_path / module_name
    else:
        source_dir = source_path
        target_dir = target_path
    
    source_files = get_python_files(source_dir, skip_dirs)
    target_files = get_python_files(target_dir, skip_dirs)
    
    matched = source_files & target_files
    missing = source_files - target_files
    extra = target_files - source_files
    
    parity = len(matched) / len(source_files) if source_files else 1.0
    
    return FileParityReport(
        source_files=source_files,
        target_files=target_files,
        matched=matched,
        missing_in_target=missing,
        extra_in_target=extra,
        parity_score=parity
    )


def compute_project_parity(
    source_path: Path,
    target_path: Path,
    modules: Optional[List[str]] = None,
    skip_dirs: Optional[Set[str]] = None
) -> Dict[str, FileParityReport]:
    """Compute file parity for multiple modules.
    
    Args:
        source_path: Path to source project root
        target_path: Path to target project root
        modules: List of module names to compare (None = entire project)
        skip_dirs: Directories to skip
    
    Returns:
        Dict mapping module names to their parity reports
    """
    if modules is None:
        # Compare entire project
        return {"project": compute_file_parity(source_path, target_path, None, skip_dirs)}
    
    reports = {}
    for module in modules:
        reports[module] = compute_file_parity(source_path, target_path, module, skip_dirs)
    
    return reports


def generate_parity_summary(reports: Dict[str, FileParityReport]) -> dict:
    """Generate summary statistics from multiple parity reports."""
    total_source = sum(len(r.source_files) for r in reports.values())
    total_target = sum(len(r.target_files) for r in reports.values())
    total_matched = sum(len(r.matched) for r in reports.values())
    total_missing = sum(len(r.missing_in_target) for r in reports.values())
    
    overall_parity = total_matched / total_source if total_source > 0 else 1.0
    
    # Find modules with worst parity
    worst_modules = sorted(
        [(name, r.parity_score) for name, r in reports.items()],
        key=lambda x: x[1]
    )[:5]
    
    return {
        "total_source_files": total_source,
        "total_target_files": total_target,
        "total_matched": total_matched,
        "total_missing": total_missing,
        "overall_parity": round(overall_parity, 3),
        "overall_parity_pct": f"{overall_parity:.1%}",
        "modules_compared": len(reports),
        "worst_modules": [
            {"module": name, "parity": f"{score:.1%}"}
            for name, score in worst_modules
        ]
    }


def save_parity_state(reports: Dict[str, FileParityReport], state_file: Path) -> None:
    """Save parity state for tracking progress."""
    state = {
        module: report.to_dict()
        for module, report in reports.items()
    }
    state["_summary"] = generate_parity_summary(reports)
    state_file.write_text(json.dumps(state, indent=2))


def load_parity_state(state_file: Path) -> dict:
    """Load parity state."""
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def format_parity_table(reports: Dict[str, FileParityReport]) -> str:
    """Format parity reports as a markdown table."""
    lines = [
        "| Module | Source | Target | Matched | Missing | Parity |",
        "|--------|--------|--------|---------|---------|--------|"
    ]
    
    for module, report in sorted(reports.items()):
        parity_str = f"{report.parity_score:.1%}"
        status = "✅" if report.parity_score >= 0.9 else "⚠️" if report.parity_score >= 0.5 else "❌"
        lines.append(
            f"| {module} | {len(report.source_files)} | {len(report.target_files)} | "
            f"{len(report.matched)} | {len(report.missing_in_target)} | {status} {parity_str} |"
        )
    
    # Add summary row
    summary = generate_parity_summary(reports)
    lines.append(
        f"| **TOTAL** | **{summary['total_source_files']}** | "
        f"**{summary['total_target_files']}** | **{summary['total_matched']}** | "
        f"**{summary['total_missing']}** | **{summary['overall_parity_pct']}** |"
    )
    
    return "\n".join(lines)
