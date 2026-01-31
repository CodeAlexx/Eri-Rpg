#!/usr/bin/env python3
"""
/coder:learn - Pattern extraction to knowledge graph.

Usage:
    python -m erirpg.commands.learn <pattern-description> [--json]
    python -m erirpg.commands.learn --from <file> [--json]
    python -m erirpg.commands.learn --list [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.knowledge import (
    add_pattern,
    search_knowledge,
    get_knowledge_summary,
    import_from_phase,
)


def learn(
    pattern_description: Optional[str] = None,
    from_file: Optional[str] = None,
    list_only: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Learn and store patterns."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "learn",
        "project": str(project_path),
    }

    try:
        if list_only:
            # Show knowledge summary
            summary = get_knowledge_summary(project_path)
            result["summary"] = summary

        elif from_file:
            # Import patterns from file
            file_path = Path(from_file)
            if not file_path.is_absolute():
                file_path = project_path / from_file

            if not file_path.exists():
                result["error"] = f"File not found: {file_path}"
            else:
                # Try to import from phase summary
                imported = import_from_phase(file_path, project_path)
                result["source"] = str(file_path)
                result["imported"] = imported
                result["message"] = f"Imported patterns from {file_path.name}"

        elif pattern_description:
            # Store manually described pattern
            # Use first few words as name, rest as description
            words = pattern_description.split()
            name = " ".join(words[:3]) if len(words) > 3 else pattern_description
            stored = add_pattern(name, pattern_description, project_path=project_path)
            result["stored"] = stored
            result["message"] = "Pattern stored in knowledge base"

        else:
            # Show help and summary
            summary = get_knowledge_summary(project_path)
            result["summary"] = summary
            result["usage"] = {
                "add": "python -m erirpg.commands.learn '<pattern description>'",
                "import": "python -m erirpg.commands.learn --from <file>",
                "list": "python -m erirpg.commands.learn --list"
            }

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    list_only = "--list" in sys.argv

    from_file = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            from_file = sys.argv[idx + 1]

    pattern_description = None
    if not from_file and not list_only:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            pattern_description = " ".join(args)

    learn(pattern_description=pattern_description, from_file=from_file, list_only=list_only, output_json=output_json)


if __name__ == "__main__":
    main()
