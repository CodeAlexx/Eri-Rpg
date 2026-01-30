"""
Key link patterns for verifying component connections.

Common patterns:
- Component → API
- API → Database
- Form → Handler
- State → Render
"""

import re
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class LinkPattern:
    """A pattern for detecting component connections."""
    name: str
    description: str
    from_patterns: List[str]  # Patterns to match in 'from' component
    to_patterns: List[str]    # Patterns to match in 'to' component


# Common key link patterns
KEY_LINK_PATTERNS: Dict[str, LinkPattern] = {
    "component_api": LinkPattern(
        name="Component → API",
        description="UI component calls API endpoint",
        from_patterns=[
            r"fetch\s*\(",
            r"axios\.",
            r"useQuery",
            r"useMutation",
            r"\.get\s*\(",
            r"\.post\s*\(",
        ],
        to_patterns=[
            r"@app\.route",
            r"@router\.",
            r"app\.get\s*\(",
            r"app\.post\s*\(",
            r"export\s+async\s+function",
        ],
    ),
    "api_database": LinkPattern(
        name="API → Database",
        description="API endpoint accesses database",
        from_patterns=[
            r"\.query\s*\(",
            r"\.execute\s*\(",
            r"\.find\s*\(",
            r"\.create\s*\(",
            r"\.save\s*\(",
            r"\.delete\s*\(",
            r"SELECT\s+",
            r"INSERT\s+",
            r"UPDATE\s+",
        ],
        to_patterns=[
            r"CREATE\s+TABLE",
            r"class\s+\w+\s*\([^)]*Model",
            r"@Entity",
            r"schema\s*=",
        ],
    ),
    "form_handler": LinkPattern(
        name="Form → Handler",
        description="Form submission connects to handler",
        from_patterns=[
            r"onSubmit",
            r"handleSubmit",
            r"@submit",
            r"action=",
        ],
        to_patterns=[
            r"def\s+\w+.*request",
            r"async\s+function.*req",
            r"\.post\s*\(",
        ],
    ),
    "state_render": LinkPattern(
        name="State → Render",
        description="State changes trigger re-render",
        from_patterns=[
            r"useState",
            r"useReducer",
            r"useContext",
            r"this\.state",
            r"@state",
        ],
        to_patterns=[
            r"return\s*\(",
            r"render\s*\(",
            r"<\w+",
        ],
    ),
    "event_listener": LinkPattern(
        name="Event → Listener",
        description="Event emitter connects to listener",
        from_patterns=[
            r"\.emit\s*\(",
            r"\.dispatch\s*\(",
            r"\.publish\s*\(",
        ],
        to_patterns=[
            r"\.on\s*\(",
            r"\.subscribe\s*\(",
            r"addEventListener",
            r"@listen",
        ],
    ),
    "route_component": LinkPattern(
        name="Route → Component",
        description="Route maps to component",
        from_patterns=[
            r"<Route",
            r"path=",
            r"router\.",
        ],
        to_patterns=[
            r"export\s+default",
            r"export\s+function",
            r"class\s+\w+\s+extends",
        ],
    ),
    "import_export": LinkPattern(
        name="Import → Export",
        description="Module imports another module's exports",
        from_patterns=[
            r"import\s+",
            r"from\s+",
            r"require\s*\(",
        ],
        to_patterns=[
            r"export\s+",
            r"module\.exports",
            r"__all__",
        ],
    ),
}


def detect_link_type(via: str) -> Optional[str]:
    """Detect the type of link from the 'via' description.

    Args:
        via: Description of how components connect

    Returns:
        Link type key or None if not detected
    """
    via_lower = via.lower()

    if any(w in via_lower for w in ["api", "endpoint", "http", "rest"]):
        return "component_api"
    if any(w in via_lower for w in ["database", "db", "sql", "query", "model"]):
        return "api_database"
    if any(w in via_lower for w in ["form", "submit", "handler"]):
        return "form_handler"
    if any(w in via_lower for w in ["state", "render", "update"]):
        return "state_render"
    if any(w in via_lower for w in ["event", "emit", "listen", "subscribe"]):
        return "event_listener"
    if any(w in via_lower for w in ["route", "navigation", "path"]):
        return "route_component"
    if any(w in via_lower for w in ["import", "export", "require", "module"]):
        return "import_export"

    return None


