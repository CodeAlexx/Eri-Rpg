#!/usr/bin/env python3
"""
/coder:template - Save as reusable template.

Creates reusable templates from:
- Phase configurations
- Plan structures
- File scaffolds

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
    create_template,
    list_templates,
    get_template,
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
            # List available templates
            templates = list_templates(project_path)
            result["templates"] = templates
            result["count"] = len(templates)

        elif name and from_source:
            # Create template from source
            source_path = Path(from_source)
            if not source_path.is_absolute():
                source_path = project_path / from_source

            if not source_path.exists():
                result["error"] = f"Source not found: {source_path}"
            else:
                template_info = create_template(project_path, name, source_path)
                result["name"] = name
                result["source"] = str(source_path)
                result["template"] = template_info
                result["message"] = f"Template '{name}' created"

        elif name:
            # Get existing template info
            template_info = get_template(project_path, name)
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

    # Parse --from argument
    from_source = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            from_source = sys.argv[idx + 1]

    # Get name (non-flag arguments)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if from_source and from_source in args:
        args.remove(from_source)
    name = args[0] if args else None

    template(
        name=name,
        from_source=from_source,
        list_only=list_only,
        output_json=output_json
    )


if __name__ == "__main__":
    main()
