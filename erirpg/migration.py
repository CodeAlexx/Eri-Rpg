"""
Migration utilities for EriRPG storage format.

Handles migration from v1 (knowledge embedded in graph.json) to
v2 (knowledge in separate knowledge.json with CodeRefs).
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from erirpg.refs import CodeRef
from erirpg.memory import (
    KnowledgeStore,
    StoredLearning,
    StoredDecision,
    get_knowledge_path,
)


def check_migration_needed(project_path: str) -> Tuple[bool, str]:
    """Check if migration is needed for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Tuple of (needs_migration: bool, reason: str)
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    if not os.path.exists(graph_path):
        return False, "No graph.json found"

    # Check if knowledge.json already exists
    if os.path.exists(knowledge_path):
        return False, "Already migrated (knowledge.json exists)"

    # Check if graph.json has embedded knowledge
    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        return False, "No knowledge in graph.json to migrate"

    knowledge = data["knowledge"]
    has_content = any([
        knowledge.get("learnings"),
        knowledge.get("decisions"),
        knowledge.get("patterns"),
        knowledge.get("history"),
    ])

    if not has_content:
        return False, "Knowledge section is empty"

    return True, "Knowledge found in graph.json, ready to migrate"


def migrate_knowledge(
    project_path: str,
    project_name: str,
    create_refs: bool = True,
    backup: bool = True,
) -> dict:
    """Migrate knowledge from graph.json to knowledge.json.

    This is the main migration function. It:
    1. Reads knowledge from graph.json
    2. Creates CodeRefs for learnings (if files exist)
    3. Writes to knowledge.json
    4. Optionally backs up old graph.json

    Args:
        project_path: Root path of the project
        project_name: Name of the project
        create_refs: If True, create CodeRefs for learnings
        backup: If True, backup graph.json before migration

    Returns:
        Dict with migration results:
        - migrated: bool
        - learnings: int (count migrated)
        - decisions: int (count migrated)
        - patterns: int (count migrated)
        - refs_created: int (CodeRefs created)
        - refs_failed: int (files not found for refs)
        - error: str (if migration failed)
    """
    result = {
        "migrated": False,
        "learnings": 0,
        "decisions": 0,
        "patterns": 0,
        "refs_created": 0,
        "refs_failed": 0,
        "error": None,
    }

    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    # Check preconditions
    if not os.path.exists(graph_path):
        result["error"] = "No graph.json found"
        return result

    if os.path.exists(knowledge_path):
        result["error"] = "knowledge.json already exists, skipping migration"
        return result

    # Load graph.json
    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        result["error"] = "No knowledge in graph.json to migrate"
        return result

    old_knowledge = data["knowledge"]

    # Backup graph.json
    if backup:
        backup_path = graph_path + ".v1.backup"
        shutil.copy(graph_path, backup_path)

    # Create new knowledge store
    store = KnowledgeStore(project=project_name)

    # Migrate learnings
    for module_path, learning_data in old_knowledge.get("learnings", {}).items():
        # Create CodeRef if file exists
        source_ref = None
        if create_refs:
            try:
                source_ref = CodeRef.from_file(project_path, module_path)
                result["refs_created"] += 1
            except FileNotFoundError:
                result["refs_failed"] += 1
                # Still migrate the learning, just without a ref

        # Create stored learning
        stored = StoredLearning(
            module_path=module_path,
            learned_at=datetime.fromisoformat(learning_data["learned_at"]),
            summary=learning_data.get("summary", ""),
            purpose=learning_data.get("purpose", ""),
            key_functions=learning_data.get("key_functions", {}),
            key_params=learning_data.get("key_params", {}),
            gotchas=learning_data.get("gotchas", []),
            dependencies=learning_data.get("dependencies", []),
            transplanted_to=learning_data.get("transplanted_to"),
            source_ref=source_ref,
            confidence=learning_data.get("confidence", 1.0),
            version=learning_data.get("version", 1),
        )
        store.add_learning(stored)
        result["learnings"] += 1

    # Migrate decisions
    for decision_data in old_knowledge.get("decisions", []):
        stored = StoredDecision(
            id=decision_data["id"],
            date=datetime.fromisoformat(decision_data["date"]),
            title=decision_data["title"],
            reason=decision_data.get("reason", ""),
            affects=decision_data.get("affects", []),
            alternatives=decision_data.get("alternatives", []),
        )
        store.add_decision(stored)
        result["decisions"] += 1

    # Migrate patterns
    for name, description in old_knowledge.get("patterns", {}).items():
        store.add_pattern(name, description)
        result["patterns"] += 1

    # Note: history entries are NOT migrated as they have a different format
    # in v2 (RunRecord vs HistoryEntry). Old history stays in graph.json.

    # Save new knowledge store
    store.save(knowledge_path)

    result["migrated"] = True
    return result


