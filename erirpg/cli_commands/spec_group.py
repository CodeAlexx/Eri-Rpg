"""
Spec Commands - Spec management for structured task definitions.

Commands:
- spec new: Create spec from template
- spec validate: Validate a spec file
- spec show: Display spec contents
- spec list: List specs in project
"""

import json
import os
import sys
import click


def register(cli):
    """Register spec group commands with CLI."""

    @cli.group()
    def spec():
        """Spec management commands.

        Specs are first-class inputs that describe tasks, projects, and transplants.
        They provide a structured way to define work with validation and versioning.

        \b
            spec new <type>       - Create spec from template
            spec validate <path>  - Validate a spec file
            spec show <path>      - Display spec contents
            spec list             - List specs in project
        """
        pass

    @spec.command("new")
    @click.argument("spec_type", type=click.Choice(["task", "project", "transplant"]))
    @click.option("-o", "--output", default=None, help="Output path (default: .eri-rpg/specs/)")
    @click.option("--name", "-n", default=None, help="Spec name")
    def spec_new(spec_type: str, output: str, name: str):
        """Create a new spec from template.

        Creates a spec file with example values that you can edit.

        \b
        Examples:
            eri-rpg spec new task
            eri-rpg spec new project -n my-app
            eri-rpg spec new transplant -o ./specs/my-transplant.json
        """
        from erirpg.specs import get_spec_template, create_spec, SPEC_VERSION

        template = get_spec_template(spec_type)

        if name:
            template["name"] = name

        # Create the spec to normalize and generate ID
        spec = create_spec(spec_type, **{k: v for k, v in template.items() if k != "spec_type"})

        # Determine output path
        if output:
            output_path = output
        else:
            # Default to .eri-rpg/specs/ in current directory
            specs_dir = os.path.join(os.getcwd(), ".eri-rpg", "specs")
            os.makedirs(specs_dir, exist_ok=True)
            output_path = os.path.join(specs_dir, f"{spec.id}.json")

        spec.save(output_path)

        click.echo(f"Created {spec_type} spec: {output_path}")
        click.echo("")
        click.echo("Edit the file to customize, then validate:")
        click.echo(f"  eri-rpg spec validate {output_path}")

    @spec.command("validate")
    @click.argument("path", type=click.Path(exists=True))
    def spec_validate(path: str):
        """Validate a spec file.

        Checks for required fields and valid values.

        \b
        Example:
            eri-rpg spec validate ./specs/my-task.json
        """
        from erirpg.specs import load_spec, validate_spec

        try:
            spec = load_spec(path)
            is_valid, errors = validate_spec(spec)

            if is_valid:
                click.echo(f"✓ Valid {spec.spec_type} spec: {spec.id}")
                click.echo(f"  Name: {getattr(spec, 'name', 'N/A')}")
                click.echo(f"  Version: {spec.version}")
            else:
                click.echo(f"✗ Invalid spec: {path}", err=True)
                click.echo("")
                for error in errors:
                    click.echo(f"  - {error}", err=True)
                sys.exit(1)

        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON in {path}", err=True)
            click.echo(f"  {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error loading spec: {e}", err=True)
            sys.exit(1)

    @spec.command("show")
    @click.argument("path", type=click.Path(exists=True))
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def spec_show(path: str, as_json: bool):
        """Display spec contents.

        Shows the spec in a readable format.

        \b
        Example:
            eri-rpg spec show ./specs/my-task.json
            eri-rpg spec show ./specs/my-task.json --json
        """
        from erirpg.specs import load_spec

        try:
            spec = load_spec(path)

            if as_json:
                click.echo(json.dumps(spec.to_dict(), indent=2))
                return

            # Human-readable format
            click.echo(f"Spec: {spec.id}")
            click.echo("=" * 50)
            click.echo(f"Type: {spec.spec_type}")
            click.echo(f"Version: {spec.version}")
            click.echo(f"Created: {spec.created_at.strftime('%Y-%m-%d %H:%M')}")
            click.echo(f"Updated: {spec.updated_at.strftime('%Y-%m-%d %H:%M')}")
            click.echo("")

            # Type-specific fields
            if spec.spec_type == "task":
                click.echo(f"Name: {spec.name}")
                click.echo(f"Task Type: {spec.task_type or '(not set)'}")
                click.echo(f"Status: {spec.status}")
                click.echo(f"Priority: {spec.priority}")
                if spec.source_project:
                    click.echo(f"Source: {spec.source_project}")
                if spec.target_project:
                    click.echo(f"Target: {spec.target_project}")
                if spec.query:
                    click.echo(f"Query: {spec.query}")
                if spec.description:
                    click.echo(f"\nDescription:\n  {spec.description}")

            elif spec.spec_type == "project":
                click.echo(f"Name: {spec.name}")
                click.echo(f"Language: {spec.language}")
                if spec.framework:
                    click.echo(f"Framework: {spec.framework}")
                click.echo(f"Core Feature: {spec.core_feature}")
                if spec.output_path:
                    click.echo(f"Output: {spec.output_path}")
                if spec.directories:
                    click.echo(f"\nDirectories: {', '.join(spec.directories)}")
                if spec.dependencies:
                    click.echo(f"Dependencies: {', '.join(spec.dependencies)}")

            elif spec.spec_type == "transplant":
                click.echo(f"Name: {spec.name}")
                click.echo(f"Source: {spec.source_project}")
                click.echo(f"Target: {spec.target_project}")
                click.echo(f"Feature: {spec.feature_name or '(from file)'}")
                if spec.feature_file:
                    click.echo(f"Feature File: {spec.feature_file}")
                if spec.components:
                    click.echo(f"\nComponents ({len(spec.components)}):")
                    for comp in spec.components[:5]:
                        click.echo(f"  - {comp}")
                    if len(spec.components) > 5:
                        click.echo(f"  ... and {len(spec.components) - 5} more")

            # Common fields
            if spec.tags:
                click.echo(f"\nTags: {', '.join(spec.tags)}")
            if spec.notes:
                click.echo(f"\nNotes:\n  {spec.notes}")

        except Exception as e:
            click.echo(f"Error loading spec: {e}", err=True)
            sys.exit(1)

    @spec.command("list")
    @click.option("-t", "--type", "spec_type", type=click.Choice(["task", "project", "transplant"]),
                  help="Filter by spec type")
    @click.option("-p", "--path", default=None, help="Project path (default: current directory)")
    def spec_list(spec_type: str, path: str):
        """List specs in a project.

        Shows all specs stored in the project's .eri-rpg/specs/ directory.

        \b
        Example:
            eri-rpg spec list
            eri-rpg spec list -t task
            eri-rpg spec list -p /path/to/project
        """
        from erirpg.specs import list_specs, load_spec

        project_path = path or os.getcwd()
        specs = list_specs(project_path, spec_type=spec_type)

        if not specs:
            click.echo("No specs found.")
            click.echo(f"\nCreate one with: eri-rpg spec new <type>")
            return

        click.echo(f"Specs in {project_path}:")
        click.echo("")

        for spec_path in specs:
            try:
                s = load_spec(spec_path)
                name = getattr(s, "name", s.id)
                click.echo(f"  [{s.spec_type}] {name}")
                click.echo(f"    ID: {s.id}")
                click.echo(f"    Path: {spec_path}")
            except Exception as e:
                click.echo(f"  [error] {spec_path}: {e}")
            click.echo("")
