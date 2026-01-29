"""
Knowledge Commands - Learning storage and retrieval.

Commands (standard tier):
- learn: Store a learning about a module
- recall: Retrieve what was learned about a module
- relearn: Force re-read a module (removes stored learning)
- history: Show version history for a module's learning
- rollback: Rollback a module's learning to a previous version (full tier)
- decide: Record an architectural decision (legacy)
- pattern: Store a reusable pattern or gotcha
- patterns: List all stored patterns for a project
"""

import os
import sys
import click
from datetime import datetime

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register knowledge commands with CLI."""

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    @click.option("--summary", "-s", prompt=True, help="One-line summary of the module")
    @click.option("--purpose", "-p", prompt=True, help="Detailed purpose explanation")
    @click.option("--non-interactive", "-y", is_flag=True, help="Skip interactive prompts for key functions and gotchas")
    @tier_required("standard")
    def learn(project: str, module_path: str, summary: str, purpose: str, non_interactive: bool):
        """Store a learning about a module.

        After understanding a module, record key insights so you don't
        have to re-read it later. Saves ~85% tokens on revisits.

        Example:
            eri-rpg learn onetrainer modules/util/loss.py \\
                -s "Loss calculation utilities" \\
                -p "Handles MSE, masked, and prior-based losses"

            # Non-interactive mode (for scripts/automation):
            eri-rpg learn onetrainer modules/util/loss.py -y \\
                -s "Loss calculation utilities" \\
                -p "Handles MSE, masked, and prior-based losses"
        """
        from erirpg.registry import Registry
        from erirpg.indexer import get_or_load_graph
        from erirpg.refs import CodeRef
        from erirpg.memory import StoredLearning, load_knowledge, save_knowledge

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

        key_functions = {}
        gotchas = []

        if not non_interactive:
            # Prompt for optional details
            click.echo("\nOptional: Enter key functions (name: description), empty line to finish:")
            while True:
                line = click.prompt("", default="", show_default=False)
                if not line:
                    break
                if ":" in line:
                    name, desc = line.split(":", 1)
                    key_functions[name.strip()] = desc.strip()

            click.echo("\nOptional: Enter gotchas (one per line), empty line to finish:")
            while True:
                line = click.prompt("", default="", show_default=False)
                if not line:
                    break
                gotchas.append(line)

        # Create CodeRef for source file tracking
        source_path = os.path.join(proj.path, module_path)
        source_ref = None
        if os.path.exists(source_path):
            source_ref = CodeRef.from_file(proj.path, module_path)

        # Create and store learning in v2 knowledge store
        learning = StoredLearning(
            module_path=module_path,
            learned_at=datetime.now(),
            summary=summary,
            purpose=purpose,
            key_functions=key_functions,
            gotchas=gotchas,
            source_ref=source_ref,
        )

        # Load existing knowledge store and add learning
        store = load_knowledge(proj.path, project)
        store.add_learning(learning)
        save_knowledge(proj.path, store)

        click.echo(f"\n✓ Stored learning for {module_path}")
        click.echo(f"  Summary: {summary}")
        click.echo(f"  Key functions: {len(key_functions)}")
        click.echo(f"  Gotchas: {len(gotchas)}")
        if source_ref:
            click.echo(f"  Source tracking: enabled (staleness detection)")

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    @click.option("--source", is_flag=True, help="Also show original source code")
    def recall(project: str, module_path: str, source: bool):
        """Retrieve what was learned about a module.

        Use this instead of re-reading source code. If no learning
        exists, you'll be prompted to read and learn.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Load from v2 knowledge store
        store = load_knowledge(proj.path, project)
        learning = store.get_learning(module_path)

        if learning:
            # Format with staleness check
            click.echo(learning.format_for_context(proj.path))

            if source:
                click.echo("\n--- Original Source ---\n")
                source_path = os.path.join(proj.path, module_path)
                if os.path.exists(source_path):
                    with open(source_path) as f:
                        click.echo(f.read())
                else:
                    click.echo(f"Source file not found: {source_path}")
        else:
            click.echo(f"No learning stored for {module_path}")
            click.echo(f"\nTo learn this module:")
            click.echo(f"  1. Read the source: cat {os.path.join(proj.path, module_path)}")
            click.echo(f"  2. Store learning: eri-rpg learn {project} {module_path}")

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    def relearn(project: str, module_path: str):
        """Force re-read a module (removes stored learning).

        Use when the source code has changed significantly.
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, save_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Load from v2 knowledge store
        store = load_knowledge(proj.path, project)

        if store.remove_learning(module_path):
            save_knowledge(proj.path, store)
            click.echo(f"✓ Removed learning for {module_path}")
            click.echo(f"\nNow read the source and store new learning:")
            click.echo(f"  eri-rpg learn {project} {module_path}")
        else:
            click.echo(f"No learning stored for {module_path}")

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    def history(project: str, module_path: str):
        """Show version history for a module's learning.

        Displays all recorded versions with timestamps, operations,
        and associated git commits.

        Example:
            eri-rpg history eritrainer training/optimizer.py
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        store = load_knowledge(proj.path, project)
        learning = store.get_learning(module_path)

        if not learning:
            click.echo(f"No learning found for {module_path}")
            return

        click.echo(f"{'═' * 50}")
        click.echo(f" History: {module_path}")
        click.echo(f"{'═' * 50}")
        click.echo(f"Current version: v{learning.current_version}")
        click.echo("")

        if not learning.versions:
            click.echo("No version history available")
            click.echo("(Versions are created when learnings are modified)")
            return

        for v in reversed(learning.versions):
            marker = " (current)" if v.version == learning.current_version else ""
            click.echo(f"v{v.version}{marker} - {v.timestamp.strftime('%Y-%m-%d %H:%M')} - {v.operation}")
            if v.change_description:
                click.echo(f"    {v.change_description}")
            if v.commit_before:
                click.echo(f"    git before: {v.commit_before}")
            if v.commit_after:
                click.echo(f"    git after: {v.commit_after}")
            click.echo("")

        if learning.transplanted_from:
            click.echo(f"Transplanted from: {learning.transplanted_from}")

        if learning.transplanted_to_list:
            click.echo(f"Transplanted to: {', '.join(learning.transplanted_to_list)}")

    @cli.command()
    @click.argument("project")
    @click.argument("module_path")
    @click.option("-v", "--version", "target_version", type=int, default=None,
                  help="Version to rollback to (default: previous)")
    @click.option("--code", is_flag=True, help="Also restore files to disk from snapshot")
    @click.option("--dry-run", is_flag=True, help="Show what would be restored without doing it")
    @click.option("--use-git", is_flag=True, help="Use git checkout instead of stored snapshots")
    def rollback(project: str, module_path: str, target_version: int, code: bool, dry_run: bool, use_git: bool):
        """Rollback a module's learning to a previous version.

        Restores the learning's summary, purpose, key_functions, and gotchas
        to the state they were in at the specified version.

        With --code: Also restores the actual file contents from stored snapshots.

        Example:
            eri-rpg rollback eritrainer training/optimizer.py
            eri-rpg rollback eritrainer training/optimizer.py -v 2
            eri-rpg rollback eritrainer training/optimizer.py --code
            eri-rpg rollback eritrainer training/optimizer.py --code --dry-run
            eri-rpg rollback eritrainer training/optimizer.py --code --use-git
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, save_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        store = load_knowledge(proj.path, project)
        learning = store.get_learning(module_path)

        if not learning:
            click.echo(f"No learning found for {module_path}")
            return

        if not learning.versions:
            click.echo("No version history available")
            return

        # Find target version
        target = target_version if target_version is not None else learning.current_version - 1

        if target < 1:
            click.echo("Already at earliest version (versions start at 1)")
            return

        # Find the version by number
        version_obj = None
        for v in learning.versions:
            if v.version == target:
                version_obj = v
                break

        if not version_obj:
            available = [v.version for v in learning.versions]
            click.echo(f"Version {target} not found. Available: {available}")
            return

        old_version = learning.current_version

        if code:
            # Restore files to disk
            if use_git and version_obj.commit_before:
                # Use git checkout
                import subprocess
                if dry_run:
                    click.echo(f"Would run: git checkout {version_obj.commit_before} -- {module_path}")
                else:
                    try:
                        subprocess.run(
                            ['git', 'checkout', version_obj.commit_before, '--', module_path],
                            cwd=proj.path,
                            check=True,
                            capture_output=True,
                        )
                        click.echo(f"✓ Restored {module_path} from git commit {version_obj.commit_before}")
                    except subprocess.CalledProcessError as e:
                        click.echo(f"Git checkout failed: {e.stderr.decode() if e.stderr else str(e)}", err=True)
                        sys.exit(1)

                    # Also rollback metadata
                    learning.rollback(target)
                    store.add_learning(learning)
                    save_knowledge(proj.path, store)
                    click.echo(f"✓ Rolled back learning: v{old_version} -> v{target}")

            elif version_obj.files_content:
                # Use stored snapshot
                result = learning.rollback_files(
                    project_path=proj.path,
                    to_version=target,
                    dry_run=dry_run,
                )

                click.echo(result.format())

                if not dry_run and result.success:
                    store.add_learning(learning)
                    save_knowledge(proj.path, store)

            else:
                click.echo(f"No code snapshot available for version {target}.")
                if version_obj.commit_before:
                    click.echo(f"\nGit commit available. Re-run with --use-git:")
                    click.echo(f"  eri-rpg rollback {project} {module_path} -v {target} --code --use-git")
                else:
                    click.echo("You may need to restore manually from git history.")
                sys.exit(1)

        else:
            # Metadata-only rollback
            try:
                learning.rollback(target)
                store.add_learning(learning)
                save_knowledge(proj.path, store)

                click.echo(f"Rolled back {module_path}: v{old_version} -> v{target}")
                click.echo("\nNote: Only learning metadata was rolled back.")
                click.echo("To also restore file contents, use --code flag.")

                # Show what's available
                if version_obj.files_content:
                    click.echo(f"\n  eri-rpg rollback {project} {module_path} -v {target} --code")
                elif version_obj.commit_before:
                    click.echo(f"\n  eri-rpg rollback {project} {module_path} -v {target} --code --use-git")

            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)

    @cli.command()
    @click.argument("title")
    @click.option("--reason", "-r", required=True, help="Why this decision was made")
    @click.option("--affects", "-a", multiple=True, help="Module paths affected")
    @click.option("--alt", multiple=True, help="Alternatives considered")
    def decide(title: str, reason: str, affects: tuple, alt: tuple):
        """Record an architectural decision.

        Stores important decisions with rationale for future reference.

        Example:
            eri-rpg decide "Use PEFT for LoRA" \\
                -r "Better maintained than custom implementation" \\
                -a eritrainer/training/lora.py \\
                --alt "Custom LoRA" --alt "LoRAX"
        """
        from erirpg.state import State
        from erirpg.knowledge import Decision

        state = State.load()

        # Get current project from state or ask
        project = state.current_task.split()[-1] if state.current_task else None

        if not project:
            click.echo("No active project context.")
            click.echo("Decisions are stored globally in state.")

        # Create decision ID from title
        decision_id = title.lower().replace(" ", "_")[:30]

        decision = Decision(
            id=decision_id,
            date=datetime.now(),
            title=title,
            reason=reason,
            affects=list(affects),
            alternatives=list(alt),
        )

        # Store in state history for now (could also store in graph)
        state.log("decision", f"{title}: {reason}")

        click.echo(f"✓ Recorded decision: {title}")
        click.echo(f"  Reason: {reason}")
        if affects:
            click.echo(f"  Affects: {', '.join(affects)}")
        if alt:
            click.echo(f"  Alternatives: {', '.join(alt)}")

    @cli.command()
    @click.argument("project")
    @click.argument("name")
    @click.argument("description")
    def pattern(project: str, name: str, description: str):
        """Store a reusable pattern or gotcha.

        Record patterns you discover for future reference.

        Example:
            eri-rpg pattern onetrainer local_files_only \\
                "Always use local_files_only=True with from_pretrained()"
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge, save_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Use v2 knowledge storage
        store = load_knowledge(proj.path, project)
        store.add_pattern(name, description)
        save_knowledge(proj.path, store)

        click.echo(f"✓ Stored pattern: {name}")
        click.echo(f"  {description}")

    @cli.command("patterns")
    @click.argument("project")
    def list_patterns(project: str):
        """List all stored patterns for a project.

        Example:
            eri-rpg patterns myproject
        """
        from erirpg.registry import Registry
        from erirpg.memory import load_knowledge

        registry = Registry.get_instance()
        proj = registry.get(project)

        if not proj:
            click.echo(f"Error: Project '{project}' not found", err=True)
            sys.exit(1)

        # Use v2 knowledge storage
        store = load_knowledge(proj.path, project)
        patterns = store.patterns

        if not patterns:
            click.echo("No patterns stored.")
            click.echo(f"\nAdd one: eri-rpg pattern {project} <name> \"<description>\"")
            return

        click.echo(f"Patterns for {project}:")
        click.echo("=" * 40)
        for name, desc in sorted(patterns.items()):
            click.echo(f"\n• {name}")
            click.echo(f"  {desc}")
