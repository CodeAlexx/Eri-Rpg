#!/usr/bin/env python3
"""
/coder:complete-milestone - Archive milestone and tag release.

Usage:
    python -m erirpg.commands.complete_milestone [--json]
    python -m erirpg.commands.complete_milestone --version <version> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from erirpg.coder import ensure_planning_dir, load_config, save_config
from erirpg.coder.git_ops import run_git, get_commit_hash


def complete_milestone(
    version: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Complete current milestone."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "complete-milestone",
        "project": str(project_path),
    }

    try:
        planning_dir = ensure_planning_dir(project_path)
        config = load_config(project_path)

        if not version:
            version = config.get("version", "0.1.0")

        result["version"] = version

        # Create git tag
        try:
            code, stdout, stderr = run_git(["tag", "-a", f"v{version}", "-m", f"Release {version}"])
            if code == 0:
                result["tag"] = f"v{version}"
            else:
                result["tag_error"] = stderr or stdout
        except Exception as e:
            result["tag_error"] = str(e)

        # Create archive entry
        archive_dir = planning_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        commit = get_commit_hash("HEAD")
        archive_path = archive_dir / f"milestone-{version}.md"
        archive_content = f"""---
version: {version}
completed: {datetime.utcnow().isoformat()}Z
commit: {commit}
---

# Milestone {version}

## Summary
[Add milestone summary]

## Phases Completed
[List completed phases]

## Key Achievements
- [Achievement 1]
- [Achievement 2]
"""
        archive_path.write_text(archive_content)
        result["archive_file"] = str(archive_path)

        result["status"] = "completed"
        result["message"] = f"Milestone {version} completed"
        result["next_steps"] = [
            f"Push tag: git push origin v{version}",
            "Run /coder:new-milestone to start next version"
        ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    version = None
    if "--version" in sys.argv:
        idx = sys.argv.index("--version")
        if idx + 1 < len(sys.argv):
            version = sys.argv[idx + 1]

    complete_milestone(version=version, output_json=output_json)


if __name__ == "__main__":
    main()
