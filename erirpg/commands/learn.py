#!/usr/bin/env python3
"""
/coder:learn - Pattern extraction to knowledge graph.

Extracts patterns from code and stores them in knowledge base.

Usage:
    python -m erirpg.commands.learn <pattern-description> [--json]
    python -m erirpg.commands.learn --from <file> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.knowledge import (
    store_pattern,
    extract_patterns_from_file,
    get_knowledge_stats,
)


def learn(
    pattern_description: Optional[str] = None,
    from_file: Optional[str] = None,
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
        if from_file:
            # Extract patterns from file
            file_path = Path(from_file)
            if not file_path.is_absolute():
                file_path = project_path / from_file

            if not file_path.exists():
                result["error"] = f"File not found: {file_path}"
            else:
                patterns = extract_patterns_from_file(file_path)
                result["source"] = str(file_path)
                result["patterns_found"] = len(patterns)
                result["patterns"] = patterns

        elif pattern_description:
            # Store manually described pattern
            stored = store_pattern(project_path, pattern_description)
            result["stored"] = stored
            result["message"] = "Pattern stored in knowledge base"

        else:
            # Show knowledge stats
            stats = get_knowledge_stats(project_path)
            result["stats"] = stats
            result["usage"] = {
                "describe": "python -m erirpg.commands.learn '<pattern description>'",
                "from_file": "python -m erirpg.commands.learn --from <file>"
            }

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Parse --from argument
    from_file = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            from_file = sys.argv[idx + 1]

    # Get pattern description (non-flag arguments)
    pattern_description = None
    if not from_file:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if args:
            pattern_description = " ".join(args)

    learn(
        pattern_description=pattern_description,
        from_file=from_file,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
