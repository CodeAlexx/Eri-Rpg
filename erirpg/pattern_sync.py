"""
Sync patterns between EriRPG and Drift.

Provides bidirectional synchronization between:
- .eri-rpg/patterns.json (EriRPG's pattern storage)
- .drift/patterns/ (Drift's pattern storage)

This allows:
- Importing Drift's richer pattern detection into EriRPG
- Exporting EriRPG's project-specific patterns to Drift
- Combined confidence scoring from both sources
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a pattern sync operation."""
    direction: str  # "to_drift", "from_drift", "both"
    exported: int = 0
    imported: int = 0
    merged: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "exported": self.exported,
            "imported": self.imported,
            "merged": self.merged,
            "errors": self.errors,
        }


def sync_patterns(
    project_path: str,
    direction: str = "both"
) -> SyncResult:
    """
    Sync patterns between .eri-rpg/patterns.json and .drift/patterns/

    Args:
        project_path: Root path of the project
        direction: "to_drift", "from_drift", or "both"

    Returns:
        SyncResult with counts of imported/exported patterns
    """
    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"
    drift_path = Path(project_path) / ".drift"

    result = SyncResult(direction=direction)

    if direction in ("from_drift", "both"):
        try:
            result.imported = _import_from_drift(eri_path, drift_path)
        except Exception as e:
            logger.error(f"Failed to import from Drift: {e}")
            result.errors.append(f"Import error: {e}")

    if direction in ("to_drift", "both"):
        try:
            result.exported = _export_to_drift(eri_path, drift_path)
        except Exception as e:
            logger.error(f"Failed to export to Drift: {e}")
            result.errors.append(f"Export error: {e}")

    return result


def _import_from_drift(eri_path: Path, drift_path: Path) -> int:
    """
    Import Drift patterns into EriRPG format.

    Reads patterns from .drift/patterns/{approved,discovered}/*.json
    and merges them into .eri-rpg/patterns.json under "drift_patterns" key.

    Args:
        eri_path: Path to .eri-rpg/patterns.json
        drift_path: Path to .drift/ directory

    Returns:
        Number of patterns imported
    """
    if not drift_path.exists():
        return 0

    # Load existing EriRPG patterns
    eri_patterns = {}
    if eri_path.exists():
        try:
            eri_patterns = json.loads(eri_path.read_text())
        except json.JSONDecodeError:
            eri_patterns = {}

    # Initialize drift_patterns section
    if "drift_patterns" not in eri_patterns:
        eri_patterns["drift_patterns"] = {}

    imported = 0

    # Read Drift pattern files
    patterns_dir = drift_path / "patterns"
    if not patterns_dir.exists():
        return 0

    for status_dir in ["approved", "discovered"]:
        status_path = patterns_dir / status_dir
        if not status_path.exists():
            continue

        for pattern_file in status_path.glob("*.json"):
            try:
                pattern_data = json.loads(pattern_file.read_text())
                pattern_id = pattern_data.get("id", pattern_file.stem)

                # Only import if higher confidence or new
                existing = eri_patterns["drift_patterns"].get(pattern_id, {})
                new_confidence = pattern_data.get("confidence", 0)
                existing_confidence = existing.get("confidence", 0)

                if new_confidence > existing_confidence or pattern_id not in eri_patterns["drift_patterns"]:
                    eri_patterns["drift_patterns"][pattern_id] = {
                        "name": pattern_data.get("name"),
                        "category": pattern_data.get("category"),
                        "confidence": new_confidence,
                        "status": status_dir,
                        "file_count": pattern_data.get("fileCount", 0),
                        "source": "drift",
                        "imported_at": datetime.now().isoformat(),
                    }
                    imported += 1

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read pattern file {pattern_file}: {e}")

    # Also import from lake/patterns if it exists
    lake_patterns = drift_path / "lake" / "patterns"
    if lake_patterns.exists():
        for pattern_file in lake_patterns.glob("*.json"):
            try:
                pattern_data = json.loads(pattern_file.read_text())
                pattern_id = pattern_data.get("id", pattern_file.stem)

                if pattern_id not in eri_patterns["drift_patterns"]:
                    eri_patterns["drift_patterns"][pattern_id] = {
                        "name": pattern_data.get("name"),
                        "category": pattern_data.get("category"),
                        "confidence": pattern_data.get("confidence", 0),
                        "status": "lake",
                        "source": "drift",
                        "imported_at": datetime.now().isoformat(),
                    }
                    imported += 1

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read lake pattern {pattern_file}: {e}")

    # Save merged patterns
    eri_path.parent.mkdir(parents=True, exist_ok=True)
    eri_path.write_text(json.dumps(eri_patterns, indent=2))

    return imported


