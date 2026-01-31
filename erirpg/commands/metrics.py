#!/usr/bin/env python3
"""
/coder:metrics - Track execution metrics.

Usage:
    python -m erirpg.commands.metrics [--json]
    python -m erirpg.commands.metrics --summary [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.metrics import load_metrics, get_metrics_summary


def metrics(
    summary_only: bool = False,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Get execution metrics."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "metrics",
        "project": str(project_path),
    }

    try:
        if summary_only:
            summary = get_metrics_summary(project_path)
            result["summary"] = summary
        else:
            all_metrics = load_metrics(project_path)
            summary = get_metrics_summary(project_path)
            result["metrics"] = all_metrics
            result["summary"] = summary

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    summary_only = "--summary" in sys.argv

    metrics(summary_only=summary_only, output_json=output_json)


if __name__ == "__main__":
    main()
