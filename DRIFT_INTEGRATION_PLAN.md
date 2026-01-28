# Drift + EriRPG Integration Plan

## Overview

Integrate Drift's codebase intelligence (pattern detection, call graphs, confidence scoring) into EriRPG's learning and implementation system.

**Two Integration Paths:**
- **CLI Bridge** - Call `drift` commands, parse JSON output (simpler, works now)
- **MCP Direct** - Call Drift MCP tools from Claude hooks (cleaner, requires MCP setup)

We'll implement CLI Bridge first, with MCP-ready interfaces.

---

## Phase 1: Foundation (`drift_bridge.py`)

**Goal:** Thin wrapper to call Drift CLI and parse results

### File: `erirpg/drift_bridge.py`

```python
"""Bridge to Drift codebase intelligence."""
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class DriftPattern:
    """Pattern detected by Drift."""
    id: str
    name: str
    category: str  # api, auth, security, errors, etc.
    confidence: float  # 0.0-1.0
    file_count: int
    status: str  # discovered, approved, ignored

@dataclass
class DriftImpact:
    """Impact analysis result."""
    affected_files: List[str]
    affected_functions: List[str]
    risk_level: str  # low, medium, high
    coupling_score: float

@dataclass
class DriftOutlier:
    """Code that deviates from patterns."""
    file: str
    line: int
    pattern_id: str
    pattern_name: str
    description: str

class DriftBridge:
    """Interface to Drift CLI/MCP."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.drift_dir = self.project_path / ".drift"

    def is_available(self) -> bool:
        """Check if Drift is installed and project is scanned."""
        try:
            result = subprocess.run(
                ["drift", "--version"],
                capture_output=True, text=True
            )
            return result.returncode == 0 and self.drift_dir.exists()
        except FileNotFoundError:
            return False

    def scan(self, force: bool = False) -> bool:
        """Run drift scan on project."""
        cmd = ["drift", "scan"]
        if force:
            cmd.append("--force")
        result = subprocess.run(
            cmd, cwd=self.project_path,
            capture_output=True, text=True
        )
        return result.returncode == 0

    def get_patterns(self, category: Optional[str] = None) -> List[DriftPattern]:
        """Get detected patterns."""
        cmd = ["drift", "patterns", "list", "--json"]
        if category:
            cmd.extend(["--category", category])
        result = subprocess.run(
            cmd, cwd=self.project_path,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return [DriftPattern(**p) for p in data.get("patterns", [])]

    def get_file_patterns(self, file_path: str) -> Dict[str, Any]:
        """Get patterns for a specific file."""
        cmd = ["drift", "file", "patterns", file_path, "--json"]
        result = subprocess.run(
            cmd, cwd=self.project_path,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"patterns": [], "outliers": []}
        return json.loads(result.stdout)

    def impact_analysis(self, file_path: str) -> DriftImpact:
        """Analyze impact of changing a file."""
        cmd = ["drift", "callgraph", "impact", file_path, "--json"]
        result = subprocess.run(
            cmd, cwd=self.project_path,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return DriftImpact([], [], "unknown", 0.0)
        data = json.loads(result.stdout)
        return DriftImpact(
            affected_files=data.get("affected_files", []),
            affected_functions=data.get("affected_functions", []),
            risk_level=data.get("risk_level", "unknown"),
            coupling_score=data.get("coupling_score", 0.0)
        )

    def find_outliers(self, file_path: Optional[str] = None) -> List[DriftOutlier]:
        """Find code that deviates from patterns."""
        cmd = ["drift", "check", "--json"]
        if file_path:
            cmd.append(file_path)
        result = subprocess.run(
            cmd, cwd=self.project_path,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return [DriftOutlier(**o) for o in data.get("outliers", [])]

    def validate_change(self, file_path: str, content: str) -> Dict[str, Any]:
        """Validate proposed code change against patterns."""
        cmd = ["drift", "validate", file_path, "--content", "-", "--json"]
        result = subprocess.run(
            cmd, cwd=self.project_path,
            input=content, capture_output=True, text=True
        )
        if result.returncode != 0:
            return {"valid": False, "errors": [result.stderr]}
        return json.loads(result.stdout)

    def get_confidence_for_pattern(self, pattern_type: str) -> float:
        """Get confidence score for a pattern type in this codebase."""
        patterns = self.get_patterns()
        for p in patterns:
            if p.id == pattern_type or p.name.lower() == pattern_type.lower():
                return p.confidence
        return 0.0
```

### Deliverables
- [ ] `erirpg/drift_bridge.py` with DriftBridge class
- [ ] Unit tests for bridge (mocked subprocess)
- [ ] CLI command: `eri drift-status` - check if Drift available

---

## Phase 2: Enhanced StoredLearning

**Goal:** Add pattern confidence and outlier tracking to learnings

### Changes to `erirpg/memory.py`

