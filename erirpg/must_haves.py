"""
Must-haves validation for plan completeness.

Ensures plans cover all requirements before execution.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from erirpg.agent.plan import Plan, Step


@dataclass
class MustHaves:
    """Requirements that must be satisfied by a plan."""
    goal: str
    observable_truths: List[str] = field(default_factory=list)   # User sees when done
    required_artifacts: List[str] = field(default_factory=list)  # Files that must exist
    required_wiring: List[str] = field(default_factory=list)     # Critical connections
    key_links: List[str] = field(default_factory=list)           # Fragile parts to verify
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "observable_truths": self.observable_truths,
            "required_artifacts": self.required_artifacts,
            "required_wiring": self.required_wiring,
            "key_links": self.key_links,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MustHaves":
        return cls(
            goal=d["goal"],
            observable_truths=d.get("observable_truths", []),
            required_artifacts=d.get("required_artifacts", []),
            required_wiring=d.get("required_wiring", []),
            key_links=d.get("key_links", []),
        )


def validate_plan(plan: Plan, must_haves: MustHaves) -> List[str]:
    """
    Validate that a plan covers all must-haves.
    
    Args:
        plan: The plan to validate
        must_haves: Requirements to check against
        
    Returns:
        List of gaps (empty list = valid plan)
    """
    gaps = []
    
    # Collect all files touched by steps
    files_touched = set()
    for step in plan.steps:
        # Check context_files (files the step will work with)
        files_touched.update(step.context_files)
        # Check files_touched if already executed
        files_touched.update(step.files_touched)
    
    # Collect all step text for keyword matching
    all_step_text = " ".join([
        f"{s.goal} {s.description} {s.action if hasattr(s, 'action') else ''} {s.done_criteria if hasattr(s, 'done_criteria') else ''}"
        for s in plan.steps
    ]).lower()
    
    # Check required artifacts
    for artifact in must_haves.required_artifacts:
        # Check if any step mentions this file
        artifact_lower = artifact.lower()
        if artifact_lower not in all_step_text and artifact not in files_touched:
            # Also check partial matches (e.g., "user.py" matches "models/user.py")
            if not any(artifact_lower in f.lower() for f in files_touched):
                gaps.append(f"Missing artifact: {artifact}")
    
    # Check observable truths have matching done_criteria
    for truth in must_haves.observable_truths:
        truth_lower = truth.lower()
        # Look for matching done_criteria
        found = False
        for step in plan.steps:
            done = getattr(step, 'done_criteria', '') or ''
            if truth_lower in done.lower() or _fuzzy_match(truth_lower, done.lower()):
                found = True
                break
        if not found:
            gaps.append(f"No verification for: {truth}")
    
    # Check key links are mentioned
    for link in must_haves.key_links:
        link_lower = link.lower()
        if link_lower not in all_step_text:
            gaps.append(f"Key link not addressed: {link}")
    
    # Check required wiring
    for wiring in must_haves.required_wiring:
        wiring_lower = wiring.lower()
        if wiring_lower not in all_step_text:
            gaps.append(f"Required wiring missing: {wiring}")
    
    return gaps


def _fuzzy_match(needle: str, haystack: str) -> bool:
    """Check if key words from needle appear in haystack."""
    # Extract significant words (skip common words)
    skip_words = {"the", "a", "an", "is", "are", "can", "should", "must", "will"}
    words = [w for w in needle.split() if w not in skip_words and len(w) > 2]
    
    if not words:
        return False
    
    # Check if majority of words appear
    matches = sum(1 for w in words if w in haystack)
    return matches >= len(words) * 0.6


def derive_must_haves_from_goal(goal: str) -> MustHaves:
    """
    Derive basic must-haves from a goal string.
    
    This is a simple heuristic - CC should enhance this.
    """
    must_haves = MustHaves(goal=goal)
    
    goal_lower = goal.lower()
    
    # Extract file patterns
    import re
    file_patterns = re.findall(r'[\w/]+\.(?:py|ts|js|tsx|jsx|json|yaml|yml|md)', goal)
    must_haves.required_artifacts.extend(file_patterns)
    
    # Common observable truths based on keywords
    if "api" in goal_lower or "endpoint" in goal_lower:
        must_haves.observable_truths.append("API endpoint responds correctly")
        must_haves.key_links.append("route registration")
    
    if "test" in goal_lower:
        must_haves.observable_truths.append("Tests pass")
    
    if "database" in goal_lower or "model" in goal_lower:
        must_haves.observable_truths.append("Data persists correctly")
        must_haves.key_links.append("database connection")
    
    if "auth" in goal_lower or "login" in goal_lower:
        must_haves.observable_truths.append("Authentication works")
        must_haves.key_links.append("session/token handling")
        must_haves.required_wiring.append("auth middleware")
    
    if "ui" in goal_lower or "component" in goal_lower or "frontend" in goal_lower:
        must_haves.observable_truths.append("UI renders correctly")
    
    return must_haves
