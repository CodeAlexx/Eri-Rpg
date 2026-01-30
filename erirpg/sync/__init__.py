"""
EriRPG Sync - MD↔JSON synchronization.

ROADMAP.md and STATE.md are sources of truth (human-editable).
roadmap.json and state.json are auto-generated for Claude to read.

Usage:
    from erirpg.sync import sync_roadmap, sync_state

    # After editing ROADMAP.md:
    sync_roadmap(project_path)  # Regenerates roadmap.json

    # After editing STATE.md:
    sync_state(project_path)    # Regenerates state.json

    # For imports (when you have JSON and need MD):
    roadmap_json_to_md(project_path)  # Regenerates ROADMAP.md from roadmap.json
"""

from erirpg.sync.md_to_json import (
    parse_roadmap_md,
    parse_state_md,
    sync_roadmap,
    sync_state,
    sync_all,
)
from erirpg.sync.json_to_md import (
    roadmap_to_md,
    state_to_md,
    roadmap_json_to_md,
    state_json_to_md,
)

__all__ = [
    # MD → JSON
    "parse_roadmap_md",
    "parse_state_md",
    "sync_roadmap",
    "sync_state",
    "sync_all",
    # JSON → MD
    "roadmap_to_md",
    "state_to_md",
    "roadmap_json_to_md",
    "state_json_to_md",
]
