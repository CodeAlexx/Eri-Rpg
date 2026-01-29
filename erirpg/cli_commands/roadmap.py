"""
Roadmap Commands - Roadmap progress and management.

Commands:
- roadmap: Show roadmap progress for a project
- roadmap-add: Add a phase to the roadmap
- roadmap-next: Advance to the next roadmap phase
- roadmap-edit: Edit or delete a roadmap phase
"""

import sys
import click


def register(cli):
    """Register roadmap commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command()
    @click.argument("project")
    def roadmap(project: str):
        """Show roadmap progress for a project.

        Displays the roadmap from the active discussion.

        \b
        Example:
            eri-rpg roadmap myproject
        """
        from erirpg.discuss import get_active_discussion, format_roadmap

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        disc = get_active_discussion(proj.path, project)

        if not disc:
            click.echo(f"No active discussion for {project}")
            click.echo(f"Start one with: eri-rpg discuss {project} \"your goal\"")
            return

        if not disc.roadmap:
            click.echo(f"Discussion exists but no roadmap defined yet.")
            click.echo(f"Goal: {disc.goal}")
            click.echo(f"\nAdd phases with: eri-rpg roadmap-add {project} \"Phase Name\" \"Description\"")
            return

        click.echo(format_roadmap(disc.roadmap))

    @cli.command("roadmap-add")
    @click.argument("project")
    @click.argument("name")
    @click.argument("description", required=False, default="")
    def roadmap_add(project: str, name: str, description: str):
        """Add a phase to the roadmap.

        \b
        Examples:
            eri-rpg roadmap-add myproject "Setup" "Project structure and dependencies"
            eri-rpg roadmap-add myproject "Core Logic"
        """
        from erirpg.discuss import get_active_discussion, add_milestone, format_roadmap

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        disc = get_active_discussion(proj.path, project)

        if not disc:
            click.echo(f"Error: No active discussion for {project}", err=True)
            click.echo(f"Start one with: eri-rpg discuss {project} \"your goal\"")
            sys.exit(1)

        try:
            milestone = add_milestone(disc.goal, proj.path, project, name, description)
            click.echo(f"Added phase: {milestone.name}")

            # Reload and show updated roadmap
            disc = get_active_discussion(proj.path, project)
            click.echo("")
            click.echo(format_roadmap(disc.roadmap))

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("roadmap-next")
    @click.argument("project")
    def roadmap_next(project: str):
        """Advance to the next roadmap phase.

        Marks current phase as complete and shows next phase.

        \b
        Example:
            eri-rpg roadmap-next myproject
        """
        from erirpg.discuss import get_active_discussion, advance_roadmap, format_roadmap

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        disc = get_active_discussion(proj.path, project)

        if not disc:
            click.echo(f"Error: No active discussion for {project}", err=True)
            sys.exit(1)

        if not disc.roadmap:
            click.echo(f"Error: No roadmap defined for this discussion", err=True)
            sys.exit(1)

        current = disc.roadmap.current_milestone()
        if not current:
            click.echo("All phases already complete!")
            return

        click.echo(f"Completing: Phase {disc.roadmap.current_index() + 1} - {current.name}")

        try:
            next_milestone = advance_roadmap(disc.goal, proj.path, project)

            # Reload and show
            disc = get_active_discussion(proj.path, project)
            click.echo("")
            click.echo(format_roadmap(disc.roadmap))

            if next_milestone:
                click.echo(f"\nNext phase ready. Generate spec with:")
                click.echo(f"  eri-rpg goal-plan {project} \"{next_milestone.name}: {next_milestone.description}\"")
            else:
                click.echo("\n🎉 All phases complete!")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("roadmap-edit")
    @click.argument("project")
    @click.argument("phase_num", type=int)
    @click.option("--name", help="New name for the phase")
    @click.option("--description", help="New description")
    @click.option("--delete", is_flag=True, help="Delete this phase")
    def roadmap_edit(project: str, phase_num: int, name: str, description: str, delete: bool):
        """Edit or delete a roadmap phase.

        \b
        Examples:
            eri-rpg roadmap-edit myproject 2 --name "New Name"
            eri-rpg roadmap-edit myproject 3 --delete
        """
        from erirpg.discuss import get_active_discussion, format_roadmap
        from erirpg.memory import load_knowledge, save_knowledge

        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        disc = get_active_discussion(proj.path, project)

        if not disc or not disc.roadmap:
            click.echo(f"Error: No roadmap found for {project}", err=True)
            sys.exit(1)

        # Convert to 0-based index
        idx = phase_num - 1

        if idx < 0 or idx >= len(disc.roadmap.milestones):
            click.echo(f"Error: Phase {phase_num} not found (have {len(disc.roadmap.milestones)} phases)", err=True)
            sys.exit(1)

        milestone = disc.roadmap.milestones[idx]

        if delete:
            if milestone.done:
                click.echo(f"Warning: Deleting completed phase", err=True)
            disc.roadmap.milestones.pop(idx)
            click.echo(f"Deleted phase {phase_num}: {milestone.name}")
        else:
            if not name and not description:
                click.echo("Specify --name or --description to edit")
                sys.exit(1)
            if name:
                milestone.name = name
            if description:
                milestone.description = description
            click.echo(f"Updated phase {phase_num}")

        # Save
        store = load_knowledge(proj.path, project)
        store.add_discussion(disc)
        save_knowledge(proj.path, store)

        # Show updated roadmap
        click.echo("")
        click.echo(format_roadmap(disc.roadmap))
