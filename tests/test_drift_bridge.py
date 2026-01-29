"""
Tests for Drift bridge integration.

Tests the DriftBridge class with mocked subprocess calls,
as well as pattern_sync and memory enrichment functions.
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from erirpg.drift_bridge import (
    DriftBridge,
    DriftPattern,
    DriftImpact,
    DriftOutlier,
    DriftFilePatterns,
    drift_available,
)


class TestDriftPattern:
    """Tests for DriftPattern dataclass."""

    def test_from_dict(self):
        """Test creating DriftPattern from dict."""
        data = {
            "id": "api-rest-controller",
            "name": "REST Controller Pattern",
            "category": "api",
            "confidence": 0.92,
            "fileCount": 23,
            "status": "approved",
        }
        pattern = DriftPattern.from_dict(data)

        assert pattern.id == "api-rest-controller"
        assert pattern.name == "REST Controller Pattern"
        assert pattern.category == "api"
        assert pattern.confidence == 0.92
        assert pattern.file_count == 23
        assert pattern.status == "approved"

    def test_from_dict_with_snake_case(self):
        """Test creating DriftPattern from dict with snake_case keys."""
        data = {
            "id": "test-pattern",
            "name": "Test Pattern",
            "category": "testing",
            "confidence": 0.8,
            "file_count": 5,
        }
        pattern = DriftPattern.from_dict(data)

        assert pattern.file_count == 5


class TestDriftImpact:
    """Tests for DriftImpact dataclass."""

    def test_from_dict(self):
        """Test creating DriftImpact from dict."""
        data = {
            "affected_files": ["src/a.py", "src/b.py"],
            "affected_functions": ["foo", "bar"],
            "risk_level": "high",
            "coupling_score": 0.85,
        }
        impact = DriftImpact.from_dict(data)

        assert impact.affected_files == ["src/a.py", "src/b.py"]
        assert impact.affected_functions == ["foo", "bar"]
        assert impact.risk_level == "high"
        assert impact.coupling_score == 0.85

    def test_from_dict_camelCase(self):
        """Test creating DriftImpact from camelCase keys."""
        data = {
            "affectedFiles": ["src/c.py"],
            "affectedFunctions": ["baz"],
            "riskLevel": "low",
            "couplingScore": 0.2,
        }
        impact = DriftImpact.from_dict(data)

        assert impact.affected_files == ["src/c.py"]
        assert impact.risk_level == "low"


class TestDriftOutlier:
    """Tests for DriftOutlier dataclass."""

    def test_from_dict(self):
        """Test creating DriftOutlier from dict."""
        data = {
            "file": "src/api/users.ts",
            "line": 42,
            "pattern_id": "api-rest-controller",
            "pattern_name": "REST Controller",
            "description": "Missing response envelope",
            "severity": "high",
        }
        outlier = DriftOutlier.from_dict(data)

        assert outlier.file == "src/api/users.ts"
        assert outlier.line == 42
        assert outlier.pattern_id == "api-rest-controller"
        assert outlier.description == "Missing response envelope"
        assert outlier.severity == "high"


class TestDriftBridge:
    """Tests for DriftBridge class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .drift directory
            drift_dir = Path(tmpdir) / ".drift"
            drift_dir.mkdir()
            (drift_dir / "manifest.json").write_text('{"lastScan": "2024-01-01"}')
            yield tmpdir

    def test_init(self, temp_project):
        """Test DriftBridge initialization."""
        bridge = DriftBridge(temp_project)

        assert bridge.project_path == Path(temp_project).resolve()
        assert bridge.drift_dir == Path(temp_project).resolve() / ".drift"
        assert bridge.timeout == 30

    @patch("subprocess.run")
    def test_is_available_true(self, mock_run, temp_project):
        """Test is_available returns True when Drift is installed and scanned."""
        mock_run.return_value = MagicMock(returncode=0, stdout="drift 1.0.0")

        bridge = DriftBridge(temp_project)
        assert bridge.is_available() is True

    @patch("subprocess.run")
    def test_is_available_false_no_cli(self, mock_run, temp_project):
        """Test is_available returns False when Drift CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        bridge = DriftBridge(temp_project)
        assert bridge.is_available() is False

    def test_is_available_false_no_drift_dir(self):
        """Test is_available returns False when .drift directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = DriftBridge(tmpdir)
            # Don't need to mock subprocess - drift_dir doesn't exist
            bridge._available = None  # Reset cache
            # Manually set CLI available but no drift dir
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert bridge.is_available() is False

    @patch("subprocess.run")
    def test_get_patterns(self, mock_run, temp_project):
        """Test get_patterns returns parsed patterns."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "patterns": [
                    {"id": "p1", "name": "Pattern 1", "category": "api", "confidence": 0.9},
                    {"id": "p2", "name": "Pattern 2", "category": "auth", "confidence": 0.8},
                ]
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True  # Skip availability check

        patterns = bridge.get_patterns()

        assert len(patterns) == 2
        assert patterns[0].id == "p1"
        assert patterns[0].confidence == 0.9

    @patch("subprocess.run")
    def test_get_patterns_with_category(self, mock_run, temp_project):
        """Test get_patterns with category filter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"patterns": []})
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        bridge.get_patterns(category="api")

        # Check that --category was passed
        call_args = mock_run.call_args[0][0]
        assert "--category" in call_args
        assert "api" in call_args

    @patch("subprocess.run")
    def test_get_file_patterns(self, mock_run, temp_project):
        """Test get_file_patterns returns file-specific patterns and outliers."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "patterns": [
                    {"id": "p1", "name": "P1", "category": "api", "confidence": 0.9}
                ],
                "outliers": [
                    {"file": "test.py", "line": 10, "pattern_id": "p2",
                     "pattern_name": "P2", "description": "Issue"}
                ]
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        result = bridge.get_file_patterns("test.py")

        assert isinstance(result, DriftFilePatterns)
        assert len(result.patterns) == 1
        assert len(result.outliers) == 1
        assert result.outliers[0].line == 10

    @patch("subprocess.run")
    def test_impact_analysis(self, mock_run, temp_project):
        """Test impact_analysis returns impact data."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "affected_files": ["a.py", "b.py"],
                "affected_functions": ["foo"],
                "risk_level": "medium",
                "coupling_score": 0.5,
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        impact = bridge.impact_analysis("test.py")

        assert impact.risk_level == "medium"
        assert len(impact.affected_files) == 2
        assert impact.coupling_score == 0.5

    @patch("subprocess.run")
    def test_find_outliers(self, mock_run, temp_project):
        """Test find_outliers returns outlier list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "outliers": [
                    {"file": "a.py", "line": 5, "pattern_id": "p1",
                     "pattern_name": "P1", "description": "Issue 1"},
                    {"file": "b.py", "line": 10, "pattern_id": "p2",
                     "pattern_name": "P2", "description": "Issue 2"},
                ]
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        outliers = bridge.find_outliers()

        assert len(outliers) == 2
        assert outliers[0].file == "a.py"
        assert outliers[1].line == 10

    @patch("subprocess.run")
    def test_validate_change(self, mock_run, temp_project):
        """Test validate_change returns validation result."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "valid": True,
                "errors": [],
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        result = bridge.validate_change("test.py", "new content")

        assert result["valid"] is True

    @patch("subprocess.run")
    def test_get_confidence_for_pattern(self, mock_run, temp_project):
        """Test get_confidence_for_pattern returns confidence score."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "patterns": [
                    {"id": "api-rest", "name": "REST API", "category": "api", "confidence": 0.95},
                ]
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        # Exact match
        conf = bridge.get_confidence_for_pattern("api-rest")
        assert conf == 0.95

    @patch("subprocess.run")
    def test_get_status(self, mock_run, temp_project):
        """Test get_status returns status dict."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "patterns": [
                    {"id": "p1", "name": "P1", "category": "api", "confidence": 0.9},
                    {"id": "p2", "name": "P2", "category": "api", "confidence": 0.8},
                    {"id": "p3", "name": "P3", "category": "auth", "confidence": 0.7},
                ]
            })
        )

        bridge = DriftBridge(temp_project)
        bridge._available = True

        status = bridge.get_status()

        assert status["available"] is True
        assert status["patterns"]["total"] == 3
        assert status["patterns"]["by_category"]["api"] == 2
        assert status["patterns"]["by_category"]["auth"] == 1

    def test_graceful_degradation_unavailable(self, temp_project):
        """Test methods gracefully handle unavailable Drift."""
        bridge = DriftBridge(temp_project)
        bridge._available = False

        # All methods should return empty/default values
        assert bridge.get_patterns() == []
        assert bridge.get_file_patterns("test.py").patterns == []
        assert bridge.impact_analysis("test.py").risk_level == "unknown"
        assert bridge.find_outliers() == []
        assert bridge.validate_change("test.py", "content")["skipped"] is True

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run, temp_project):
        """Test timeout is properly handled."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("drift", 30)

        bridge = DriftBridge(temp_project, timeout=30)
        bridge._available = True

        # Should return None/empty, not raise
        result = bridge._run_drift(["patterns", "list"])
        assert result is None

    def test_clear_cache(self, temp_project):
        """Test cache clearing."""
        bridge = DriftBridge(temp_project)

        # Add something to cache
        DriftBridge._pattern_cache["test"] = []
        DriftBridge._file_pattern_cache["test"] = DriftFilePatterns(file="test")

        bridge.clear_cache()

        assert "test" not in DriftBridge._pattern_cache
        assert "test" not in DriftBridge._file_pattern_cache


class TestDriftAvailable:
    """Tests for the drift_available convenience function."""

    @patch("subprocess.run")
    def test_drift_available_true(self, mock_run):
        """Test drift_available returns True when available."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            drift_dir = Path(tmpdir) / ".drift"
            drift_dir.mkdir()
            (drift_dir / "manifest.json").write_text("{}")

            assert drift_available(tmpdir) is True

    def test_drift_available_false(self):
        """Test drift_available returns False when not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No .drift directory
            assert drift_available(tmpdir) is False


class TestPatternSync:
    """Tests for pattern_sync module."""

    @pytest.fixture
    def temp_project_with_patterns(self):
        """Create temp project with EriRPG patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .eri-rpg/patterns.json
            eri_dir = Path(tmpdir) / ".eri-rpg"
            eri_dir.mkdir()
            patterns = {
                "extension_points": [
                    {"name": "BaseScheduler", "location": "schedulers/base.py", "methods": ["step"]}
                ],
                "registries": [
                    {"name": "SchedulerFactory", "file": "schedulers/factory.py", "pattern": "dict"}
                ],
                "base_classes": {
                    "BaseScheduler": "schedulers/base.py"
                },
            }
            (eri_dir / "patterns.json").write_text(json.dumps(patterns))

            # Create .drift directory
            drift_dir = Path(tmpdir) / ".drift"
            drift_dir.mkdir()
            patterns_dir = drift_dir / "patterns" / "approved"
            patterns_dir.mkdir(parents=True)
            (patterns_dir / "test-pattern.json").write_text(json.dumps({
                "id": "test-pattern",
                "name": "Test Pattern",
                "category": "testing",
                "confidence": 0.85,
            }))

            yield tmpdir

    def test_sync_from_drift(self, temp_project_with_patterns):
        """Test importing patterns from Drift."""
        from erirpg.pattern_sync import sync_patterns

        result = sync_patterns(temp_project_with_patterns, direction="from_drift")

        assert result.imported == 1

        # Check patterns.json was updated
        eri_path = Path(temp_project_with_patterns) / ".eri-rpg" / "patterns.json"
        patterns = json.loads(eri_path.read_text())
        assert "drift_patterns" in patterns
        assert "test-pattern" in patterns["drift_patterns"]

    def test_sync_to_drift(self, temp_project_with_patterns):
        """Test exporting patterns to Drift."""
        from erirpg.pattern_sync import sync_patterns

        result = sync_patterns(temp_project_with_patterns, direction="to_drift")

        assert result.exported == 3  # 1 extension + 1 registry + 1 base class

        # Check custom patterns were created
        custom_dir = Path(temp_project_with_patterns) / ".drift" / "patterns" / "custom"
        assert custom_dir.exists()
        assert len(list(custom_dir.glob("*.json"))) == 3

    def test_get_combined_confidence(self, temp_project_with_patterns):
        """Test combined confidence calculation."""
        from erirpg.pattern_sync import get_combined_confidence

        # Should find BaseScheduler in EriRPG patterns
        conf = get_combined_confidence(temp_project_with_patterns, "BaseScheduler")
        assert conf == 0.8  # Base class confidence (updated)

    def test_get_sync_status(self, temp_project_with_patterns):
        """Test sync status reporting."""
        from erirpg.pattern_sync import get_sync_status

        status = get_sync_status(temp_project_with_patterns)

        assert status["eri_rpg"]["exists"] is True
        assert status["eri_rpg"]["pattern_count"] == 3  # ext + reg + base
        assert status["drift"]["exists"] is True
        assert status["drift"]["pattern_count"] == 1
        assert status["sync_possible"] is True


