"""
GSD Commands - Decision logging and deferred ideas (GSD-style).

Commands (standard tier):
- log-decision: Log a decision with full rationale
- list-decisions: List recent decisions
- defer: Capture a deferred idea for later implementation
- deferred: List deferred ideas
- promote: Promote a deferred idea to a roadmap milestone
"""

import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register GSD commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command(name="log-decision")
    @click.argument("project")
    @click.argument("context")
    @click.argument("choice")
    @click.argument("rationale")
    @tier_required("standard")
    def log_decision_cmd(project: str, context: str, choice: str, rationale: str):
        """Log a decision with full rationale (GSD-style).

        Unlike 'decide' (architectural decisions), this logs user decisions
        made during discussion or execution with detailed context.

        Example:
            eri-rpg log-decision myproj "Auth method" "JWT" "Stateless, works with microservices"
        """
        from erirpg.discuss import log_decision

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        decision = log_decision(
            proj.path,
            project,
            context,
            choice,
            rationale,
            source="manual",
        )

        click.echo(f"Logged decision: {decision.id}")
        click.echo(f"  Context: {context}")
        click.echo(f"  Choice: {choice}")
        click.echo(f"  Rationale: {rationale}")

    @cli.command(name="list-decisions")
    @click.argument("project")
    @click.option("--search", "-s", default=None, help="Search decisions by keyword")
    @click.option("--limit", "-n", default=20, help="Number of decisions to show")
    def list_decisions_cmd(project: str, search: str, limit: int):
        """List recent decisions (GSD-style).

        Example:
            eri-rpg list-decisions myproj
            eri-rpg list-decisions myproj --search "auth"
        """
        from erirpg.discuss import get_decisions

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        decs = get_decisions(proj.path, project, limit, search)

        if not decs:
            click.echo("No decisions found")
            return

        click.echo(f"Decisions ({len(decs)} shown):")
        click.echo("=" * 60)

        for d in decs:
            click.echo(f"[{d.id}] {d.timestamp.strftime('%Y-%m-%d %H:%M')}")
            click.echo(f"  Context: {d.context}")
            click.echo(f"  Choice: {d.choice}")
            click.echo(f"  Rationale: {d.rationale}")
            if d.alternatives:
                click.echo(f"  Alternatives: {', '.join(d.alternatives)}")
            click.echo(f"  Source: {d.source}")
            click.echo("")

    @cli.command(name="defer")
    @click.argument("project")
    @click.argument("idea")
    @click.option("--tags", "-t", default="", help="Comma-separated tags (e.g., v2,perf,ui)")
    def defer_cmd(project: str, idea: str, tags: str):
        """Capture a deferred idea for later implementation.

        Example:
            eri-rpg defer myproj "Add caching layer" --tags v2,perf
        """
        from erirpg.discuss import defer_idea

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        deferred = defer_idea(
            proj.path,
            project,
            idea,
            source="manual",
            tags=tag_list,
        )

        click.echo(f"Deferred idea: {deferred.id}")
        click.echo(f"  Idea: {idea}")
        if tag_list:
            click.echo(f"  Tags: {', '.join(tag_list)}")

    @cli.command(name="deferred")
    @click.argument("project")
    @click.option("--tag", "-t", default=None, help="Filter by tag")
    @click.option("--all", "-a", "all_ideas", is_flag=True, help="Include promoted ideas")
    def deferred_cmd(project: str, tag: str, all_ideas: bool):
        """List deferred ideas.

        Example:
            eri-rpg deferred myproj
            eri-rpg deferred myproj --tag v2
        """
        from erirpg.discuss import get_deferred_ideas

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        ideas = get_deferred_ideas(proj.path, project, tag, all_ideas)

        if not ideas:
            click.echo("No deferred ideas found")
            return

        click.echo(f"Deferred Ideas ({len(ideas)}):")
        click.echo("=" * 60)

        for i in ideas:
            status = "✓ Promoted" if i.promoted_to else "○ Pending"
            click.echo(f"[{i.id}] {status}")
            click.echo(f"  {i.idea}")
            if i.tags:
                click.echo(f"  Tags: {', '.join(i.tags)}")
            click.echo(f"  Source: {i.source} | Created: {i.created.strftime('%Y-%m-%d')}")
            if i.promoted_to:
                click.echo(f"  Promoted to: {i.promoted_to}")
            click.echo("")

    @cli.command(name="promote")
    @click.argument("project")
    @click.argument("idea_id")
    @click.option("--goal", "-g", default=None, help="Goal of roadmap to add to")
    def promote_cmd(project: str, idea_id: str, goal: str):
        """Promote a deferred idea to a roadmap milestone.

        Example:
            eri-rpg promote myproj IDEA-001 --goal "Build feature X"
        """
        from erirpg.discuss import promote_idea_to_milestone, get_active_discussion

        proj = registry.get(project)
        if not proj:
            click.echo(f"Project '{project}' not found")
            raise SystemExit(1)

        # If no goal specified, use active discussion
        if not goal:
            disc = get_active_discussion(proj.path, project)
            if not disc:
                click.echo("No active discussion found. Specify --goal")
                raise SystemExit(1)
            goal = disc.goal

        milestone = promote_idea_to_milestone(proj.path, project, idea_id, goal)

        if not milestone:
            click.echo(f"Could not promote idea {idea_id}")
            click.echo("Check that the idea exists and a discussion/roadmap exists for the goal")
            raise SystemExit(1)

        click.echo(f"Promoted {idea_id} to milestone: {milestone.id}")
        click.echo(f"  Name: {milestone.name}")
        click.echo(f"  Description: {milestone.description}")
