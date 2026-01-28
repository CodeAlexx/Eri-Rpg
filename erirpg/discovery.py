"""
Discovery level detection for research pipeline.

Determines how much research is needed based on goal keywords and dependencies.
"""

import re
from typing import Optional, Set, Tuple

# Keywords that indicate architectural/deep research needed
ARCH_KEYWORDS = {"architecture", "redesign", "migrate", "infrastructure", "rewrite", "refactor major"}

# Keywords that indicate integration work
INTEGRATION_KEYWORDS = {"oauth", "database", "redis", "docker", "kubernetes", "aws", "api", "webhook"}

# Keywords that indicate simple internal work (skip research)
SKIP_KEYWORDS = {"fix bug", "typo", "rename", "format", "lint", "comment", "docstring"}

# Regex for extracting known dependencies/libraries from goal text
DEP_PATTERN = re.compile(
    r'\b(fastapi|flask|django|sqlalchemy|redis|postgres|postgresql|mysql|sqlite|'
    r'pytest|docker|aws|oauth|celery|rabbitmq|kafka|mongodb|elasticsearch|'
    r'graphql|grpc|websocket|jwt|stripe|twilio|sendgrid|numpy|pandas|'
    r'tensorflow|pytorch|transformers|pydantic|httpx|aiohttp|asyncio)\b',
    re.IGNORECASE
)

# Phrases that indicate user wants Claude to decide
DISCRETION_PHRASES = [
    "you decide", "your call", "whatever", "up to you",
    "doesn't matter", "don't care", "either", "any is fine",
    "whatever you think", "your choice", "dealer's choice"
]


def extract_deps(text: str) -> Set[str]:
    """
    Extract known library/framework dependencies from text.
    
    Args:
        text: Goal or description text to scan
        
    Returns:
        Set of lowercase dependency names found
    """
    matches = DEP_PATTERN.findall(text)
    return {m.lower() for m in matches}


def detect_discovery_level(
    goal: str,
    known_deps: Optional[Set[str]] = None
) -> Tuple[int, str]:
    """
    Detect how much research is needed for a goal.
    
    Args:
        goal: The task/goal description
        known_deps: Dependencies already known to the project (from pyproject.toml etc)
        
    Returns:
        Tuple of (level, reason) where:
        - 0 = skip (internal work, no research needed)
        - 1 = quick (single library lookup)
        - 2 = standard (choosing between options)
        - 3 = deep (architectural decisions)
    """
    goal_lower = goal.lower()
    known_deps = known_deps or set()
    
    # Check for skip keywords first
    if any(kw in goal_lower for kw in SKIP_KEYWORDS):
        return (0, "skip keyword detected")
    
    # Check for architectural keywords
    if any(kw in goal_lower for kw in ARCH_KEYWORDS):
        return (3, "architectural change")
    
    # Extract new dependencies
    mentioned_deps = extract_deps(goal)
    new_deps = mentioned_deps - known_deps
    
    # Check for integration keywords
    if any(kw in goal_lower for kw in INTEGRATION_KEYWORDS):
        if new_deps:
            return (2, f"integration with new deps: {', '.join(new_deps)}")
        else:
            return (1, "integration with known deps")
    
    # Check dependency count
    if len(new_deps) > 2:
        return (2, f"multiple new deps: {', '.join(new_deps)}")
    if len(new_deps) == 1:
        return (1, f"single new dep: {list(new_deps)[0]}")
    
    return (0, "no research indicators")


def is_discretion_answer(answer: str) -> bool:
    """
    Check if user's answer indicates they want Claude to decide.
    
    Args:
        answer: User's response to a question
        
    Returns:
        True if user wants Claude to use discretion
    """
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in DISCRETION_PHRASES)


def get_level_description(level: int) -> str:
    """Get human-readable description of discovery level."""
    descriptions = {
        0: "Skip - No research needed (internal work)",
        1: "Quick - Single library lookup",
        2: "Standard - Compare options and choose",
        3: "Deep - Architectural research required"
    }
    return descriptions.get(level, f"Unknown level: {level}")