class TestMemoryEnrichment:
    """Tests for memory enrichment functions."""

    @pytest.fixture
    def temp_project_with_learnings(self):
        """Create temp project with learnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .eri-rpg directory
            eri_dir = Path(tmpdir) / ".eri-rpg"
            eri_dir.mkdir()

            # Create knowledge.json with learnings
            from datetime import datetime
            knowledge = {
                "project": "test",
                "version": "2.2.0",
                "learnings": {
                    "src/api.py": {
                        "module_path": "src/api.py",
                        "learned_at": datetime.now().isoformat(),
                        "summary": "API handler",
                        "purpose": "Handle API requests",
                        "key_functions": {},
                        "gotchas": [],
                        "validated_by_drift": False,
                    }
                },
                "decisions": [],
                "patterns": {},
                "discussions": {},
                "runs": [],
                "user_decisions": [],
                "deferred_ideas": [],
            }
            (eri_dir / "knowledge.json").write_text(json.dumps(knowledge))

            # Create .drift directory
            drift_dir = Path(tmpdir) / ".drift"
            drift_dir.mkdir()
            (drift_dir / "manifest.json").write_text("{}")

            yield tmpdir

    @patch("subprocess.run")
    def test_enrich_learnings_batch(self, mock_run, temp_project_with_learnings):
        """Test batch enrichment of learnings."""
        from erirpg.memory import enrich_learnings_batch

        # Mock Drift responses
        def mock_subprocess(*args, **kwargs):
            cmd = args[0]
            if "file" in cmd and "patterns" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({
                        "patterns": [{"id": "api-pattern", "name": "API", "category": "api", "confidence": 0.9}],
                        "outliers": []
                    })
                )
            elif "check" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({"outliers": []})
                )
            elif "--version" in cmd:
                return MagicMock(returncode=0, stdout="drift 1.0")
            return MagicMock(returncode=0, stdout="{}")

        mock_run.side_effect = mock_subprocess

        stats = enrich_learnings_batch(temp_project_with_learnings)

        assert stats["drift_available"] is True
        # Note: enriched count depends on pattern matching logic

    def test_enrich_learnings_batch_no_drift(self):
        """Test enrichment gracefully handles missing Drift."""
        from erirpg.memory import enrich_learnings_batch

        with tempfile.TemporaryDirectory() as tmpdir:
            # No .drift directory
            eri_dir = Path(tmpdir) / ".eri-rpg"
            eri_dir.mkdir()
            (eri_dir / "knowledge.json").write_text("{}")

            stats = enrich_learnings_batch(tmpdir)

            assert stats["drift_available"] is False
            assert stats["enriched"] == 0