```python
@dataclass
class StoredLearning:
    # Existing fields...
    file_path: str
    what_i_learned: str
    why_it_matters: str
    code_pattern: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Pattern-aware fields (from analyze.py)
    implements: Optional[str] = None
    registered_in: Optional[str] = None
    hooks_into: List[str] = field(default_factory=list)
    public_interface: List[str] = field(default_factory=list)

    # NEW: Drift integration fields
    drift_pattern_id: Optional[str] = None      # "api-rest-controller"
    drift_confidence: float = 0.0               # 0.0-1.0 from Drift
    is_outlier: bool = False                    # Deviates from patterns
    outlier_reason: Optional[str] = None        # Why it's an outlier
    validated_by_drift: bool = False            # Has Drift verified this

    def enrich_with_drift(self, bridge: 'DriftBridge') -> None:
        """Enrich learning with Drift pattern data."""
        if not bridge.is_available():
            return

        file_data = bridge.get_file_patterns(self.file_path)

        for pattern in file_data.get("patterns", []):
            if self._matches_pattern(pattern):
                self.drift_pattern_id = pattern["id"]
                self.drift_confidence = pattern["confidence"]
                break

        outliers = file_data.get("outliers", [])
        for outlier in outliers:
            if self._is_about_outlier(outlier):
                self.is_outlier = True
                self.outlier_reason = outlier.get("description")
                break

        self.validated_by_drift = True
```

### Deliverables
- [ ] Update `StoredLearning` dataclass with Drift fields
- [ ] Add `enrich_with_drift()` method
- [ ] Add `enrich_learnings_batch()` function
- [ ] CLI command: `eri enrich-learnings` - batch enrich with Drift

---

## Phase 3: Pre-Implement Impact Hook

**Goal:** Run Drift impact analysis before making changes

### Changes to `erirpg/implement.py`

```python
def plan_implementation(
    feature_description: str,
    project_path: str,
    patterns: Optional[ProjectPatterns] = None,
    use_drift: bool = True  # NEW
) -> ImplementationPlan:
    """Plan implementation with optional Drift impact analysis."""

    plan = _create_base_plan(feature_description, project_path, patterns)

    if use_drift:
        plan = _enrich_with_drift_impact(plan, project_path)

    return plan

def _enrich_with_drift_impact(
    plan: ImplementationPlan,
    project_path: str
) -> ImplementationPlan:
    """Add Drift impact analysis to plan."""
    from .drift_bridge import DriftBridge

    bridge = DriftBridge(project_path)
    if not bridge.is_available():
        return plan

    for file_plan in plan.files:
        impact = bridge.impact_analysis(file_plan.path)

        for affected in impact.affected_files:
            if affected not in [f.path for f in plan.files]:
                file_plan.notes.append(f"Also affects: {affected}")

        if impact.coupling_score > 0.7:
            file_plan.notes.append(
                f"High coupling ({impact.coupling_score:.2f}) - changes may ripple"
            )

        file_plan.risk = impact.risk_level

        outliers = bridge.find_outliers(file_plan.path)
        if outliers:
            file_plan.notes.append(
                f"Current outliers: {len(outliers)} - consider fixing"
            )

    plan.pre_checks.append("Run: drift callgraph show --focus <entry_point>")

    return plan
```

### Deliverables
- [ ] Add `use_drift` param to `plan_implementation()`
- [ ] Create `_enrich_with_drift_impact()` function
- [ ] Add `risk` field to `FilePlan`
- [ ] CLI flag: `eri implement --no-drift` to skip enrichment

---

## Phase 4: Pattern Sync

**Goal:** Merge EriRPG patterns with Drift patterns bidirectionally

### File: `erirpg/pattern_sync.py`

