"""
Transplant Commands - Feature extraction and transplant operations.

Commands:
- extract: Extract a feature from a project
- plan: Plan transplant to target project (note: this shadows plan_group's plan command)
- context: Generate context for Claude Code
"""

import os
import sys
import click


def register(cli):
    """Register transplant commands with CLI."""
    from erirpg.registry import Registry
    from erirpg.state import State
    from erirpg.indexer import get_or_load_graph

    @cli.command()
    @click.argument("project")
    @click.argument("query")
    @click.option("-o", "--output", required=True, help="Output file path")
    @click.option("-n", "--name", default=None, help="Feature name")
    def extract(project: str, query: str, output: str, name: str):
        """Extract a feature from a project.

        Finds matching modules, includes dependencies, saves as JSON.
        """
        from erirpg.transplant import extract_feature

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        try:
            graph = get_or_load_graph(proj)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        feature_name = name or query.replace(" ", "_")

        try:
            feature = extract_feature(graph, proj, query, feature_name)
            feature.save(output)

            click.echo(f"Extracted feature: {feature_name}")
            click.echo(f"Components: {len(feature.components)}")
            for c in feature.components:
                click.echo(f"  - {c}")
            click.echo(f"Provides: {len(feature.provides)} interfaces")
            click.echo(f"Requires: {len(feature.requires)} packages")
            click.echo(f"\nSaved to: {output}")

            # Update state
            state = State.load()
            state.update(
                current_task=f"Transplant {feature_name} from {project}",
                phase="extracting",
                feature_file=output,
            )
            state.log("extract", f"Extracted {feature_name} to {output}")

            click.echo(f"\nNext: eri-rpg plan {output} <target_project>")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command("transplant-plan")
    @click.argument("feature_file", type=click.Path(exists=True))
    @click.argument("target_project")
    def transplant_plan(feature_file: str, target_project: str):
        """Plan transplant to target project.

        Creates mappings and wiring tasks.

        Note: Named transplant-plan to avoid conflict with plan group.
        """
        from erirpg.transplant import Feature, plan_transplant

        registry = Registry.get_instance()
        target = registry.get(target_project)

        if not target:
            click.echo(f"Error: Target project '{target_project}' not found", err=True)
            sys.exit(1)

        try:
            target_graph = get_or_load_graph(target)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        feature = Feature.load(feature_file)
        transplant_plan = plan_transplant(feature, target_graph, target)

        # Save plan
        plan_file = feature_file.replace(".json", ".plan.json")
        transplant_plan.save(plan_file)

        click.echo(f"Transplant plan: {feature.name} -> {target_project}")
        click.echo("")

        click.echo("Mappings:")
        for m in transplant_plan.mappings:
            click.echo(f"  {m.source_interface}: {m.action}")
            if m.notes:
                click.echo(f"    {m.notes}")

        if transplant_plan.wiring:
            click.echo("\nWiring tasks:")
            for w in transplant_plan.wiring:
                click.echo(f"  {w.file}: {w.details}")

        click.echo(f"\nSaved to: {plan_file}")

        # Update state
        state = State.load()
        state.update(phase="planning", plan_file=plan_file)
        state.log("plan", f"Created plan at {plan_file}")

        click.echo(f"\nNext: eri-rpg context {feature_file} {target_project}")

    @cli.command()
    @click.argument("feature_file", type=click.Path(exists=True))
    @click.argument("target_project")
    @click.option("--no-learnings", is_flag=True, help="Include full source instead of learnings")
    def context(feature_file: str, target_project: str, no_learnings: bool):
        """Generate context for Claude Code.

        Creates a markdown file with source code, target interfaces,
        and transplant plan. Uses stored learnings when available
        for ~85% token reduction on revisited modules.
        """
        from erirpg.transplant import (
            Feature,
            TransplantPlan,
            plan_transplant,
            generate_context,
            estimate_tokens,
        )

        registry = Registry.get_instance()
        target = registry.get(target_project)

        if not target:
            click.echo(f"Error: Target project '{target_project}' not found", err=True)
            sys.exit(1)

        try:
            target_graph = get_or_load_graph(target)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        feature = Feature.load(feature_file)

        # Load source project's graph for knowledge lookup
        source_proj = registry.get(feature.source_project)
        source_graph = None
        if source_proj:
            try:
                source_graph = get_or_load_graph(source_proj)
            except ValueError:
                pass  # No graph, no learnings - that's fine

        # Load or generate plan
        plan_file = feature_file.replace(".json", ".plan.json")
        if os.path.exists(plan_file):
            transplant_plan = TransplantPlan.load(plan_file)
        else:
            transplant_plan = plan_transplant(feature, target_graph, target)
            transplant_plan.save(plan_file)

        context_path = generate_context(
            feature, transplant_plan, source_graph, target_graph, target,
            source_project=source_proj,
            use_learnings=not no_learnings
        )

        tokens = estimate_tokens(feature, transplant_plan, source_project=source_proj)

        click.echo(f"Generated context: {context_path}")
        click.echo(f"Estimated tokens: ~{tokens:,}")
        click.echo("")
        click.echo("Give this file to Claude Code:")
        click.echo(f"  cat {context_path}")
        click.echo("")
        click.echo("Or reference it directly in conversation.")

        # Update state
        state = State.load()
        state.update(phase="context_ready", context_file=context_path, waiting_on="claude")
        state.log("context", f"Generated context at {context_path}")

        click.echo("\nAfter Claude implements, run: eri-rpg validate")
