"""
Search functionality for EriRPG knowledge.

Provides keyword-based search over learnings with ranking
by relevance, freshness, and confidence.
"""

import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from erirpg.memory import StoredLearning


def tokenize(text: str) -> Set[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Text to tokenize

    Returns:
        Set of lowercase word tokens
    """
    if not text:
        return set()
    return set(re.findall(r'\w+', text.lower()))


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets.

    Args:
        set1: First set
        set2: Second set

    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def search_learnings(
    learnings: Dict[str, "StoredLearning"],
    query: str,
    limit: int = 10,
    project_path: str = None,
) -> List[Tuple[str, "StoredLearning", float]]:
    """Search learnings by query.

    Scoring components:
    - Path match: 0.2 weight (module path contains query terms)
    - Summary match: 0.3 weight (summary text matches)
    - Purpose match: 0.2 weight (purpose text matches)
    - Functions match: 0.2 weight (function names/descriptions)
    - Gotchas match: 0.1 weight (gotcha text matches)

    Boosted by:
    - Recency: +0.1 for learnings < 7 days old
    - Confidence: multiplied by confidence score
    - Freshness: -0.2 if stale (when project_path provided)

    Args:
        learnings: Dict of module_path -> StoredLearning
        query: Search query (space-separated keywords)
        limit: Maximum results to return
        project_path: Optional project path for staleness checking

    Returns:
        List of (module_path, learning, score) tuples sorted by score
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for module_path, learning in learnings.items():
        score = 0.0

        # Path match (0.2 weight)
        path_tokens = tokenize(module_path.replace("/", " ").replace("_", " "))
        path_score = jaccard_similarity(query_tokens, path_tokens)
        score += path_score * 0.2

        # Exact path substring match bonus
        if query.lower() in module_path.lower():
            score += 0.15

        # Summary match (0.3 weight)
        summary_tokens = tokenize(learning.summary)
        summary_score = jaccard_similarity(query_tokens, summary_tokens)
        score += summary_score * 0.3

        # Exact phrase in summary bonus
        if query.lower() in learning.summary.lower():
            score += 0.2

        # Purpose match (0.2 weight)
        purpose_tokens = tokenize(learning.purpose)
        purpose_score = jaccard_similarity(query_tokens, purpose_tokens)
        score += purpose_score * 0.2

        # Functions match (0.2 weight)
        func_text = " ".join(
            f"{name} {desc}"
            for name, desc in learning.key_functions.items()
        )
        func_tokens = tokenize(func_text)
        func_score = jaccard_similarity(query_tokens, func_tokens)
        score += func_score * 0.2

        # Gotchas match (0.1 weight)
        gotcha_text = " ".join(learning.gotchas)
        gotcha_tokens = tokenize(gotcha_text)
        gotcha_score = jaccard_similarity(query_tokens, gotcha_tokens)
        score += gotcha_score * 0.1

        # Recency boost
        days_old = (datetime.now() - learning.learned_at).days
        if days_old < 7:
            score += 0.1
        elif days_old < 30:
            score += 0.05

        # Confidence multiplier
        score *= learning.confidence

        # Staleness penalty
        if project_path and learning.is_stale(project_path):
            score -= 0.2

        if score > 0.01:  # Threshold to filter noise
            results.append((module_path, learning, score))

    # Sort by score descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]


def search_patterns(
    patterns: Dict[str, str],
    query: str,
    limit: int = 10,
) -> List[Tuple[str, str, float]]:
    """Search patterns by query.

    Args:
        patterns: Dict of name -> description
        query: Search query
        limit: Maximum results

    Returns:
        List of (name, description, score) tuples
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for name, description in patterns.items():
        score = 0.0

        # Name match
        name_tokens = tokenize(name.replace("_", " "))
        name_score = jaccard_similarity(query_tokens, name_tokens)
        score += name_score * 0.5

        # Exact name match
        if query.lower() in name.lower():
            score += 0.3

        # Description match
        desc_tokens = tokenize(description)
        desc_score = jaccard_similarity(query_tokens, desc_tokens)
        score += desc_score * 0.5

        if score > 0.01:
            results.append((name, description, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]


def search_decisions(
    decisions: List,
    query: str,
    limit: int = 10,
) -> List[Tuple[int, object, float]]:
    """Search decisions by query.

    Args:
        decisions: List of StoredDecision objects
        query: Search query
        limit: Maximum results

    Returns:
        List of (index, decision, score) tuples
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    results = []

    for i, decision in enumerate(decisions):
        score = 0.0

        # Title match
        title_tokens = tokenize(decision.title)
        title_score = jaccard_similarity(query_tokens, title_tokens)
        score += title_score * 0.4

        # Exact title match
        if query.lower() in decision.title.lower():
            score += 0.2

        # Reason match
        reason_tokens = tokenize(decision.reason)
        reason_score = jaccard_similarity(query_tokens, reason_tokens)
        score += reason_score * 0.4

        # Affects match
        affects_text = " ".join(decision.affects)
        affects_tokens = tokenize(affects_text)
        affects_score = jaccard_similarity(query_tokens, affects_tokens)
        score += affects_score * 0.2

        if score > 0.01:
            results.append((i, decision, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results[:limit]
