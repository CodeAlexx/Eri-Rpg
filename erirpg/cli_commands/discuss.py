"""
Discuss Commands - Goal clarification and discussion management.

Commands:
- discuss: Start or continue a goal clarification discussion
- discuss-answer: Answer a discussion question
- discuss-resolve: Mark a discussion as resolved
- discuss-show: Show discussion(s) for a project
- discuss-clear: Clear discussions for a project
"""

import sys
import click


def register(cli):
    """Register discuss commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command()
    @click.argument("project")
    @click.argument("goal")
    @click.option("--force", is_flag=True, help="Force discussion even if not needed")
    def discuss(project: str, goal: str, force: bool):
        """Start or continue a goal clarification discussion.

        Before running goal-plan, use discuss to clarify vague goals.

        \b
        Example:
            eri-rpg discuss myproject "improve the code"
        """
        from erirpg.discuss import (
            needs_discussion, get_or_start_discussion, format_discussion
        )

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check if discussion is needed
        needed, reason = needs_discussion(goal, proj.path, force=force)

        if not needed and not force:
            click.echo(f"Discussion not needed: {reason}")
            click.echo(f"\nProceed with: eri-rpg goal-plan {project} \"{goal}\"")
            return

        # Get or start discussion
        discussion, is_new = get_or_start_discussion(goal, proj.path, project)

        if is_new:
            click.echo(f"Started new discussion for: {goal}")
        else:
            click.echo(f"Continuing discussion for: {goal}")

        click.echo("")
        click.echo(format_discussion(discussion))

        # Show how to answer
        unanswered = discussion.unanswered()
        if unanswered:
            click.echo(f"\nAnswer with:")
            click.echo(f"  eri-rpg discuss-answer {project} \"{goal}\" \"{unanswered[0]}\" \"<your answer>\"")

    @cli.command("discuss-answer")
    @click.argument("project")
    @click.argument("goal")
    @click.argument("question")
    @click.argument("answer")
    def discuss_answer(project: str, goal: str, question: str, answer: str):
        """Answer a discussion question.

        \b
        Example:
            eri-rpg discuss-answer myproject "improve the code" "What specific aspect?" "Performance"
        """
        from erirpg.discuss import answer_question, format_discussion
        from erirpg.memory import load_knowledge

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Check if discussion exists
        store = load_knowledge(proj.path, project)
        discussion = store.get_discussion_by_goal(goal)

        if not discussion:
            click.echo(f"Error: No discussion found for goal: {goal}", err=True)
            click.echo(f"Start one with: eri-rpg discuss {project} \"{goal}\"")
            sys.exit(1)

        # Validate question
        if question not in discussion.questions:
            click.echo(f"Error: Question not found in discussion", err=True)
            click.echo(f"Valid questions:")
            for i, q in enumerate(discussion.questions, 1):
                click.echo(f"  {i}. {q}")
            sys.exit(1)

        # Answer
        try:
            discussion = answer_question(goal, proj.path, project, question, answer)
            click.echo(f"Recorded answer for: {question}")
            click.echo(f"  → {answer}")
            click.echo("")
            click.echo(format_discussion(discussion))

            if discussion.is_complete():
                click.echo(f"\nAll questions answered!")
                click.echo(f"Resolve with: eri-rpg discuss-resolve {project} \"{goal}\"")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("discuss-resolve")
    @click.argument("project")
    @click.argument("goal")
    def discuss_resolve(project: str, goal: str):
        """Mark a discussion as resolved and ready for spec generation.

        \b
        Example:
            eri-rpg discuss-resolve myproject "improve the code"
        """
        from erirpg.discuss import resolve_discussion, enrich_goal

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        try:
            discussion = resolve_discussion(goal, proj.path, project)
            click.echo(f"Discussion resolved!")
            click.echo("")

            # Show enriched goal
            enriched = enrich_goal(goal, proj.path, project)
            click.echo("Enriched goal for spec generation:")
            click.echo("-" * 40)
            click.echo(enriched)
            click.echo("-" * 40)
            click.echo("")
            click.echo(f"Generate spec with:")
            click.echo(f"  eri-rpg goal-plan {project} \"{goal}\"")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("discuss-show")
    @click.argument("project")
    @click.argument("goal", required=False)
    def discuss_show(project: str, goal: str = None):
        """Show discussion(s) for a project.

        \b
        Examples:
            eri-rpg discuss-show myproject              # Show all discussions
            eri-rpg discuss-show myproject "the goal"   # Show specific discussion
        """
        from erirpg.discuss import format_discussion
        from erirpg.memory import load_knowledge

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        store = load_knowledge(proj.path, project)

        if goal:
            # Show specific discussion
            discussion = store.get_discussion_by_goal(goal)
            if not discussion:
                click.echo(f"No discussion found for goal: {goal}")
                return
            click.echo(format_discussion(discussion))
        else:
            # Show all discussions
            discussions = store.list_discussions()
            if not discussions:
                click.echo(f"No discussions for {project}")
                return

            click.echo(f"Discussions for {project}:")
            click.echo("")
            for disc in discussions:
                status = "✓ Resolved" if disc.resolved else f"○ In Progress ({len(disc.unanswered())} unanswered)"
                click.echo(f"  {disc.id[:8]}: {disc.goal[:40]}...")
                click.echo(f"    Status: {status}")
                click.echo("")

    @cli.command("discuss-clear")
    @click.argument("project")
    @click.option("--all", "clear_all", is_flag=True, help="Clear all discussions")
    @click.option("--resolved", is_flag=True, help="Clear only resolved discussions")
    def discuss_clear(project: str, clear_all: bool, resolved: bool):
        """Clear discussions for a project.

        \b
        Examples:
            eri-rpg discuss-clear myproject --all       # Clear all
            eri-rpg discuss-clear myproject --resolved  # Clear resolved only
        """
        from erirpg.memory import load_knowledge, save_knowledge

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        if not clear_all and not resolved:
            click.echo("Specify --all or --resolved")
            sys.exit(1)

        store = load_knowledge(proj.path, project)

        if clear_all:
            count = store.clear_discussions()
            save_knowledge(proj.path, store)
            click.echo(f"Cleared {count} discussion(s)")
        elif resolved:
            # Clear only resolved discussions
            to_remove = [d.id for d in store.list_discussions() if d.resolved]
            for disc_id in to_remove:
                store.remove_discussion(disc_id)
            save_knowledge(proj.path, store)
            click.echo(f"Cleared {len(to_remove)} resolved discussion(s)")
