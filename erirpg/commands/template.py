#!/usr/bin/env python3
"""
/coder:template - Save as reusable template.

Usage:
    python -m erirpg.commands.template <name> [--json]
    python -m erirpg.commands.template <name> --from <source> [--json]
    python -m erirpg.commands.template --list [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.docs import (
    save_template,
    load_template,
    list_templates,
    create_template_from_file,
)


def template(
    name: Optional[str] = None,
    from_source: Optional[str] = None,
    list_only: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Create or list templates."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "template",
        "project": str(project_path),
    }

    try:
        if list_only:
            templates = list_templates(project_path)
            result["templates"] = templates
            result["count"] = len(templates)

        elif name and from_source:
            source_path = Path(from_source)
            if not source_path.is_absolute():
                source_path = project_path / from_source

            if not source_path.exists():
                result["error"] = f"Source not found: {source_path}"
            else:
                template_info = create_template_from_file(source_path, name, project_path)
                result["name"] = name
                result["source"] = str(source_path)
                result["template"] = template_info
                result["message"] = f"Template '{name}' created"

        elif name:
            # Get existing template
            template_info = load_template(name, project_path)
            if template_info:
                result["name"] = name
                result["template"] = template_info
            else:
                result["error"] = f"Template not found: {name}"

        else:
            result["usage"] = {
                "create": "python -m erirpg.commands.template <name> --from <source>",
                "list": "python -m erirpg.commands.template --list",
                "get": "python -m erirpg.commands.template <name>"
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

    from_source = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            from_source = sys.argv[idx + 1]

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if from_source and from_source in args:
        args.remove(from_source)
    name = args[0] if args else None

    template(name=name, from_source=from_source, list_only=list_only, output_json=output_json)


if __name__ == "__main__":
    main()
