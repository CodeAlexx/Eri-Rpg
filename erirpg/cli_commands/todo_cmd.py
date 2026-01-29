"""
TODO Commands - Personal task tracking.

Commands:
- todo: Add or list todos
- todo-done: Mark a todo complete
- todo-rm: Remove a todo
- todo-clear: Clear completed todos
"""

import sys
import click


def register(cli):
    """Register todo commands with CLI."""

    @cli.command("todo")
    @click.argument("text", nargs=-1)
    @click.option("-p", "--project", default=None, help="Associate with project")
    @click.option("--priority", type=click.Choice(["low", "normal", "high", "urgent"]),
                  default="normal", help="Priority level")
    @click.option("-t", "--tag", multiple=True, help="Add tags")
    @click.option("-a", "--all", "show_all", is_flag=True, help="Show all including completed")
    def todo_cmd(text: tuple, project: str, priority: str, tag: tuple, show_all: bool):
        """Add or list personal todos.

        \b
        Examples:
            eri-rpg todo                           # List pending todos
            eri-rpg todo fix the auth bug          # Add a todo
            eri-rpg todo -p myproject add tests    # Add with project
            eri-rpg todo --priority high urgent fix
            eri-rpg todo -t bug -t backend fix crash
            eri-rpg todo --all                     # Show completed too
        """
        from erirpg.todos import (
            load_todos, add_todo, format_todo_list
        )

        # If no text, list todos
        if not text:
            todos = load_todos()

            if show_all:
                # Show all todos grouped
                pending = todos.by_priority()
                completed = todos.completed()

                if pending:
                    click.echo(format_todo_list(pending, "Pending"))
                else:
                    click.echo("No pending todos")

                if completed:
                    click.echo("")
                    click.echo(format_todo_list(completed, "Recently Completed"))
            else:
                pending = todos.by_priority()
                if pending:
                    click.echo(format_todo_list(pending, "Pending Todos"))
                else:
                    click.echo("No pending todos 🎉")
            return

        # Add new todo
        todo_text = " ".join(text)
        tags = list(tag) if tag else []

        todo = add_todo(todo_text, project, priority, tags)
        click.echo(f"Added: [{todo.id}] {todo.text}")

    @cli.command("todo-done")
    @click.argument("todo_id", type=int)
    def todo_done_cmd(todo_id: int):
        """Mark a todo as complete.

        \b
        Example:
            eri-rpg todo-done 3
        """
        from erirpg.todos import complete_todo

        todo = complete_todo(todo_id)
        if todo:
            click.echo(f"✅ Completed: {todo.text}")
        else:
            click.echo(f"Todo {todo_id} not found", err=True)
            sys.exit(1)

    @cli.command("todo-rm")
    @click.argument("todo_id", type=int)
    def todo_rm_cmd(todo_id: int):
        """Remove a todo entirely.

        \b
        Example:
            eri-rpg todo-rm 3
        """
        from erirpg.todos import remove_todo, load_todos

        todos = load_todos()
        todo = todos.get(todo_id)

        if remove_todo(todo_id):
            click.echo(f"Removed: {todo.text if todo else todo_id}")
        else:
            click.echo(f"Todo {todo_id} not found", err=True)
            sys.exit(1)

    @cli.command("todo-clear")
    @click.option("--force", is_flag=True, help="Skip confirmation")
    def todo_clear_cmd(force: bool):
        """Clear all completed todos.

        \b
        Example:
            eri-rpg todo-clear
            eri-rpg todo-clear --force
        """
        from erirpg.todos import load_todos, clear_completed

        todos = load_todos()
        completed_count = len(todos.completed(limit=1000))

        if completed_count == 0:
            click.echo("No completed todos to clear")
            return

        if not force:
            if not click.confirm(f"Clear {completed_count} completed todo(s)?"):
                click.echo("Cancelled")
                return

        count = clear_completed()
        click.echo(f"Cleared {count} completed todo(s)")