def _export_to_drift(eri_path: Path, drift_path: Path) -> int:
    """
    Export EriRPG patterns to Drift-compatible format.

    Creates .drift/patterns/custom/*.json files from EriRPG's
    extension_points and registries.

    Args:
        eri_path: Path to .eri-rpg/patterns.json
        drift_path: Path to .drift/ directory

    Returns:
        Number of patterns exported
    """
    if not eri_path.exists():
        return 0

    try:
        eri_patterns = json.loads(eri_path.read_text())
    except json.JSONDecodeError:
        return 0

    exported = 0

    # Create Drift custom patterns directory
    custom_dir = drift_path / "patterns" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    # Export extension points as patterns
    for ext in eri_patterns.get("extension_points", []):
        ext_name = ext.get("name", "unknown")
        pattern_id = f"eri-extension-{_to_slug(ext_name)}"

        pattern_data = {
            "id": pattern_id,
            "name": f"Extension Point: {ext_name}",
            "category": "structural",
            "confidence": 0.8,  # EriRPG detected
            "source": "erirpg",
            "description": f"Extension point for {ext_name}",
            "baseClass": ext.get("base_class"),
            "methodSignatures": ext.get("method_signatures", ext.get("methods", [])),
            "locations": ext.get("locations", [ext.get("location")]),
            "exportedAt": datetime.now().isoformat(),
        }

        pattern_file = custom_dir / f"{pattern_id}.json"
        pattern_file.write_text(json.dumps(pattern_data, indent=2))
        exported += 1

    # Export registries as patterns
    for reg in eri_patterns.get("registries", []):
        reg_name = reg.get("name", "unknown")
        pattern_id = f"eri-registry-{_to_slug(reg_name)}"

        pattern_data = {
            "id": pattern_id,
            "name": f"Registry: {reg_name}",
            "category": "structural",
            "confidence": 0.85,
            "source": "erirpg",
            "description": f"Component registry: {reg_name}",
            "registryType": reg.get("pattern", reg.get("type")),
            "location": reg.get("file", reg.get("path")),
            "exportedAt": datetime.now().isoformat(),
        }

        pattern_file = custom_dir / f"{pattern_id}.json"
        pattern_file.write_text(json.dumps(pattern_data, indent=2))
        exported += 1

    # Export base classes as patterns
    for name, location in eri_patterns.get("base_classes", {}).items():
        pattern_id = f"eri-baseclass-{_to_slug(name)}"

        pattern_data = {
            "id": pattern_id,
            "name": f"Base Class: {name}",
            "category": "structural",
            "confidence": 0.9,
            "source": "erirpg",
            "description": f"Base class for inheritance: {name}",
            "className": name,
            "location": location,
            "exportedAt": datetime.now().isoformat(),
        }

        pattern_file = custom_dir / f"{pattern_id}.json"
        pattern_file.write_text(json.dumps(pattern_data, indent=2))
        exported += 1

    return exported


def _to_slug(text: str) -> str:
    """Convert text to URL-friendly slug."""
    import re
    # Convert to lowercase
    slug = text.lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def get_combined_confidence(
    project_path: str,
    pattern_type: str
) -> float:
    """
    Get combined confidence from both EriRPG and Drift.

    Weights:
    - Drift: 0.6 (more comprehensive pattern detection)
    - EriRPG: 0.4 (project-specific patterns)

    Args:
        project_path: Root path of the project
        pattern_type: Pattern ID or name to look up

    Returns:
        Combined confidence score (0.0-1.0)
    """
    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"

    eri_conf = 0.0
    drift_conf = 0.0
    pattern_lower = pattern_type.lower()

    # Check EriRPG patterns
    if eri_path.exists():
        try:
            patterns = json.loads(eri_path.read_text())

            # Check extension points
            for ext in patterns.get("extension_points", []):
                if pattern_lower in ext.get("name", "").lower():
                    eri_conf = 0.8
                    break

            # Check registries
            if eri_conf == 0:
                for reg in patterns.get("registries", []):
                    if pattern_lower in reg.get("name", "").lower():
                        eri_conf = 0.85
                        break

            # Check base classes
            if eri_conf == 0:
                for name in patterns.get("base_classes", {}):
                    if pattern_lower in name.lower():
                        eri_conf = 0.9
                        break

            # Check imported drift patterns
            if eri_conf == 0:
                for pid, pdata in patterns.get("drift_patterns", {}).items():
                    if pattern_lower in pid.lower() or pattern_lower in pdata.get("name", "").lower():
                        drift_conf = max(drift_conf, pdata.get("confidence", 0))

        except (json.JSONDecodeError, IOError):
            pass

    # Check Drift directly if available
    try:
        from erirpg.drift_bridge import DriftBridge
        bridge = DriftBridge(project_path)
        if bridge.is_available():
            direct_conf = bridge.get_confidence_for_pattern(pattern_type)
            drift_conf = max(drift_conf, direct_conf)
    except ImportError:
        pass

    # Calculate weighted combination
    if drift_conf > 0 and eri_conf > 0:
        return (drift_conf * 0.6) + (eri_conf * 0.4)
    elif drift_conf > 0:
        return drift_conf
    elif eri_conf > 0:
        return eri_conf
    else:
        return 0.0


