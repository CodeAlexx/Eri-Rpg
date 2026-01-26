"""
Auto-learning module.

Automatically captures learnings when the agent reads/writes files.
No manual CLI calls needed.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from erirpg.memory import KnowledgeStore, StoredLearning, load_knowledge, save_knowledge
from erirpg.refs import CodeRef


def auto_learn(
    project_path: str,
    files: List[str],
    step_goal: str,
    notes: str = "",
    project_name: Optional[str] = None,
) -> List[str]:
    """
    Automatically create learnings for touched files.

    Args:
        project_path: Root path of the project
        files: List of file paths (relative to project_path) that were touched
        step_goal: The goal of the step (used to derive purpose)
        notes: Any notes about what was done
        project_name: Project name for knowledge store (default: derived from path)

    Returns:
        List of file paths that were learned
    """
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    # Load existing knowledge
    store = load_knowledge(project_path, project_name)
    learned = []

    for file_path in files:
        full_path = os.path.join(project_path, file_path)
        if not os.path.exists(full_path):
            continue

        # Create CodeRef for staleness tracking
        try:
            source_ref = CodeRef.from_file(project_path, file_path)
        except Exception:
            source_ref = None

        # Check if we already have a learning that's still fresh
        existing = store.get_learning(file_path)
        if existing and source_ref and not existing.is_stale(project_path):
            # Learning is still fresh, skip
            continue

        # Create new learning
        learning = StoredLearning(
            module_path=file_path,
            learned_at=datetime.now(),
            summary=f"Modified during: {step_goal}",
            purpose=step_goal,
            key_functions={},  # Agent can fill this in later
            gotchas=[notes] if notes else [],
            source_ref=source_ref,
        )

        store.add_learning(learning)
        learned.append(file_path)

    # Save updated knowledge
    if learned:
        save_knowledge(project_path, store)

    return learned


def update_learning(
    project_path: str,
    file_path: str,
    summary: Optional[str] = None,
    purpose: Optional[str] = None,
    key_functions: Optional[Dict[str, str]] = None,
    gotchas: Optional[List[str]] = None,
    project_name: Optional[str] = None,
) -> bool:
    """
    Update an existing learning with richer information.

    Called by the agent when it has deeper understanding of a file.

    Returns:
        True if learning was updated, False if not found
    """
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    store = load_knowledge(project_path, project_name)
    existing = store.get_learning(file_path)

    if not existing:
        return False

    # Update fields if provided
    if summary is not None:
        existing.summary = summary
    if purpose is not None:
        existing.purpose = purpose
    if key_functions is not None:
        existing.key_functions = key_functions
    if gotchas is not None:
        existing.gotchas = gotchas

    # Update the ref to current state
    full_path = os.path.join(project_path, file_path)
    if os.path.exists(full_path):
        try:
            existing.source_ref = CodeRef.from_file(project_path, file_path)
        except Exception:
            pass

    existing.learned_at = datetime.now()
    store.add_learning(existing)  # Overwrites existing
    save_knowledge(project_path, store)
    return True


def get_knowledge(
    project_path: str,
    file_path: str,
    project_name: Optional[str] = None,
) -> Optional[StoredLearning]:
    """
    Get stored knowledge for a file.

    Returns None if no knowledge exists or if it's stale.
    """
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    store = load_knowledge(project_path, project_name)
    learning = store.get_learning(file_path)

    if learning and learning.is_stale(project_path):
        # Return with staleness warning
        return learning

    return learning


def is_stale(
    project_path: str,
    file_path: str,
    project_name: Optional[str] = None,
) -> bool:
    """Check if knowledge for a file is stale."""
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    store = load_knowledge(project_path, project_name)
    learning = store.get_learning(file_path)

    if not learning:
        return True  # No knowledge = stale

    return learning.is_stale(project_path)


def get_all_knowledge(
    project_path: str,
    project_name: Optional[str] = None,
) -> Dict[str, StoredLearning]:
    """Get all stored knowledge for a project."""
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    store = load_knowledge(project_path, project_name)
    return {path: store.get_learning(path) for path in store.list_modules() if store.get_learning(path)}


def get_stale_knowledge(
    project_path: str,
    project_name: Optional[str] = None,
) -> List[str]:
    """Get list of files with stale knowledge."""
    if not project_name:
        project_name = os.path.basename(project_path.rstrip("/"))

    store = load_knowledge(project_path, project_name)
    stale = []
    for path in store.list_modules():
        learning = store.get_learning(path)
        if learning and learning.is_stale(project_path):
            stale.append(path)
    return stale