def verify_component_connection(
    project_path: str,
    from_path: str,
    to_path: str,
    link_type: Optional[str] = None,
) -> Tuple[bool, str]:
    """Verify connection between two components.

    Args:
        project_path: Path to project root
        from_path: Path to 'from' component
        to_path: Path to 'to' component
        link_type: Optional specific link type to check

    Returns:
        Tuple of (connected: bool, evidence: str)
    """
    from_full = os.path.join(project_path, from_path)
    to_full = os.path.join(project_path, to_path)

    # Check files exist
    if not os.path.exists(from_full):
        return False, f"Source file not found: {from_path}"
    if not os.path.exists(to_full):
        return False, f"Target file not found: {to_path}"

    # Read contents
    try:
        with open(from_full, "r", errors="replace") as f:
            from_content = f.read()
        with open(to_full, "r", errors="replace") as f:
            to_content = f.read()
    except Exception as e:
        return False, f"Error reading files: {e}"

    # If link type specified, use those patterns
    if link_type and link_type in KEY_LINK_PATTERNS:
        pattern = KEY_LINK_PATTERNS[link_type]

        from_matches = any(re.search(p, from_content) for p in pattern.from_patterns)
        to_matches = any(re.search(p, to_content) for p in pattern.to_patterns)

        if from_matches and to_matches:
            return True, f"Verified via {pattern.name} pattern"
        elif from_matches:
            return False, f"Source has {pattern.name} patterns but target doesn't match"
        else:
            return False, f"Source doesn't have {pattern.name} patterns"

    # Otherwise, try all patterns
    for link_name, pattern in KEY_LINK_PATTERNS.items():
        from_matches = any(re.search(p, from_content) for p in pattern.from_patterns)
        to_matches = any(re.search(p, to_content) for p in pattern.to_patterns)

        if from_matches and to_matches:
            return True, f"Verified via {pattern.name} pattern"

    # Fallback: check for direct import
    to_module = _path_to_module(to_path)
    import_patterns = [
        rf"from\s+.*{re.escape(to_module)}\s+import",
        rf"import\s+.*{re.escape(to_module)}",
        rf"require\s*\(['\"].*{re.escape(os.path.basename(to_path).split('.')[0])}['\"]",
    ]

    if any(re.search(p, from_content) for p in import_patterns):
        return True, "Verified via import"

    return False, "No connection pattern matched"


def _path_to_module(file_path: str) -> str:
    """Convert file path to module name pattern."""
    # Remove extension and convert separators
    path = os.path.splitext(file_path)[0]
    return path.replace(os.sep, ".").replace("/", ".").lstrip(".")


def suggest_link_verification(via: str) -> str:
    """Suggest how to verify a link based on 'via' description.

    Args:
        via: Description of how components connect

    Returns:
        Suggestion for manual verification
    """
    link_type = detect_link_type(via)

    if link_type:
        pattern = KEY_LINK_PATTERNS[link_type]
        return f"Check for {pattern.name}: {pattern.description}"

    return f"Manually verify that the connection via '{via}' exists"


def find_missing_links(
    project_path: str,
    component_path: str,
    expected_connections: List[str],
) -> List[str]:
    """Find expected connections that are missing.

    Args:
        project_path: Path to project root
        component_path: Path to component to check
        expected_connections: List of expected connected components

    Returns:
        List of missing connection paths
    """
    missing = []

    for expected in expected_connections:
        connected, _ = verify_component_connection(
            project_path,
            component_path,
            expected,
        )
        if not connected:
            missing.append(expected)

    return missing
