"""
Bridge to Drift codebase intelligence.

Provides a thin wrapper around Drift CLI commands with:
- LRU caching for repeated queries
- Async variants for GUI/watch mode
- Graceful degradation when Drift unavailable
"""
import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftPattern:
    """Pattern detected by Drift."""
    id: str
    name: str
    category: str  # api, auth, security, errors, logging, data-access, etc.
    confidence: float  # 0.0-1.0
    file_count: int = 0
    status: str = "discovered"  # discovered, approved, ignored

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriftPattern":
        """Create from Drift JSON output."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            confidence=data.get("confidence", 0.0),
            file_count=data.get("fileCount", data.get("file_count", 0)),
            status=data.get("status", "discovered")
        )


@dataclass
class DriftImpact:
    """Impact analysis result from Drift callgraph."""
    affected_files: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    risk_level: str = "unknown"  # low, medium, high, critical
    coupling_score: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriftImpact":
        """Create from Drift JSON output."""
        return cls(
            affected_files=data.get("affected_files", data.get("affectedFiles", [])),
            affected_functions=data.get("affected_functions", data.get("affectedFunctions", [])),
            risk_level=data.get("risk_level", data.get("riskLevel", "unknown")),
            coupling_score=data.get("coupling_score", data.get("couplingScore", 0.0))
        )


@dataclass
class DriftOutlier:
    """Code that deviates from established patterns."""
    file: str
    line: int
    pattern_id: str
    pattern_name: str
    description: str
    severity: str = "medium"  # low, medium, high

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriftOutlier":
        """Create from Drift JSON output."""
        return cls(
            file=data.get("file", ""),
            line=data.get("line", data.get("startLine", 0)),
            pattern_id=data.get("pattern_id", data.get("patternId", "")),
            pattern_name=data.get("pattern_name", data.get("patternName", "")),
            description=data.get("description", ""),
            severity=data.get("severity", data.get("priority", "medium"))
        )


@dataclass
class DriftFilePatterns:
    """Patterns and outliers for a specific file."""
    file: str
    patterns: List[DriftPattern] = field(default_factory=list)
    outliers: List[DriftOutlier] = field(default_factory=list)

    @classmethod
    def from_dict(cls, file: str, data: Dict[str, Any]) -> "DriftFilePatterns":
        """Create from Drift JSON output."""
        return cls(
            file=file,
            patterns=[DriftPattern.from_dict(p) for p in data.get("patterns", [])],
            outliers=[DriftOutlier.from_dict(o) for o in data.get("outliers", [])]
        )


class DriftBridge:
    """
    Interface to Drift CLI/MCP.

    Provides methods to query Drift's codebase intelligence:
    - Pattern detection and confidence scoring
    - Call graph and impact analysis
    - Outlier detection (code that doesn't match patterns)
    - Change validation

    Usage:
        bridge = DriftBridge("/path/to/project")
        if bridge.is_available():
            patterns = bridge.get_patterns()
            impact = bridge.impact_analysis("src/file.py")
    """

    # Class-level cache for expensive operations
    _pattern_cache: Dict[str, List[DriftPattern]] = {}
    _file_pattern_cache: Dict[str, DriftFilePatterns] = {}

    def __init__(self, project_path: str, timeout: int = 30):
        """
        Initialize Drift bridge.

        Args:
            project_path: Path to project root (should contain .drift/)
            timeout: Timeout in seconds for Drift CLI commands
        """
        self.project_path = Path(project_path).resolve()
        self.drift_dir = self.project_path / ".drift"
        self.timeout = timeout
        self._available: Optional[bool] = None

    def _run_drift(
        self,
        args: List[str],
        input_data: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Run a Drift CLI command and parse JSON output.

        Args:
            args: Command arguments (e.g., ["patterns", "list"])
            input_data: Optional stdin input

        Returns:
            Parsed JSON output or None on failure
        """
        cmd = ["drift"] + args + ["--json"]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                logger.debug(f"Drift command failed: {result.stderr}")
                return None

            if not result.stdout.strip():
                return {}

            return json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            logger.warning(f"Drift command timed out: {' '.join(cmd)}")
            return None
        except FileNotFoundError:
            logger.debug("Drift CLI not found")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Drift output: {e}")
            return None
        except Exception as e:
            logger.warning(f"Drift command error: {e}")
            return None

    async def _run_drift_async(
        self,
        args: List[str],
        input_data: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Run a Drift CLI command asynchronously.

        For GUI/watch mode where blocking is unacceptable.
        """
        cmd = ["drift"] + args + ["--json"]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_data.encode() if input_data else None),
                timeout=self.timeout
            )

            if process.returncode != 0:
                logger.debug(f"Drift command failed: {stderr.decode()}")
                return None

            output = stdout.decode()
            if not output.strip():
                return {}

            return json.loads(output)

        except asyncio.TimeoutError:
            logger.warning(f"Drift command timed out: {' '.join(cmd)}")
            return None
        except FileNotFoundError:
            logger.debug("Drift CLI not found")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Drift output: {e}")
            return None
        except Exception as e:
            logger.warning(f"Drift command error: {e}")
            return None

    def is_available(self) -> bool:
        """
        Check if Drift is installed and project has been scanned.

        Caches result for performance.
        """
        if self._available is not None:
            return self._available

        # Check if drift CLI exists
        try:
            result = subprocess.run(
                ["drift", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            cli_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            cli_available = False

        # Check if project has been scanned
        scanned = self.drift_dir.exists() and (self.drift_dir / "manifest.json").exists()

        self._available = cli_available and scanned
        return self._available

    def scan(self, force: bool = False, incremental: bool = True) -> bool:
        """
        Run Drift scan on project.

        Args:
            force: Force full rescan even if incremental available
            incremental: Use incremental scan (default True)

        Returns:
            True if scan succeeded
        """
        cmd = ["scan"]
        if force:
            cmd.append("--force")
        if not incremental:
            cmd.append("--full")

        result = self._run_drift(cmd)
        if result is not None:
            # Invalidate caches after scan
            self.clear_cache()
            self._available = None
            return True
        return False

    def clear_cache(self) -> None:
        """Clear all cached data."""
        DriftBridge._pattern_cache.clear()
        DriftBridge._file_pattern_cache.clear()

    @lru_cache(maxsize=32)
    def get_patterns(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[DriftPattern]:
        """
        Get detected patterns from Drift.

        Args:
            category: Filter by category (api, auth, security, etc.)
            status: Filter by status (discovered, approved, ignored)

        Returns:
            List of DriftPattern objects
        """
        if not self.is_available():
            return []

        # Check class-level cache
        cache_key = f"{self.project_path}:{category}:{status}"
        if cache_key in DriftBridge._pattern_cache:
            return DriftBridge._pattern_cache[cache_key]

        cmd = ["patterns", "list"]
        if category:
            cmd.extend(["--category", category])
        if status:
            cmd.extend(["--status", status])

        data = self._run_drift(cmd)
        if data is None:
            return []

        patterns = [
            DriftPattern.from_dict(p)
            for p in data.get("patterns", data.get("data", {}).get("patterns", []))
        ]

        DriftBridge._pattern_cache[cache_key] = patterns
        return patterns

    @lru_cache(maxsize=128)
    def get_file_patterns(self, file_path: str) -> DriftFilePatterns:
        """
        Get patterns and outliers for a specific file.

        Args:
            file_path: Path to file (relative to project root)

        Returns:
            DriftFilePatterns with patterns and outliers for this file
        """
        if not self.is_available():
            return DriftFilePatterns(file=file_path)

        # Check class-level cache
        cache_key = f"{self.project_path}:{file_path}"
        if cache_key in DriftBridge._file_pattern_cache:
            return DriftBridge._file_pattern_cache[cache_key]

        data = self._run_drift(["file", "patterns", file_path])
        if data is None:
            return DriftFilePatterns(file=file_path)

        result = DriftFilePatterns.from_dict(
            file_path,
            data.get("data", data)
        )

        DriftBridge._file_pattern_cache[cache_key] = result
        return result

    def impact_analysis(self, file_path: str) -> DriftImpact:
        """
        Analyze impact of changing a file.

        Uses Drift's call graph to find:
        - What other files would be affected
        - What functions call into this file
        - Risk level of the change
        - Coupling score

        Args:
            file_path: Path to file being changed

        Returns:
            DriftImpact with affected files and risk assessment
        """
        if not self.is_available():
            return DriftImpact()

        data = self._run_drift(["callgraph", "impact", file_path])
        if data is None:
            return DriftImpact()

        return DriftImpact.from_dict(data.get("data", data))

    async def impact_analysis_async(self, file_path: str) -> DriftImpact:
        """Async variant of impact_analysis for GUI/watch mode."""
        if not self.is_available():
            return DriftImpact()

        data = await self._run_drift_async(["callgraph", "impact", file_path])
        if data is None:
            return DriftImpact()

        return DriftImpact.from_dict(data.get("data", data))

    def find_outliers(self, file_path: Optional[str] = None) -> List[DriftOutlier]:
        """
        Find code that deviates from established patterns.

        Args:
            file_path: Optional specific file to check, or None for all

        Returns:
            List of DriftOutlier objects
        """
        if not self.is_available():
            return []

        cmd = ["check"]
        if file_path:
            cmd.append(file_path)

        data = self._run_drift(cmd)
        if data is None:
            return []

        outliers_data = data.get("outliers", data.get("data", {}).get("outliers", []))
        return [DriftOutlier.from_dict(o) for o in outliers_data]

    async def find_outliers_async(
        self,
        file_path: Optional[str] = None
    ) -> List[DriftOutlier]:
        """Async variant of find_outliers for GUI/watch mode."""
        if not self.is_available():
            return []

        cmd = ["check"]
        if file_path:
            cmd.append(file_path)

        data = await self._run_drift_async(cmd)
        if data is None:
            return []

        outliers_data = data.get("outliers", data.get("data", {}).get("outliers", []))
        return [DriftOutlier.from_dict(o) for o in outliers_data]

    def validate_change(
        self,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Validate proposed code change against patterns.

        Args:
            file_path: Path to file being changed
            content: New content to validate

        Returns:
            Validation result with 'valid' bool and any 'errors'
        """
        if not self.is_available():
            return {"valid": True, "skipped": True, "reason": "Drift unavailable"}

        data = self._run_drift(
            ["validate", file_path, "--content", "-"],
            input_data=content
        )

        if data is None:
            return {"valid": True, "skipped": True, "reason": "Validation failed"}

        return data.get("data", data)

    def get_confidence_for_pattern(self, pattern_type: str) -> float:
        """
        Get confidence score for a pattern type in this codebase.

        Args:
            pattern_type: Pattern ID or name to look up

        Returns:
            Confidence score (0.0-1.0) or 0.0 if not found
        """
        patterns = self.get_patterns()
        pattern_lower = pattern_type.lower()

        for p in patterns:
            if p.id.lower() == pattern_lower or p.name.lower() == pattern_lower:
                return p.confidence

        # Try partial match
        for p in patterns:
            if pattern_lower in p.id.lower() or pattern_lower in p.name.lower():
                return p.confidence

        return 0.0

    def get_code_examples(
        self,
        pattern_id: str,
        max_examples: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get code examples for a specific pattern.

        Args:
            pattern_id: ID of pattern to get examples for
            max_examples: Maximum number of examples to return

        Returns:
            List of example dicts with 'file', 'lines', 'code' keys
        """
        if not self.is_available():
            return []

        data = self._run_drift([
            "examples", pattern_id,
            "--limit", str(max_examples)
        ])

        if data is None:
            return []

        return data.get("examples", data.get("data", {}).get("examples", []))

    def suggest_changes(
        self,
        file_path: str,
        issue_type: str = "outlier"
    ) -> List[Dict[str, Any]]:
        """
        Get AI-guided suggestions for fixing issues.

        Args:
            file_path: File to get suggestions for
            issue_type: Type of issue (outlier, security, coupling, error-handling)

        Returns:
            List of suggestion dicts with before/after/rationale
        """
        if not self.is_available():
            return []

        data = self._run_drift([
            "suggest", file_path,
            "--issue", issue_type
        ])

        if data is None:
            return []

        return data.get("suggestions", data.get("data", {}).get("suggestions", []))

    def get_status(self) -> Dict[str, Any]:
        """
        Get Drift status for this project.

        Returns:
            Dict with version, scan status, pattern counts, etc.
        """
        status = {
            "available": self.is_available(),
            "project_path": str(self.project_path),
            "drift_dir_exists": self.drift_dir.exists(),
            "patterns": {},
            "last_scan": None
        }

        if not self.is_available():
            return status

        # Get pattern counts by category
        patterns = self.get_patterns()
        by_category: Dict[str, int] = {}
        for p in patterns:
            by_category[p.category] = by_category.get(p.category, 0) + 1
        status["patterns"] = {
            "total": len(patterns),
            "by_category": by_category
        }

        # Get last scan time from manifest
        manifest_path = self.drift_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                status["last_scan"] = manifest.get("lastScan", manifest.get("timestamp"))
            except (json.JSONDecodeError, IOError):
                pass

        return status


# Convenience function for quick checks
def drift_available(project_path: str) -> bool:
    """Quick check if Drift is available for a project."""
    return DriftBridge(project_path).is_available()
