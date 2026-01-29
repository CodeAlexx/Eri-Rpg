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
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from erirpg.memory import Decision, DeferredIdea

from erirpg.memory import (
    Discussion,
    Milestone,
    Roadmap,
    load_knowledge,
    save_knowledge,
)

# ============================================================================
# Domain Detection and Gray Areas
# ============================================================================

DOMAIN_GRAY_AREAS = {
    "ui": [
        "layout and spacing",
        "user interactions",
        "empty states",
        "loading states",
        "error display",
        "responsive behavior",
    ],
    "api": [
        "response format",
        "error codes and messages",
        "pagination",
        "rate limiting",
        "authentication",
        "versioning",
    ],
    "cli": [
        "output format",
        "verbosity levels",
        "flags vs environment vars",
        "error handling",
        "progress indication",
    ],
    "data": [
        "validation rules",
        "edge cases",
        "null/empty handling",
        "migrations",
        "default values",
    ],
    "backend": [
        "error handling",
        "logging",
        "caching",
        "concurrency",
        "transactions",
    ],
    "testing": [
        "test scope",
        "mocking strategy",
        "edge cases to cover",
        "performance thresholds",
    ],
}

# File patterns for domain detection
DOMAIN_FILE_PATTERNS = {
    "ui": [".jsx", ".tsx", ".vue", ".svelte", ".css", ".scss", "component", "widget"],
    "api": ["api/", "routes/", "endpoint", "handler", "controller"],
    "cli": ["cli", "command", "main.py", "__main__"],
    "data": ["model", "schema", "migration", "database", "db"],
    "backend": ["service", "worker", "task", "queue", "cache"],
    "testing": ["test_", "_test", "spec.", ".test."],
}

# Keywords for domain detection
DOMAIN_KEYWORDS = {
    "ui": ["component", "button", "form", "modal", "layout", "style", "responsive", "ui", "ux", "frontend"],
    "api": ["endpoint", "api", "rest", "graphql", "request", "response", "route", "http"],
    "cli": ["command", "cli", "flag", "argument", "option", "terminal", "console"],
    "data": ["database", "model", "schema", "migration", "query", "orm", "table"],
    "backend": ["service", "worker", "queue", "cache", "async", "task", "job", "background"],
    "testing": ["test", "spec", "mock", "fixture", "assert", "coverage"],
}


def detect_domain(goal: str, project_path: str) -> str:
    """Detect primary domain from goal text and project structure.

    Returns:
        Domain string: "ui", "api", "cli", "data", "backend", "testing", or "general"
    """
    goal_lower = goal.lower()

    # Score each domain by keyword matches
    scores = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in goal_lower:
                scores[domain] += 1

    # Also check file patterns in goal
    for domain, patterns in DOMAIN_FILE_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in goal_lower:
                scores[domain] += 0.5

    # Get highest scoring domain
    best_domain = max(scores, key=scores.get)
    if scores[best_domain] > 0:
        return best_domain

    return "general"


def get_gray_area_questions(goal: str, domain: str) -> List[str]:
    """Generate questions about common ambiguities for a domain.

    Gray area detection - asks about common decision points
    that are often left ambiguous.

    Returns:
        List of gray area questions
    """
    gray_areas = DOMAIN_GRAY_AREAS.get(domain, [])
    if not gray_areas:
        return []

    questions = []
    for area in gray_areas[:4]:  # Max 4 gray area questions
        questions.append(f"How should we handle {area}? (say 'defer' to handle later)")

    return questions



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
            if f.endswith((".py", ".rs", ".c", ".h", ".js", ".ts", ".go", ".dart")):
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
        ".py", ".rs", ".c", ".js", ".ts", ".dart",  # File references
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



def answer_question_with_logging(
    goal: str,
    project_path: str,
    project_name: str,
    question: str,
    answer: str,
) -> Tuple["Discussion", Optional["Decision"], Optional["DeferredIdea"]]:
    """Record an answer to a question with decision logging and defer detection.

    If answer contains "defer" or "v2" or "later", captures as deferred idea.
    Otherwise logs as a decision.

    Returns:
        (Updated Discussion, Decision if logged, DeferredIdea if deferred)
    """
    from datetime import datetime

    from erirpg.memory import Decision, DeferredIdea, load_knowledge, save_knowledge

    store = load_knowledge(project_path, project_name)
    discussion = store.get_discussion_by_goal(goal)

    if not discussion:
        raise ValueError(f"No discussion found for goal: {goal}")

    # Record the answer
    discussion.answer(question, answer)

    decision = None
    deferred = None
    answer_lower = answer.lower()

    # Check for defer keywords
    defer_keywords = ["defer", "v2", "later", "future", "skip", "not now", "backlog"]
    is_deferred = any(kw in answer_lower for kw in defer_keywords)

    if is_deferred:
        # Capture as deferred idea
        deferred = DeferredIdea(
            id=store.next_idea_id(),
            idea=f"{question}: {answer}",
            source="discuss",
            created=datetime.now(),
            tags=["v2"] if "v2" in answer_lower else ["deferred"],
        )
        store.add_deferred_idea(deferred)
    else:
        # Log as decision
        decision = Decision(
            id=store.next_decision_id(),
            timestamp=datetime.now(),
            context=question,
            choice=answer,
            rationale="User specified during discussion",
            alternatives=[],
            source="discuss",
        )
        store.add_user_decision(decision)

    store.add_discussion(discussion)
    save_knowledge(project_path, store)

    return discussion, decision, deferred



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
# Decision Logging Helpers
# ============================================================================