def get_all_patterns(project_path: str) -> Dict[str, Any]:
    """
    Get all patterns from both EriRPG and Drift.

    Args:
        project_path: Root path of the project

    Returns:
        Dict with patterns from both sources
    """
    result = {
        "eri_patterns": {
            "extension_points": [],
            "registries": [],
            "base_classes": {},
        },
        "drift_patterns": {},
        "combined": [],
    }

    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"

    # Load EriRPG patterns
    if eri_path.exists():
        try:
            patterns = json.loads(eri_path.read_text())
            result["eri_patterns"]["extension_points"] = patterns.get("extension_points", [])
            result["eri_patterns"]["registries"] = patterns.get("registries", [])
            result["eri_patterns"]["base_classes"] = patterns.get("base_classes", {})
            result["drift_patterns"] = patterns.get("drift_patterns", {})
        except (json.JSONDecodeError, IOError):
            pass

    # Get fresh patterns from Drift
    try:
        from erirpg.drift_bridge import DriftBridge
        bridge = DriftBridge(project_path)
        if bridge.is_available():
            drift_patterns = bridge.get_patterns()
            for p in drift_patterns:
                result["drift_patterns"][p.id] = {
                    "name": p.name,
                    "category": p.category,
                    "confidence": p.confidence,
                    "status": p.status,
                    "file_count": p.file_count,
                    "source": "drift_live",
                }
    except ImportError:
        pass

    # Create combined list with confidence
    seen = set()
    for pid, pdata in result["drift_patterns"].items():
        if pid not in seen:
            result["combined"].append({
                "id": pid,
                "name": pdata.get("name", pid),
                "category": pdata.get("category", "unknown"),
                "confidence": pdata.get("confidence", 0),
                "source": pdata.get("source", "unknown"),
            })
            seen.add(pid)

    # Add EriRPG-only patterns
    for ext in result["eri_patterns"]["extension_points"]:
        pid = f"eri-extension-{_to_slug(ext.get('name', 'unknown'))}"
        if pid not in seen:
            result["combined"].append({
                "id": pid,
                "name": f"Extension: {ext.get('name')}",
                "category": "structural",
                "confidence": 0.8,
                "source": "erirpg",
            })
            seen.add(pid)

    for reg in result["eri_patterns"]["registries"]:
        pid = f"eri-registry-{_to_slug(reg.get('name', 'unknown'))}"
        if pid not in seen:
            result["combined"].append({
                "id": pid,
                "name": f"Registry: {reg.get('name')}",
                "category": "structural",
                "confidence": 0.85,
                "source": "erirpg",
            })
            seen.add(pid)

    # Sort by confidence
    result["combined"].sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return result


def get_sync_status(project_path: str) -> Dict[str, Any]:
    """
    Get status of pattern sync between EriRPG and Drift.

    Args:
        project_path: Root path of the project

    Returns:
        Dict with sync status information
    """
    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"
    drift_path = Path(project_path) / ".drift"

    status = {
        "eri_rpg": {
            "exists": eri_path.exists(),
            "pattern_count": 0,
            "drift_patterns_count": 0,
        },
        "drift": {
            "exists": drift_path.exists(),
            "pattern_count": 0,
            "custom_count": 0,
        },
        "sync_possible": False,
    }

    # Check EriRPG
    if eri_path.exists():
        try:
            patterns = json.loads(eri_path.read_text())
            status["eri_rpg"]["pattern_count"] = (
                len(patterns.get("extension_points", [])) +
                len(patterns.get("registries", [])) +
                len(patterns.get("base_classes", {}))
            )
            status["eri_rpg"]["drift_patterns_count"] = len(patterns.get("drift_patterns", {}))
        except (json.JSONDecodeError, IOError):
            pass

    # Check Drift
    if drift_path.exists():
        patterns_dir = drift_path / "patterns"
        if patterns_dir.exists():
            for status_dir in ["approved", "discovered"]:
                status_path = patterns_dir / status_dir
                if status_path.exists():
                    status["drift"]["pattern_count"] += len(list(status_path.glob("*.json")))

            custom_dir = patterns_dir / "custom"
            if custom_dir.exists():
                status["drift"]["custom_count"] = len(list(custom_dir.glob("*.json")))

    status["sync_possible"] = status["eri_rpg"]["exists"] or status["drift"]["exists"]

    return status
