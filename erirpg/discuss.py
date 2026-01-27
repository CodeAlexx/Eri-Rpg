"""
Discussion mode for goal clarification.

Before generating a spec, discuss mode asks clarifying questions
to help refine vague or complex goals into concrete specs.

Key functions:
- needs_discussion(): Determines if a goal needs discussion
- generate_questions(): Creates clarifying questions
- start_discussion(): Creates a Discussion in KnowledgeStore
- answer_question(): Records an answer
- resolve_discussion(): Marks discussion complete
- enrich_goal(): Adds discussion context to goal for spec generation
"""

import os
import hashlib
from typing import List, Optional, Tuple

from erirpg.memory import (
    Discussion,
    KnowledgeStore,
    load_knowledge,
    save_knowledge,
)
from erirpg.registry import Registry


# ============================================================================
# Detection Functions
# ============================================================================

def count_project_files(project_path: str) -> int:
    """Count source files in project (excluding hidden/build dirs)."""
    count = 0
    skip_dirs = {".git", ".eri-rpg", "__pycache__", "node_modules", "target", "build", "dist", ".venv", "venv"}
    
    for root, dirs, files in os.walk(project_path):
        # Skip hidden and build directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        
        for f in files:
            if f.endswith((".py", ".rs", ".c", ".h", ".js", ".ts", ".go")):
                count += 1
                
        # Early exit if we've found enough files
        if count > 100:
            return count
            
    return count


def is_new_project(project_path: str, threshold: int = 5) -> bool:
    """Check if project is new (few source files)."""
    return count_project_files(project_path) < threshold


def is_vague_goal(goal: str) -> bool:
    """Check if goal is vague and needs clarification.
    
    Vague indicators:
    - Short goals (under 20 chars) 
    - Contains vague words like "improve", "fix", "refactor" without specifics
    - Missing concrete targets (no file names, function names, etc.)
    """
    goal_lower = goal.lower()
    
    # Very short goals are often vague
    if len(goal) < 20:
        return True
    
    # Vague action words without specifics
    vague_words = ["improve", "fix", "refactor", "update", "change", "modify", "enhance", "optimize"]
    has_vague_word = any(word in goal_lower for word in vague_words)
    
    # Check for specifics that make it less vague
    specific_indicators = [
        ".py", ".rs", ".c", ".js", ".ts",  # File references
        "()", "function", "method", "class",  # Code references
        "error", "bug", "crash", "fail",  # Specific problems
        "add", "create", "implement", "remove",  # Concrete actions
    ]
    has_specifics = any(indicator in goal_lower for indicator in specific_indicators)
    
    # Vague if has vague word but no specifics
    if has_vague_word and not has_specifics:
        return True
        
    return False


def needs_discussion(
    goal: str,
    project_path: str,
    force: bool = False,
    skip: bool = False,
) -> Tuple[bool, str]:
    """Determine if a goal needs discussion before spec generation.
    
    Args:
        goal: The user's goal
        project_path: Path to project root
        force: Force discussion even if not needed
        skip: Skip discussion even if needed
        
    Returns:
        (needs_discussion, reason) tuple
    """
    if skip:
        return False, "Discussion skipped via --skip flag"
        
    if force:
        return True, "Discussion forced via --discuss flag"
    
    # Check for vague goal
    if is_vague_goal(goal):
        return True, "Goal appears vague - needs clarification"
    
    # Check for new project (few files)
    if is_new_project(project_path):
        return True, "New project - needs to understand structure"
    
    return False, "Goal is specific enough"


# ============================================================================
# Question Generation
# ============================================================================

def generate_questions(
    goal: str,
    project_path: str,
    project_name: str,
) -> List[str]:
    """Generate clarifying questions for a goal.
    
    Questions depend on:
    - Goal type (add, modify, fix, etc.)
    - Project state (new vs existing)
    - Goal specificity
    
    Returns:
        List of questions to ask
    """
    questions = []
    goal_lower = goal.lower()
    
    # Detect goal type
    is_add = any(w in goal_lower for w in ["add", "create", "implement", "new"])
    is_fix = any(w in goal_lower for w in ["fix", "bug", "error", "crash"])
    is_refactor = any(w in goal_lower for w in ["refactor", "improve", "optimize", "enhance"])
    is_transplant = any(w in goal_lower for w in ["transplant", "from", "copy"])
    
    # Project state questions
    if is_new_project(project_path):
        questions.append("What is the main purpose of this project?")
        questions.append("What language/framework patterns should we follow?")
    
    # Goal-type specific questions
    if is_add:
        questions.append("What specific behavior should this feature have?")
        questions.append("Where should this feature be integrated?")
        questions.append("Are there existing patterns to follow?")
        
    elif is_fix:
        questions.append("What is the expected behavior?")
        questions.append("What is the actual behavior (error message, etc.)?")
        questions.append("Can you provide steps to reproduce?")
        
    elif is_refactor:
        questions.append("What specific aspect should be improved?")
        questions.append("Are there constraints (backwards compatibility, etc.)?")
        questions.append("What's the success criteria for this refactor?")
        
    elif is_transplant:
        questions.append("Which specific functions/classes should be transplanted?")
        questions.append("How should it integrate with existing code?")
        questions.append("Are there configuration changes needed?")
    
    else:
        # Generic questions for unrecognized goal types
        questions.append("Can you provide more details about what you want?")
        questions.append("What's the expected outcome?")
        questions.append("Are there any constraints or requirements?")
    
    # Limit to 3-5 questions
    return questions[:5]