```python
"""Sync patterns between EriRPG and Drift."""
import json
from pathlib import Path
from typing import Dict

def sync_patterns(project_path: str, direction: str = "both") -> Dict[str, int]:
    """
    Sync patterns between .eri-rpg/patterns.json and .drift/patterns/

    direction: "to_drift", "from_drift", "both"
    Returns: {"exported": n, "imported": n}
    """
    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"
    drift_path = Path(project_path) / ".drift"

    stats = {"exported": 0, "imported": 0}

    if direction in ("from_drift", "both"):
        stats["imported"] = _import_from_drift(eri_path, drift_path)

    if direction in ("to_drift", "both"):
        stats["exported"] = _export_to_drift(eri_path, drift_path)

    return stats

def _import_from_drift(eri_path: Path, drift_path: Path) -> int:
    """Import Drift patterns into EriRPG format."""
    if not drift_path.exists():
        return 0

    eri_patterns = {}
    if eri_path.exists():
        eri_patterns = json.loads(eri_path.read_text())

    if "drift_patterns" not in eri_patterns:
        eri_patterns["drift_patterns"] = {}

    imported = 0

    patterns_dir = drift_path / "patterns"
    if patterns_dir.exists():
        for status_dir in ["approved", "discovered"]:
            status_path = patterns_dir / status_dir
            if status_path.exists():
                for pattern_file in status_path.glob("*.json"):
                    pattern_data = json.loads(pattern_file.read_text())
                    pattern_id = pattern_data.get("id", pattern_file.stem)

                    existing = eri_patterns["drift_patterns"].get(pattern_id, {})
                    if pattern_data.get("confidence", 0) > existing.get("confidence", 0):
                        eri_patterns["drift_patterns"][pattern_id] = {
                            "name": pattern_data.get("name"),
                            "category": pattern_data.get("category"),
                            "confidence": pattern_data.get("confidence"),
                            "status": status_dir,
                            "file_count": pattern_data.get("fileCount", 0),
                            "source": "drift"
                        }
                        imported += 1

    eri_path.parent.mkdir(parents=True, exist_ok=True)
    eri_path.write_text(json.dumps(eri_patterns, indent=2))

    return imported

def _export_to_drift(eri_path: Path, drift_path: Path) -> int:
    """Export EriRPG patterns to Drift-compatible format."""
    if not eri_path.exists():
        return 0

    eri_patterns = json.loads(eri_path.read_text())
    exported = 0

    custom_dir = drift_path / "patterns" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    for ext in eri_patterns.get("extension_points", []):
        pattern_id = f"eri-extension-{ext['name'].lower().replace(' ', '-')}"
        pattern_data = {
            "id": pattern_id,
            "name": f"Extension Point: {ext['name']}",
            "category": "structural",
            "confidence": 0.8,
            "source": "erirpg",
            "baseClass": ext.get("base_class"),
            "methodSignatures": ext.get("method_signatures", []),
            "locations": ext.get("locations", [])
        }

        pattern_file = custom_dir / f"{pattern_id}.json"
        pattern_file.write_text(json.dumps(pattern_data, indent=2))
        exported += 1

    for reg in eri_patterns.get("registries", []):
        pattern_id = f"eri-registry-{reg['name'].lower().replace(' ', '-')}"
        pattern_data = {
            "id": pattern_id,
            "name": f"Registry: {reg['name']}",
            "category": "structural",
            "confidence": 0.85,
            "source": "erirpg",
            "registryType": reg.get("pattern"),
            "location": reg.get("file")
        }

        pattern_file = custom_dir / f"{pattern_id}.json"
        pattern_file.write_text(json.dumps(pattern_data, indent=2))
        exported += 1

    return exported

def get_combined_confidence(project_path: str, pattern_type: str) -> float:
    """
    Get combined confidence from both EriRPG and Drift.
    Weights: Drift 0.6 (more comprehensive), EriRPG 0.4 (project-specific)
    """
    from .drift_bridge import DriftBridge

    eri_path = Path(project_path) / ".eri-rpg" / "patterns.json"

    eri_conf = 0.0
    drift_conf = 0.0

    if eri_path.exists():
        patterns = json.loads(eri_path.read_text())
        for ext in patterns.get("extension_points", []):
            if pattern_type.lower() in ext.get("name", "").lower():
                eri_conf = 0.8
                break

    bridge = DriftBridge(project_path)
    if bridge.is_available():
        drift_conf = bridge.get_confidence_for_pattern(pattern_type)

    if drift_conf > 0 and eri_conf > 0:
        return (drift_conf * 0.6) + (eri_conf * 0.4)
    elif drift_conf > 0:
        return drift_conf
    elif eri_conf > 0:
        return eri_conf
    else:
        return 0.0
```

### Deliverables
- [ ] Create `erirpg/pattern_sync.py`
- [ ] Implement `_import_from_drift()` - Drift → EriRPG
- [ ] Implement `_export_to_drift()` - EriRPG → Drift
- [ ] Add `get_combined_confidence()` for weighted scoring
- [ ] CLI command: `eri sync-patterns [--direction both|to_drift|from_drift]`

---

## Phase 5: MCP Integration (Future)

**Goal:** Call Drift tools directly via MCP instead of CLI

| EriRPG Need | Drift MCP Tool |
|-------------|----------------|
| Get patterns | `drift_patterns_list` |
| File patterns | `drift_file_patterns` |
| Impact analysis | `drift_impact_analysis` |
| Validate change | `drift_validate_change` |
| Find outliers | `drift_check` |
| Get examples | `drift_code_examples` |

---

## Implementation Order

```
Phase 1: drift_bridge.py
  - DriftBridge class with CLI wrappers
  - `eri drift-status` command

Phase 2: StoredLearning
  - Add Drift fields (confidence, outlier, validated)
  - enrich_with_drift() method
  - `eri enrich-learnings` command

Phase 3: Pre-Implement
  - Impact analysis in planning
  - Risk assessment in FilePlan
  - Optional hook integration

Phase 4: Pattern Sync
  - Bidirectional sync
  - Combined confidence scoring
  - `eri sync-patterns` command

Phase 5: MCP (Future)
  - Direct tool calls when MCP stable
```

---

## Success Metrics

- [ ] Learnings have confidence scores from Drift
- [ ] Implementation plans show affected files and risk
- [ ] Patterns sync bidirectionally without data loss
- [ ] Outlier detection prevents anti-pattern learnings
- [ ] Combined confidence > individual confidence accuracy
