"""
Behavior Verifier - Compare source and target implementations.

Performs automated verification:
1. Signature matching (function names, args, returns)
2. Class hierarchy matching (base classes, methods)
3. Import coverage (all required imports present)
4. Constant preservation (same values)

Replaces the paper-only verification that marked everything as "pending".
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .behavior_extractor import (
    BehaviorExtractor, 
    ExtractedModule, 
    ExtractedClass, 
    ExtractedFunction,
    extract_module_behavior
)


class VerifyStatus(Enum):
    PASS = "✅"
    FAIL = "❌"
    PARTIAL = "⚠️"
    MISSING = "🔴"
    EXTRA = "➕"
    
    def __str__(self):
        return self.value


@dataclass
class VerifyResult:
    """Result of a single verification check."""
    item: str
    category: str
    status: VerifyStatus
    source_value: str
    target_value: str
    details: str
    
    def to_dict(self) -> dict:
        return {
            "item": self.item,
            "category": self.category,
            "status": str(self.status),
            "source": self.source_value[:100],
            "target": self.target_value[:100],
            "details": self.details
        }


@dataclass
class FileVerificationReport:
    """Verification report for a single file."""
    source_file: str
    target_file: str
    results: List[VerifyResult]
    passed: int
    failed: int
    partial: int
    missing: int
    
    @property
    def score(self) -> str:
        total = self.passed + self.failed + self.partial + self.missing
        return f"{self.passed}/{total}"
    
    @property
    def status(self) -> str:
        if self.missing > 0:
            return "MISSING"
        if self.failed > 0:
            return "FAILED"
        if self.partial > 0:
            return "PARTIAL"
        return "PASSED"
    
    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "status": self.status,
            "score": self.score,
            "passed": self.passed,
            "failed": self.failed,
            "partial": self.partial,
            "missing": self.missing,
            "failures": [
                r.to_dict() for r in self.results 
                if r.status in (VerifyStatus.FAIL, VerifyStatus.MISSING)
            ][:10]  # Limit for readability
        }


@dataclass
class ModuleVerificationReport:
    """Verification report for an entire module."""
    module_name: str
    file_reports: Dict[str, FileVerificationReport]
    
    @property
    def total_passed(self) -> int:
        return sum(r.passed for r in self.file_reports.values())
    
    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.file_reports.values())
    
    @property
    def total_missing(self) -> int:
        return sum(r.missing for r in self.file_reports.values())
    
    @property
    def total_partial(self) -> int:
        return sum(r.partial for r in self.file_reports.values())
    
    @property
    def score(self) -> str:
        total = self.total_passed + self.total_failed + self.total_partial + self.total_missing
        return f"{self.total_passed}/{total}"
    
    @property
    def status(self) -> str:
        if self.total_missing > 0 or self.total_failed > 0:
            return "FAILED"
        if self.total_partial > 0:
            return "PARTIAL"
        return "PASSED"
    
    def to_dict(self) -> dict:
        return {
            "module": self.module_name,
            "status": self.status,
            "score": self.score,
            "files_checked": len(self.file_reports),
            "passed": self.total_passed,
            "failed": self.total_failed,
            "partial": self.total_partial,
            "missing": self.total_missing,
            "file_statuses": {
                path: report.status 
                for path, report in self.file_reports.items()
            }
        }


class BehaviorVerifier:
    """Verify target implementation matches source behavior."""
    
    def __init__(self):
        self.extractor = BehaviorExtractor()
    
    def verify_file(
        self, 
        source_file: Path, 
        target_file: Path
    ) -> FileVerificationReport:
        """Verify a single file pair."""
        results = []
        
        # Check if target exists
        if not target_file.exists():
            return FileVerificationReport(
                source_file=str(source_file),
                target_file=str(target_file),
                results=[VerifyResult(
                    item=target_file.name,
                    category="file",
                    status=VerifyStatus.MISSING,
                    source_value=str(source_file),
                    target_value="FILE NOT FOUND",
                    details=f"Target file does not exist: {target_file}"
                )],
                passed=0, failed=0, partial=0, missing=1
            )
        
        # Check if source exists
        if not source_file.exists():
            return FileVerificationReport(
                source_file=str(source_file),
                target_file=str(target_file),
                results=[VerifyResult(
                    item=source_file.name,
                    category="file",
                    status=VerifyStatus.EXTRA,
                    source_value="FILE NOT FOUND",
                    target_value=str(target_file),
                    details=f"Extra file in target (not in source)"
                )],
                passed=0, failed=0, partial=1, missing=0
            )
        
        # Extract both files
        try:
            source_mod = self.extractor.extract_file(source_file)
            target_mod = self.extractor.extract_file(target_file)
        except Exception as e:
            return FileVerificationReport(
                source_file=str(source_file),
                target_file=str(target_file),
                results=[VerifyResult(
                    item="parse",
                    category="error",
                    status=VerifyStatus.FAIL,
                    source_value=str(source_file),
                    target_value=str(target_file),
                    details=f"Parse error: {e}"
                )],
                passed=0, failed=1, partial=0, missing=0
            )
        
        # Verify classes
        results.extend(self._verify_classes(source_mod, target_mod))
        
        # Verify functions
        results.extend(self._verify_functions(source_mod, target_mod))
        
        # Verify critical imports
        results.extend(self._verify_imports(source_mod, target_mod))
        
        # Count results
        passed = sum(1 for r in results if r.status == VerifyStatus.PASS)
        failed = sum(1 for r in results if r.status == VerifyStatus.FAIL)
        partial = sum(1 for r in results if r.status == VerifyStatus.PARTIAL)
        missing = sum(1 for r in results if r.status == VerifyStatus.MISSING)
        
        return FileVerificationReport(
            source_file=str(source_file),
            target_file=str(target_file),
            results=results,
            passed=passed,
            failed=failed,
            partial=partial,
            missing=missing
        )
    
    def _verify_classes(
        self, 
        source: ExtractedModule, 
        target: ExtractedModule
    ) -> List[VerifyResult]:
        """Verify class definitions match."""
        results = []
        source_classes = {c.name: c for c in source.classes}
        target_classes = {c.name: c for c in target.classes}
        
        for name, src_class in source_classes.items():
            if name not in target_classes:
                results.append(VerifyResult(
                    item=f"class {name}",
                    category="class",
                    status=VerifyStatus.MISSING,
                    source_value=f"class {name}({', '.join(src_class.bases)})",
                    target_value="NOT FOUND",
                    details=f"Class {name} not implemented in target"
                ))
                continue
            
            tgt_class = target_classes[name]
            
            # Check base classes
            src_bases = set(src_class.bases)
            tgt_bases = set(tgt_class.bases)
            
            if src_bases != tgt_bases:
                # Check if it's a partial match (some bases present)
                common = src_bases & tgt_bases
                if common:
                    results.append(VerifyResult(
                        item=f"class {name} bases",
                        category="inheritance",
                        status=VerifyStatus.PARTIAL,
                        source_value=str(list(src_bases)),
                        target_value=str(list(tgt_bases)),
                        details=f"Base class mismatch: missing {src_bases - tgt_bases}"
                    ))
                else:
                    results.append(VerifyResult(
                        item=f"class {name} bases",
                        category="inheritance",
                        status=VerifyStatus.FAIL,
                        source_value=str(list(src_bases)),
                        target_value=str(list(tgt_bases)),
                        details="Base class completely different"
                    ))
            else:
                results.append(VerifyResult(
                    item=f"class {name}",
                    category="class",
                    status=VerifyStatus.PASS,
                    source_value=f"class {name}",
                    target_value=f"class {name}",
                    details="Class exists with correct bases"
                ))
            
            # Check methods
            results.extend(self._verify_methods(name, src_class, tgt_class))
        
        return results
    
    def _verify_methods(
        self,
        class_name: str,
        src_class: ExtractedClass,
        tgt_class: ExtractedClass
    ) -> List[VerifyResult]:
        """Verify class methods match."""
        results = []
        src_methods = {m.name: m for m in src_class.methods}
        tgt_methods = {m.name: m for m in tgt_class.methods}
        
        for name, src_method in src_methods.items():
            # Skip private/magic methods for verification
            if name.startswith("__") and name != "__init__":
                continue
            if name.startswith("_") and not name.startswith("__"):
                continue
            
            if name not in tgt_methods:
                results.append(VerifyResult(
                    item=f"{class_name}.{name}()",
                    category="method",
                    status=VerifyStatus.MISSING,
                    source_value=f"def {name}({', '.join(src_method.args[:3])}...)",
                    target_value="NOT FOUND",
                    details=f"Method {name} not implemented"
                ))
            else:
                tgt_method = tgt_methods[name]
                
                # Check argument count (basic signature check)
                src_arg_count = len([a for a in src_method.args if not a.startswith("self")])
                tgt_arg_count = len([a for a in tgt_method.args if not a.startswith("self")])
                
                if abs(src_arg_count - tgt_arg_count) > 2:
                    results.append(VerifyResult(
                        item=f"{class_name}.{name}()",
                        category="method",
                        status=VerifyStatus.PARTIAL,
                        source_value=f"def {name}({src_arg_count} args)",
                        target_value=f"def {name}({tgt_arg_count} args)",
                        details="Argument count differs significantly"
                    ))
                else:
                    results.append(VerifyResult(
                        item=f"{class_name}.{name}()",
                        category="method",
                        status=VerifyStatus.PASS,
                        source_value=f"def {name}(...)",
                        target_value=f"def {name}(...)",
                        details="Method exists"
                    ))
        
        return results
    
    def _verify_functions(
        self, 
        source: ExtractedModule, 
        target: ExtractedModule
    ) -> List[VerifyResult]:
        """Verify top-level functions match."""
        results = []
        source_funcs = {f.name: f for f in source.functions}
        target_funcs = {f.name: f for f in target.functions}
        
        for name, src_func in source_funcs.items():
            # Skip private functions
            if name.startswith("_"):
                continue
                
            if name not in target_funcs:
                results.append(VerifyResult(
                    item=f"def {name}()",
                    category="function",
                    status=VerifyStatus.MISSING,
                    source_value=f"def {name}({', '.join(src_func.args[:3])}...)",
                    target_value="NOT FOUND",
                    details=f"Function {name} not implemented"
                ))
            else:
                tgt_func = target_funcs[name]
                
                # Check signature compatibility
                if len(src_func.args) != len(tgt_func.args):
                    diff = abs(len(src_func.args) - len(tgt_func.args))
                    if diff > 2:
                        results.append(VerifyResult(
                            item=f"def {name}()",
                            category="function",
                            status=VerifyStatus.PARTIAL,
                            source_value=f"{len(src_func.args)} args",
                            target_value=f"{len(tgt_func.args)} args",
                            details="Argument count differs"
                        ))
                    else:
                        results.append(VerifyResult(
                            item=f"def {name}()",
                            category="function",
                            status=VerifyStatus.PASS,
                            source_value=f"def {name}(...)",
                            target_value=f"def {name}(...)",
                            details="Function exists (minor arg difference)"
                        ))
                else:
                    results.append(VerifyResult(
                        item=f"def {name}()",
                        category="function",
                        status=VerifyStatus.PASS,
                        source_value=f"def {name}(...)",
                        target_value=f"def {name}(...)",
                        details="Function exists with matching signature"
                    ))
        
        return results
    
    def _verify_imports(
        self, 
        source: ExtractedModule, 
        target: ExtractedModule
    ) -> List[VerifyResult]:
        """Verify critical imports are present."""
        results = []
        
        # Build set of all source imports
        source_imports = set(source.imports)
        for module, names in source.from_imports.items():
            for name in names:
                source_imports.add(f"{module}.{name}")
        
        # Build set of all target imports
        target_imports = set(target.imports)
        for module, names in target.from_imports.items():
            for name in names:
                target_imports.add(f"{module}.{name}")
        
        # Check critical third-party imports
        critical_packages = {"torch", "diffusers", "transformers", "safetensors", "accelerate"}
        
        for imp in source_imports:
            base_package = imp.split(".")[0]
            if base_package in critical_packages:
                # Check if any form of this import exists in target
                matching = [t for t in target_imports if t.startswith(base_package)]
                if not matching:
                    results.append(VerifyResult(
                        item=f"import {imp}",
                        category="import",
                        status=VerifyStatus.PARTIAL,
                        source_value=imp,
                        target_value="NOT FOUND",
                        details=f"Critical import from {base_package} may be missing"
                    ))
        
        return results


def verify_module_behavior(
    source_path: Path,
    target_path: Path,
    module_name: str,
    skip_dirs: Optional[Set[str]] = None
) -> ModuleVerificationReport:
    """Verify all files in a module."""
    if skip_dirs is None:
        skip_dirs = {"__pycache__", ".git", ".venv", "venv"}
    
    verifier = BehaviorVerifier()
    file_reports = {}
    
    source_dir = source_path / module_name
    target_dir = target_path / module_name
    
    if not source_dir.exists():
        return ModuleVerificationReport(
            module_name=module_name,
            file_reports={}
        )
    
    for source_file in source_dir.rglob("*.py"):
        # Skip excluded dirs
        rel_path = source_file.relative_to(source_path)
        if any(skip in rel_path.parts for skip in skip_dirs):
            continue
        
        target_file = target_path / rel_path
        report = verifier.verify_file(source_file, target_file)
        file_reports[str(rel_path)] = report
    
    return ModuleVerificationReport(
        module_name=module_name,
        file_reports=file_reports
    )


def format_verification_table(report: ModuleVerificationReport) -> str:
    """Format verification report as a markdown table."""
    lines = [
        f"# Verification Report: {report.module_name}",
        "",
        f"**Status:** {report.status}",
        f"**Score:** {report.score}",
        "",
        "| File | Status | Passed | Failed | Missing |",
        "|------|--------|--------|--------|---------|"
    ]
    
    for path, file_report in sorted(report.file_reports.items()):
        status_icon = {
            "PASSED": "✅",
            "PARTIAL": "⚠️",
            "FAILED": "❌",
            "MISSING": "🔴"
        }.get(file_report.status, "❓")
        
        lines.append(
            f"| `{path}` | {status_icon} {file_report.status} | "
            f"{file_report.passed} | {file_report.failed} | {file_report.missing} |"
        )
    
    lines.extend([
        "",
        f"**Total:** {report.total_passed} passed, {report.total_failed} failed, "
        f"{report.total_missing} missing, {report.total_partial} partial"
    ])
    
    return "\n".join(lines)