# ============================================================================
# Discussion Lifecycle
# ============================================================================

def start_discussion(
    goal: str,
    project_path: str,
    project_name: str,
) -> Discussion:
    """Start a new discussion for a goal.
    
    Creates Discussion object and stores in KnowledgeStore.
    
    Returns:
        The created Discussion
    """
    questions = generate_questions(goal, project_path, project_name)
    discussion = Discussion.create(goal, questions)
    
    # Store in KnowledgeStore
    store = load_knowledge(project_path, project_name)
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return discussion


def get_or_start_discussion(
    goal: str,
    project_path: str,
    project_name: str,
) -> Tuple[Discussion, bool]:
    """Get existing discussion or start a new one.
    
    Returns:
        (Discussion, is_new) - discussion and whether it was newly created
    """
    store = load_knowledge(project_path, project_name)
    existing = store.get_discussion_by_goal(goal)
    
    if existing and not existing.resolved:
        return existing, False
    
    # Start new discussion
    discussion = start_discussion(goal, project_path, project_name)
    return discussion, True


def answer_question(
    goal: str,
    project_path: str,
    project_name: str,
    question: str,
    answer: str,
) -> Discussion:
    """Record an answer to a question.
    
    Returns:
        Updated Discussion
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")
    
    discussion.answer(question, answer)
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return discussion


def resolve_discussion(
    goal: str,
    project_path: str,
    project_name: str,
) -> Discussion:
    """Mark a discussion as resolved.
    
    Returns:
        The resolved Discussion
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")
    
    discussion.resolve()
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return discussion


# ============================================================================
# Goal Enrichment
# ============================================================================

def enrich_goal(
    goal: str,
    project_path: str,
    project_name: str,
) -> str:
    """Enrich a goal with discussion context.
    
    Combines the original goal with answers from discussion
    to create a more detailed, specific goal for spec generation.
    
    Returns:
        Enriched goal string, or original if no discussion
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion or not discussion.answers:
        return goal
    
    # Build enriched goal
    lines = [f"Goal: {goal}", "", "Context from discussion:"]
    
    for question, answer in discussion.answers.items():
        lines.append(f"- {question}")
        lines.append(f"  Answer: {answer}")
    
    return "\n".join(lines)


def get_enriched_goal(
    goal: str,
    project_path: str,
    project_name: str,
) -> Tuple[str, Optional[Discussion]]:
    """Get enriched goal and discussion if exists.
    
    Returns:
        (enriched_goal, discussion) - enriched goal and discussion or None
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    enriched = enrich_goal(goal, project_path, project_name)
    
    return enriched, discussion


# ============================================================================
# CLI Helpers
# ============================================================================

def format_discussion(discussion: Discussion) -> str:
    """Format discussion for CLI display."""
    lines = [
        f"Discussion: {discussion.id[:8]}",
        f"Goal: {discussion.goal}",
        f"Status: {'Resolved' if discussion.resolved else 'In Progress'}",
        f"Created: {discussion.created_at.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    
    if discussion.questions:
        lines.append("Questions:")
        for i, q in enumerate(discussion.questions, 1):
            answer = discussion.answers.get(q, "(unanswered)")
            status = "✓" if q in discussion.answers else "○"
            lines.append(f"  {status} {i}. {q}")
            if q in discussion.answers:
                lines.append(f"      → {answer}")
    
    unanswered = discussion.unanswered()
    if unanswered:
        lines.append(f"\nNext: Answer question #{discussion.questions.index(unanswered[0]) + 1}")
    elif not discussion.resolved:
        lines.append("\nAll questions answered. Run 'eri-rpg discuss-resolve' to complete.")
    
    return "\n".join(lines)
