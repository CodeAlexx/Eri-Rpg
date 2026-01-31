#!/usr/bin/env python3
"""
/coder:metrics - Track execution metrics.

Displays execution metrics including:
- Time tracking
- Token usage
- Success rates
- Performance trends

Usage:
    python -m erirpg.commands.metrics [--json]
    python -m erirpg.commands.metrics --session [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional

from erirpg.coder.metrics import (
    get_execution_metrics,
    get_session_metrics,
    get_historical_trends,
)


def metrics(
    session_only: bool = False,
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
        if session_only:
            # Current session metrics only
            session = get_session_metrics(project_path)
            result["session"] = session
        else:
            # All metrics
            execution = get_execution_metrics(project_path)
            session = get_session_metrics(project_path)
            trends = get_historical_trends(project_path)

            result["execution"] = execution
            result["session"] = session
            result["trends"] = trends

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    session_only = "--session" in sys.argv

    metrics(session_only=session_only, output_json=output_json)


if __name__ == "__main__":
    main()