def log_decision(
    project_path: str,
    project_name: str,
    context: str,
    choice: str,
    rationale: str,
    alternatives: List[str] = None,
    source: str = "manual",
    run_id: Optional[str] = None,
) -> "Decision":
    """Log a decision with rationale.

    Args:
        project_path: Path to project
        project_name: Project name
        context: What was being decided
        choice: What was chosen
        rationale: Why this choice
        alternatives: What was rejected
        source: "discuss", "manual", "auto"
        run_id: Optional run ID

    Returns:
        The created Decision
    """
    from datetime import datetime

    from erirpg.memory import Decision, load_knowledge, save_knowledge

    store = load_knowledge(project_path, project_name)

    decision = Decision(
        id=store.next_decision_id(),
        timestamp=datetime.now(),
        context=context,
        choice=choice,
        rationale=rationale,
        alternatives=alternatives or [],
        source=source,
        run_id=run_id,
    )

    store.add_user_decision(decision)
    save_knowledge(project_path, store)

    return decision


def get_decisions(
    project_path: str,
    project_name: str,
    limit: int = 20,
    search: Optional[str] = None,
) -> List["Decision"]:
    """Get recent decisions, optionally filtered by search.

    Returns:
        List of Decision objects
    """
    from erirpg.memory import load_knowledge

    store = load_knowledge(project_path, project_name)

    if search:
        return store.search_decisions(search)[:limit]
    return store.get_user_decisions(limit)


# ============================================================================
# Deferred Ideas Helpers
# ============================================================================

def defer_idea(
    project_path: str,
    project_name: str,
    idea: str,
    source: str = "manual",
    tags: List[str] = None,
) -> "DeferredIdea":
    """Capture a deferred idea.

    Args:
        project_path: Path to project
        project_name: Project name
        idea: The idea description
        source: "discuss", "manual", "gap-closure"
        tags: Optional tags like ["ui", "v2", "perf"]

    Returns:
        The created DeferredIdea
    """
    from datetime import datetime

    from erirpg.memory import DeferredIdea, load_knowledge, save_knowledge

    store = load_knowledge(project_path, project_name)

    deferred = DeferredIdea(
        id=store.next_idea_id(),
        idea=idea,
        source=source,
        created=datetime.now(),
        tags=tags or [],
    )

    store.add_deferred_idea(deferred)
    save_knowledge(project_path, store)

    return deferred


def get_deferred_ideas(
    project_path: str,
    project_name: str,
    tag: Optional[str] = None,
    include_promoted: bool = False,
) -> List["DeferredIdea"]:
    """Get deferred ideas, optionally filtered by tag.

    Returns:
        List of DeferredIdea objects
    """
    from erirpg.memory import load_knowledge

    store = load_knowledge(project_path, project_name)

    if tag:
        return store.get_deferred_by_tag(tag)
    return store.get_deferred_ideas(include_promoted)


def promote_idea_to_milestone(
    project_path: str,
    project_name: str,
    idea_id: str,
    goal: str,
) -> Optional["Milestone"]:
    """Promote a deferred idea to a roadmap milestone.

    Args:
        project_path: Path to project
        project_name: Project name
        idea_id: ID of idea to promote
        goal: Goal of the discussion with the roadmap

    Returns:
        The created Milestone, or None if idea not found
    """
    from erirpg.memory import load_knowledge, save_knowledge

    store = load_knowledge(project_path, project_name)

    # Find the idea
    idea = None
    for i in store.deferred_ideas:
        if i.id == idea_id:
            idea = i
            break

    if not idea:
        return None

    # Get or create discussion/roadmap
    discussion = store.get_discussion_by_goal(goal)
    if not discussion:
        return None

    if not discussion.roadmap:
        discussion.roadmap = Roadmap.create(goal)

    # Add milestone
    milestone = discussion.roadmap.add_milestone(
        name=f"Deferred: {idea.idea[:30]}",
        description=idea.idea,
    )

    # Mark idea as promoted
    store.promote_idea(idea_id, milestone.id)

    store.add_discussion(discussion)
    save_knowledge(project_path, store)

    return milestone



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


# ============================================================================
# New Project Discussion Functions
# ============================================================================

