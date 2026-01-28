"""Data loading helpers for EriRPG UI."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_PATH = Path.home() / ".eri-rpg" / "registry.json"


def load_registry() -> Dict[str, Any]:
    """Load the global project registry."""
    try:
        if REGISTRY_PATH.exists():
            return json.loads(REGISTRY_PATH.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {"projects": {}}


def get_project(name: str) -> Optional[Dict[str, Any]]:
    """Get a project from registry by name."""
    registry = load_registry()
    return registry.get("projects", {}).get(name)


def get_project_path(name: str) -> Optional[Path]:
    """Get project path from registry."""
    project = get_project(name)
    if project:
        return Path(project.get("path", ""))
    return None


def load_state(project_path: str) -> Dict[str, Any]:
    """Load project state.json."""
    try:
        state_file = Path(project_path) / ".eri-rpg" / "state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def load_knowledge(project_path: str) -> Dict[str, Any]:
    """Load project knowledge.json."""
    try:
        knowledge_file = Path(project_path) / ".eri-rpg" / "knowledge.json"
        if knowledge_file.exists():
            return json.loads(knowledge_file.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {"learnings": {}, "decisions": [], "patterns": {}}


def load_graph(project_path: str) -> Dict[str, Any]:
    """Load project dependency graph."""
    try:
        graph_file = Path(project_path) / ".eri-rpg" / "graph.json"
        if graph_file.exists():
            return json.loads(graph_file.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {"nodes": [], "edges": []}


def load_runs(project_path: str) -> List[Dict[str, Any]]:
    """Load all runs from project runs directory."""
    runs = []
    runs_dir = Path(project_path) / ".eri-rpg" / "runs"
    if not runs_dir.exists():
        return runs

    for run_file in runs_dir.glob("*.json"):
        try:
            run_data = json.loads(run_file.read_text())
            run_data["_id"] = run_file.stem
            runs.append(run_data)
        except (json.JSONDecodeError, IOError):
            pass

    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return runs


def load_roadmap(project_path: str) -> Optional[str]:
    """Load project roadmap markdown."""
    try:
        roadmap_file = Path(project_path) / ".planning" / "ROADMAP.md"
        if roadmap_file.exists():
            return roadmap_file.read_text()
    except IOError:
        pass
    return None


def count_modules(project_path: str) -> int:
    """Count nodes in dependency graph."""
    graph = load_graph(project_path)
    nodes = graph.get("nodes", [])
    return len(nodes) if isinstance(nodes, (list, dict)) else 0


def load_config(project_path: str) -> Dict[str, Any]:
    """Load project config.json."""
    try:
        config_file = Path(project_path) / ".eri-rpg" / "config.json"
        if config_file.exists():
            return json.loads(config_file.read_text())
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def get_project_mode(project_path: str) -> str:
    """Get project operational mode (bootstrap or maintain).

    Handles migration: projects with learnings default to maintain.
    """
    config = load_config(project_path)

    # If mode is explicitly set, use it
    if "mode" in config:
        return config["mode"]

    # Migration: check if project has learnings
    knowledge = load_knowledge(project_path)
    if knowledge.get("learnings"):
        return "maintain"

    # Default for new/empty projects
    return "bootstrap"


def count_learned(project_path: str) -> int:
    """Count entries in knowledge.learnings."""
    knowledge = load_knowledge(project_path)
    return len(knowledge.get("learnings", {}))


def check_staleness(project_path: str, file_path: str, source_ref: Dict) -> bool:
    """Check if a learning is stale."""
    if not source_ref:
        return False
    try:
        full_path = Path(project_path) / file_path
        if not full_path.exists():
            return True
        current_mtime = full_path.stat().st_mtime
        learned_mtime = source_ref.get("mtime", 0)
        return current_mtime > learned_mtime
    except (IOError, OSError):
        return False


def format_relative_time(timestamp: float) -> str:
    """Format timestamp as relative time."""
    now = datetime.now().timestamp()
    diff = now - timestamp
    if diff < 60:
        return "now"
    elif diff < 3600:
        return f"{int(diff / 60)}m ago"
    elif diff < 86400:
        return f"{int(diff / 3600)}h ago"
    else:
        return f"{int(diff / 86400)}d ago"


def get_last_active(project_path: str) -> Optional[str]:
    """Get timestamp of last activity."""
    mtimes = []
    for name in ["state.json", "knowledge.json"]:
        f = Path(project_path) / ".eri-rpg" / name
        try:
            if f.exists():
                mtimes.append(f.stat().st_mtime)
        except OSError:
            pass
    if mtimes:
        return format_relative_time(max(mtimes))
    return None


def get_git_log(project_path: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get git log for project."""
    commits = []
    try:
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--pretty=format:%H|%h|%s|%ar|%an"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 4)
                if len(parts) >= 4:
                    msg = parts[2] if len(parts) > 2 else ""
                    commits.append({
                        "hash": parts[0], "short_hash": parts[1],
                        "message": msg, "time": parts[3],
                        "author": parts[4] if len(parts) > 4 else "",
                        "is_erirpg": "eri-rpg" in msg.lower()
                    })
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    return commits


def get_drift_status(project_path: str) -> Dict[str, Any]:
    """Get Drift integration status."""
    drift_dir = Path(project_path) / ".drift"
    status = {"available": drift_dir.exists(), "patterns": [], "outliers": [],
              "enriched_count": 0, "total_learnings": 0}
    if not drift_dir.exists():
        return status

    patterns_dir = drift_dir / "patterns"
    if patterns_dir.exists():
        for status_dir in ["approved", "discovered"]:
            status_path = patterns_dir / status_dir
            if status_path.exists():
                for pf in status_path.glob("*.json"):
                    try:
                        p = json.loads(pf.read_text())
                        p["_status"] = status_dir
                        status["patterns"].append(p)
                    except (json.JSONDecodeError, IOError):
                        pass

    knowledge = load_knowledge(project_path)
    learnings = knowledge.get("learnings", {})
    status["total_learnings"] = len(learnings)
    for path, data in learnings.items():
        if data.get("drift_pattern_id") or data.get("validated_by_drift"):
            status["enriched_count"] += 1
        if data.get("is_outlier"):
            status["outliers"].append(path)
    return status


def get_all_projects() -> List[Dict[str, Any]]:
    """Get all projects with stats."""
    registry = load_registry()
    projects = []
    for name, data in registry.get("projects", {}).items():
        path = data.get("path", "")
        config = load_config(path)
        mode = get_project_mode(path)
        projects.append({
            "name": name, "path": path,
            "description": data.get("description", ""),
            "modules": count_modules(path),
            "learned": count_learned(path),
            "last_active": get_last_active(path),
            "mode": mode,
            "graduated_at": config.get("graduated_at"),
        })
    projects.sort(key=lambda p: p.get("last_active") or "zzz")
    return projects


def get_active_task() -> Optional[Dict[str, Any]]:
    """Find currently active task across all projects."""
    registry = load_registry()
    for name, data in registry.get("projects", {}).items():
        path = data.get("path", "")
        state = load_state(path)
        phase = state.get("phase", "idle")
        if phase and phase != "idle":
            return {
                "project": name, "project_path": path,
                "task": state.get("current_task", ""),
                "phase": phase,
                "waiting_on": state.get("waiting_on", ""),
                "context_file": state.get("context_file"),
                "history": state.get("history", [])[-15:]
            }
    return None
