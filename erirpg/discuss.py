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
    Milestone,
    Roadmap,
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
    discussion = Discussion.create(goal, questions, project=project_name)
    
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
        f"Project: {discussion.project}" if discussion.project else "",
        f"Status: {'Resolved' if discussion.resolved else 'In Progress'}",
        f"Created: {discussion.created_at.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    # Remove empty lines from missing project
    lines = [l for l in lines if l != ""]
    lines.append("")
    
    if discussion.questions:
        lines.append("Questions:")
        for i, q in enumerate(discussion.questions, 1):
            answer = discussion.answers.get(q, "(unanswered)")
            status = "✓" if q in discussion.answers else "○"
            lines.append(f"  {status} {i}. {q}")
            if q in discussion.answers:
                lines.append(f"      → {answer}")
    
    # Show roadmap if exists
    if discussion.roadmap:
        lines.append("")
        lines.append(format_roadmap(discussion.roadmap))
    
    unanswered = discussion.unanswered()
    if unanswered:
        lines.append(f"\nNext: Answer question #{discussion.questions.index(unanswered[0]) + 1}")
    elif discussion.roadmap is None and not discussion.resolved:
        lines.append("\nQuestions done. Add roadmap with: eri-rpg roadmap-add <project> \"Phase Name\" \"Description\"")
    elif not discussion.resolved:
        lines.append("\nReady. Run 'eri-rpg discuss-resolve' to finalize.")
    
    return "\n".join(lines)


# ============================================================================
# Roadmap Functions
# ============================================================================

def create_roadmap(
    goal: str,
    project_path: str,
    project_name: str,
) -> Roadmap:
    """Create a roadmap for a discussion.
    
    Creates empty roadmap linked to discussion.
    Add milestones with add_milestone().
    
    Returns:
        The created Roadmap
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")
    
    if discussion.roadmap:
        return discussion.roadmap
    
    roadmap = Roadmap.create(goal)
    discussion.roadmap = roadmap
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return roadmap


def add_milestone(
    goal: str,
    project_path: str,
    project_name: str,
    name: str,
    description: str,
) -> Milestone:
    """Add a milestone to a discussion's roadmap.
    
    Creates roadmap if it doesn't exist.
    
    Returns:
        The created Milestone
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")
    
    # Create roadmap if needed
    if not discussion.roadmap:
        discussion.roadmap = Roadmap.create(goal)
    
    milestone = discussion.roadmap.add_milestone(name, description)
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return milestone


def advance_roadmap(
    goal: str,
    project_path: str,
    project_name: str,
) -> Optional[Milestone]:
    """Mark current milestone done and return next one.
    
    Returns:
        Next milestone, or None if roadmap complete
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")
    
    if not discussion.roadmap:
        raise ValueError(f"No roadmap found for goal: {goal}")
    
    next_milestone = discussion.roadmap.advance()
    store.add_discussion(discussion)
    save_knowledge(project_path, store)
    
    return next_milestone


def get_roadmap(
    goal: str,
    project_path: str,
    project_name: str,
) -> Optional[Roadmap]:
    """Get roadmap for a goal.
    
    Returns:
        Roadmap or None if no discussion/roadmap exists
    """
    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)
    
    if not discussion:
        return None
    
    return discussion.roadmap


def get_active_discussion(
    project_path: str,
    project_name: str,
) -> Optional[Discussion]:
    """Get the active (unresolved) discussion for a project.
    
    Returns most recent unresolved discussion.
    
    Returns:
        Discussion or None if no active discussion
    """
    store = load_knowledge(project_path, project_name)
    discussions = store.list_discussions()
    
    for disc in discussions:
        if not disc.resolved:
            return disc
    
    return None


def format_roadmap(roadmap: Roadmap) -> str:
    """Format roadmap for CLI display."""
    lines = [
        "═" * 40,
        f" ROADMAP: {roadmap.goal[:30]}{'...' if len(roadmap.goal) > 30 else ''}",
        "═" * 40,
        "",
    ]
    
    current_idx = roadmap.current_index()
    
    for i, m in enumerate(roadmap.milestones):
        if m.done:
            status = "✓"
            marker = ""
        elif i == current_idx:
            status = "◐"
            marker = " [current]"
        else:
            status = "○"
            marker = ""
        
        lines.append(f"  {status} Phase {i + 1}: {m.name}{marker}")
        if m.description:
            lines.append(f"      {m.description}")
        if m.spec_id:
            lines.append(f"      Spec: {m.spec_id}")
        if m.run_id:
            lines.append(f"      Run: {m.run_id}")
    
    lines.append("")
    lines.append(f"Progress: {roadmap.progress()} ({roadmap.progress_percent()}%)")
    
    current = roadmap.current_milestone()
    if current:
        lines.append(f"Current: Phase {current_idx + 1} - {current.name}")
    elif roadmap.is_complete():
        lines.append("Status: All phases complete!")
    
    return "\n".join(lines)


def get_current_milestone_goal(
    project_path: str,
    project_name: str,
) -> Optional[str]:
    """Get the goal string for the current milestone.
    
    Used to generate specs for the current phase.
    
    Returns:
        Goal string for current milestone, or None
    """
    disc = get_active_discussion(project_path, project_name)
    if not disc or not disc.roadmap:
        return None
    
    current = disc.roadmap.current_milestone()
    if not current:
        return None
    
    # Build milestone-specific goal
    return f"{current.name}: {current.description}"