NEW_PROJECT_QUESTIONS = [
    # Core purpose
    "What is the core purpose of this project? (One sentence describing the main thing it does)",
    # Stack preference
    "What technical stack should we use? (e.g., fastapi, cli, flask, django, or 'no preference')",
    # Constraints
    "Are there any key constraints? (e.g., must work offline, no external deps, specific platform)",
    # Target users
    "Who will use this? (developers, end users, internal team, etc.)",
]


def generate_new_project_questions(
    description: str,
    project_path: str,
) -> List[str]:
    """Generate clarifying questions for new project creation.

    Questions cover:
    - Core purpose/MVP scope
    - Technical stack preferences
    - Constraints (offline, external deps)
    - Target users

    Args:
        description: Initial project description
        project_path: Path where project will be created

    Returns:
        List of questions to ask
    """
    questions = []

    desc_lower = description.lower() if description else ""

    # Always ask about core purpose unless description is very detailed
    if len(description) < 100:
        questions.append(NEW_PROJECT_QUESTIONS[0])

    # Ask about stack if not already mentioned
    stack_keywords = ["fastapi", "flask", "django", "cli", "click", "api", "rest", "graphql"]
    has_stack_hint = any(kw in desc_lower for kw in stack_keywords)
    if not has_stack_hint:
        questions.append(NEW_PROJECT_QUESTIONS[1])

    # Always ask about constraints
    questions.append(NEW_PROJECT_QUESTIONS[2])

    # Ask about target users unless obvious from description
    user_keywords = ["user", "developer", "team", "customer", "client"]
    has_user_hint = any(kw in desc_lower for kw in user_keywords)
    if not has_user_hint:
        questions.append(NEW_PROJECT_QUESTIONS[3])

    # Limit to 3-4 questions
    return questions[:4]


def generate_spec_from_discussion(
    discussion: Discussion,
    stack_hint: Optional[str] = None,
    project_path: str = "",
    project_name: str = "",
) -> "ProjectSpec":
    """Generate a ProjectSpec from completed discussion.

    Maps discussion answers to ProjectSpec fields:
    - core_feature from purpose answer
    - framework from stack answer
    - directories from structure answer

    Args:
        discussion: Completed discussion with answers
        stack_hint: Optional stack override
        project_path: Path where project will be created
        project_name: Name for the project

    Returns:
        Generated ProjectSpec
    """
    from erirpg.specs import ProjectSpec

    # Extract answers
    answers = discussion.answers

    # Find core feature (purpose answer)
    core_feature = ""
    for q, a in answers.items():
        if "core purpose" in q.lower() or "main thing" in q.lower():
            core_feature = a
            break

    # If no specific answer, use the goal
    if not core_feature:
        core_feature = discussion.goal

    # Find framework preference
    framework = stack_hint or ""
    for q, a in answers.items():
        if "stack" in q.lower() or "technical" in q.lower():
            answer_lower = a.lower()
            if "fastapi" in answer_lower or "api" in answer_lower:
                framework = "fastapi"
            elif "cli" in answer_lower or "command" in answer_lower:
                framework = "cli"
            elif "flask" in answer_lower:
                framework = "flask"
            elif "django" in answer_lower:
                framework = "django"
            elif "no preference" not in answer_lower and a.strip():
                framework = a.strip()
            break

    # Extract constraints as notes
    notes_parts = []
    skip_answers = ["none", "no", "n/a", "", "(default)", "(no answer)"]
    for q, a in answers.items():
        if "constraint" in q.lower():
            if a.lower() not in skip_answers:
                notes_parts.append(f"Constraints: {a}")
        if "who will use" in q.lower() or "target" in q.lower():
            if a.lower() not in skip_answers:
                notes_parts.append(f"Target users: {a}")

    # Build description from goal and answers
    description = discussion.goal
    if notes_parts:
        description += "\n\n" + "\n".join(notes_parts)

    # Create spec
    spec = ProjectSpec(
        name=project_name or _extract_name_from_goal(discussion.goal),
        description=description,
        language="python",  # Default to Python
        framework=framework,
        core_feature=core_feature,
        output_path=project_path,
        notes="\n".join(notes_parts),
    )

    # Normalize and generate ID
    spec.normalize()

    return spec


def _extract_name_from_goal(goal: str) -> str:
    """Extract a project name from a goal string.

    Args:
        goal: Goal string like "REST API for users"

    Returns:
        Slugified name like "rest-api-users"
    """
    import re

    # Remove common prefixes
    for prefix in ["create ", "build ", "make ", "implement ", "add "]:
        if goal.lower().startswith(prefix):
            goal = goal[len(prefix):]
            break

    # Take first few words
    words = goal.split()[:4]
    name = "-".join(words)

    # Slugify
    name = re.sub(r'[^a-zA-Z0-9-]', '', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')

    return name or "new-project"