def remove_embedded_knowledge(project_path: str, backup: bool = True) -> bool:
    """Remove embedded knowledge from graph.json after migration.

    Call this after verifying migration was successful to clean up
    the old embedded knowledge from graph.json.

    Args:
        project_path: Root path of the project
        backup: If True, backup graph.json before modification

    Returns:
        True if successful, False otherwise
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")

    if not os.path.exists(graph_path):
        return False

    with open(graph_path, "r") as f:
        data = json.load(f)

    if "knowledge" not in data:
        return True  # Already clean

    if backup:
        backup_path = graph_path + ".pre-cleanup.backup"
        shutil.copy(graph_path, backup_path)

    del data["knowledge"]

    with open(graph_path, "w") as f:
        json.dump(data, f, indent=2)

    return True


def auto_migrate_if_needed(project_path: str, project_name: str) -> Optional[dict]:
    """Automatically migrate if needed, otherwise return None.

    This is a convenience function that checks if migration is needed
    and performs it if so. Safe to call multiple times.

    Args:
        project_path: Root path of the project
        project_name: Name of the project

    Returns:
        Migration result dict if migration was performed, None otherwise
    """
    needs_migration, reason = check_migration_needed(project_path)

    if not needs_migration:
        return None

    return migrate_knowledge(project_path, project_name)


def get_migration_status(project_path: str) -> dict:
    """Get detailed migration status for a project.

    Args:
        project_path: Root path of the project

    Returns:
        Dict with status information
    """
    graph_path = os.path.join(project_path, ".eri-rpg", "graph.json")
    knowledge_path = get_knowledge_path(project_path)

    status = {
        "graph_exists": os.path.exists(graph_path),
        "knowledge_exists": os.path.exists(knowledge_path),
        "has_embedded_knowledge": False,
        "embedded_learnings": 0,
        "embedded_decisions": 0,
        "embedded_patterns": 0,
        "standalone_learnings": 0,
        "standalone_decisions": 0,
        "standalone_patterns": 0,
        "migration_needed": False,
        "migration_reason": "",
    }

    # Check graph.json
    if status["graph_exists"]:
        with open(graph_path, "r") as f:
            data = json.load(f)
        if "knowledge" in data:
            status["has_embedded_knowledge"] = True
            knowledge = data["knowledge"]
            status["embedded_learnings"] = len(knowledge.get("learnings", {}))
            status["embedded_decisions"] = len(knowledge.get("decisions", []))
            status["embedded_patterns"] = len(knowledge.get("patterns", {}))

    # Check knowledge.json
    if status["knowledge_exists"]:
        with open(knowledge_path, "r") as f:
            data = json.load(f)
        status["standalone_learnings"] = len(data.get("learnings", {}))
        status["standalone_decisions"] = len(data.get("decisions", []))
        status["standalone_patterns"] = len(data.get("patterns", {}))

    # Determine migration status
    needs_migration, reason = check_migration_needed(project_path)
    status["migration_needed"] = needs_migration
    status["migration_reason"] = reason

    return status
