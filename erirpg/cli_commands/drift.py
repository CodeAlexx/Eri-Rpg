"""
Drift Commands - Drift integration and pattern synchronization.

Commands (full tier):
- drift-status: Check Drift integration status for a project
- enrich-learnings: Enrich stored learnings with Drift pattern data
- sync-patterns: Sync patterns between EriRPG and Drift
- sync: Synchronize knowledge.json with codebase files
- drift-patterns: List patterns from Drift for a project
- drift-impact: Show impact analysis for changing a file
"""

import json
import os
import sys
import click

from erirpg.cli_commands.guards import tier_required


def register(cli):
    """Register drift commands with CLI."""
    from erirpg.registry import Registry

    registry = Registry.get_instance()

    @cli.command(name="drift-status")
    @click.argument("project", required=False)
    @tier_required("full")
    def drift_status_cmd(project: str = None):
        """Check Drift integration status for a project.

        Shows whether Drift is available, patterns detected, and sync status.

        Examples:
            eri-rpg drift-status onetrainer
            eri-rpg drift-status  # uses current directory
        """
        from erirpg.memory import get_drift_status
        from erirpg.pattern_sync import get_sync_status

        # Get project path
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
        else:
            project_path = os.getcwd()

        # Get Drift status
        status = get_drift_status(project_path)
        sync_status = get_sync_status(project_path)

        click.echo("=" * 60)
        click.echo("Drift Integration Status")
        click.echo("=" * 60)
        click.echo("")

        # Drift availability
        if status.get("available"):
            click.echo("✅ Drift CLI: Available")
            if status.get("last_scan"):
                click.echo(f"   Last scan: {status['last_scan']}")
        else:
            click.echo("❌ Drift CLI: Not available")
            if not status.get("drift_dir_exists"):
                click.echo("   Run 'drift scan' to initialize")
            click.echo("")
            click.echo("To install Drift:")
            click.echo("   npm install -g @dadbodgeoff/drift")
            click.echo("   # or")
            click.echo("   npx @dadbodgeoff/drift scan")

        click.echo("")

        # Pattern counts
        patterns = status.get("patterns", {})
        if patterns:
            total = patterns.get("total", 0)
            click.echo(f"Patterns detected: {total}")
            by_category = patterns.get("by_category", {})
            if by_category:
                for cat, count in sorted(by_category.items(), key=lambda x: -x[1])[:5]:
                    click.echo(f"   {cat}: {count}")

        click.echo("")

        # Sync status
        click.echo("Pattern Sync:")
        eri = sync_status.get("eri_rpg", {})
        drift = sync_status.get("drift", {})

        click.echo(f"   EriRPG patterns: {eri.get('pattern_count', 0)}")
        click.echo(f"   Imported from Drift: {eri.get('drift_patterns_count', 0)}")
        click.echo(f"   Drift patterns: {drift.get('pattern_count', 0)}")
        click.echo(f"   Exported to Drift: {drift.get('custom_count', 0)}")

        if sync_status.get("sync_possible"):
            click.echo("")
            click.echo("Run 'eri-rpg sync-patterns' to synchronize")

    @cli.command(name="enrich-learnings")
    @click.argument("project", required=False)
    @click.option("--force", is_flag=True, help="Re-enrich even if already validated")
    def enrich_learnings_cmd(project: str = None, force: bool = False):
        """Enrich stored learnings with Drift pattern data.

        Adds confidence scores, pattern IDs, and outlier status to
        existing learnings by querying Drift.

        Examples:
            eri-rpg enrich-learnings onetrainer
            eri-rpg enrich-learnings --force  # re-enrich all
        """
        from erirpg.memory import enrich_learnings_batch

        # Get project path
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
        else:
            project_path = os.getcwd()

        click.echo("Enriching learnings with Drift data...")

        stats = enrich_learnings_batch(project_path, force=force)

        if not stats.get("drift_available"):
            click.echo("❌ Drift not available for this project")
            click.echo("   Run 'drift scan' first")
            return

        click.echo("")
        click.echo(f"✅ Enriched: {stats['enriched']}")
        click.echo(f"⏭️  Skipped (already validated): {stats['skipped']}")

        if stats['failed'] > 0:
            click.echo(f"❌ Failed: {stats['failed']}")

        click.echo("")
        click.echo("Learnings now have:")
        click.echo("  - drift_confidence: Pattern match confidence score")
        click.echo("  - drift_pattern_id: Matching pattern ID")
        click.echo("  - is_outlier: Whether code deviates from patterns")

    @cli.command(name="sync-patterns")
    @click.argument("project", required=False)
    @click.option(
        "--direction",
        type=click.Choice(["both", "to_drift", "from_drift"]),
        default="both",
        help="Sync direction"
    )
    def sync_patterns_cmd(project: str = None, direction: str = "both"):
        """Sync patterns between EriRPG and Drift.

        - from_drift: Import Drift patterns into EriRPG
        - to_drift: Export EriRPG patterns to Drift's custom directory
        - both: Bidirectional sync (default)

        Examples:
            eri-rpg sync-patterns onetrainer
            eri-rpg sync-patterns --direction from_drift
        """
        from erirpg.pattern_sync import sync_patterns, get_sync_status

        # Get project path
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
        else:
            project_path = os.getcwd()

        # Check sync is possible
        sync_status = get_sync_status(project_path)
        if not sync_status.get("sync_possible"):
            click.echo("No patterns found in either EriRPG or Drift")
            click.echo("Run 'eri-rpg analyze' or 'drift scan' first")
            return

        click.echo(f"Syncing patterns ({direction})...")

        result = sync_patterns(project_path, direction)

        click.echo("")
        if direction in ("from_drift", "both"):
            click.echo(f"📥 Imported from Drift: {result.imported}")

        if direction in ("to_drift", "both"):
            click.echo(f"📤 Exported to Drift: {result.exported}")

        if result.errors:
            click.echo("")
            click.echo("Errors:")
            for err in result.errors:
                click.echo(f"   ❌ {err}")

        click.echo("")
        click.echo("Patterns are now synchronized.")
        click.echo("EriRPG learnings can use Drift confidence scores.")
        click.echo("Drift can use EriRPG extension points and registries.")

    @cli.command(name="sync")
    @click.argument("project", required=False)
    @click.option("--learn", is_flag=True, help="Auto-learn unknown/stale files")
    @click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @click.option("--lang", type=click.Choice(["python", "rust", "c", "mojo", "dart"]),
                  help="Limit to specific language")
    def sync_cmd(project: str = None, learn: bool = False, verbose: bool = False,
                 as_json: bool = False, lang: str = None):
        """Synchronize knowledge.json with codebase files.

        Scans all source files and compares against existing learnings:

        \b
        - Known:   File exists and hash matches stored learning
        - Stale:   File exists but content has changed
        - Unknown: File exists but no learning stored
        - Deleted: Learning exists but file was removed

        Use --learn to automatically parse and learn unknown/stale files.

        \b
        Examples:
            eri-rpg sync                    # Show status for current directory
            eri-rpg sync onetrainer         # Show status for named project
            eri-rpg sync --learn            # Auto-learn unknown/stale files
            eri-rpg sync --learn --verbose  # Learn with detailed output
            eri-rpg sync --json             # Output as JSON for scripting
            eri-rpg sync --lang python      # Only scan Python files
        """
        from erirpg.sync import sync_knowledge, sync_and_learn

        # Get project path and name
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
            project_name = project
        else:
            project_path = os.getcwd()
            project_name = os.path.basename(project_path)

        # Check .eri-rpg directory exists
        eri_dir = os.path.join(project_path, ".eri-rpg")
        if not os.path.exists(eri_dir):
            click.echo(f"Warning: No .eri-rpg directory found at {project_path}")
            click.echo("Creating .eri-rpg directory...")
            os.makedirs(eri_dir, exist_ok=True)

        if learn:
            # Sync and auto-learn
            if not as_json:
                click.echo(f"Scanning {project_path}...")
            result = sync_and_learn(project_path, project_name, lang, verbose)
        else:
            # Just sync status
            if not as_json:
                click.echo(f"Scanning {project_path}...")
            result = sync_knowledge(project_path, project_name, lang, verbose)

        # Output results
        if as_json:
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            click.echo("")
            click.echo(result.summary())

            # Show first few items in each category if verbose
            if verbose:
                if result.unknown:
                    click.echo("")
                    click.echo("Unknown files (sample):")
                    for status in result.unknown[:10]:
                        click.echo(f"  - {status.path}")
                    if len(result.unknown) > 10:
                        click.echo(f"  ... and {len(result.unknown) - 10} more")

                if result.stale:
                    click.echo("")
                    click.echo("Stale files (sample):")
                    for status in result.stale[:10]:
                        click.echo(f"  - {status.path}")
                    if len(result.stale) > 10:
                        click.echo(f"  ... and {len(result.stale) - 10} more")

                if result.deleted:
                    click.echo("")
                    click.echo("Deleted files:")
                    for status in result.deleted[:10]:
                        click.echo(f"  - {status.path}")
                    if len(result.deleted) > 10:
                        click.echo(f"  ... and {len(result.deleted) - 10} more")

    @cli.command(name="drift-patterns")
    @click.argument("project", required=False)
    @click.option("--category", "-c", help="Filter by category")
    def drift_patterns_cmd(project: str = None, category: str = None):
        """List patterns from Drift for a project.

        Shows patterns detected by Drift with confidence scores.

        Examples:
            eri-rpg drift-patterns onetrainer
            eri-rpg drift-patterns --category api
        """
        from erirpg.pattern_sync import get_all_patterns

        # Get project path
        if project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
        else:
            project_path = os.getcwd()

        all_patterns = get_all_patterns(project_path)
        combined = all_patterns.get("combined", [])

        if not combined:
            click.echo("No patterns found. Run 'drift scan' or 'eri-rpg analyze' first.")
            return

        # Filter by category
        if category:
            combined = [p for p in combined if p.get("category", "").lower() == category.lower()]

        click.echo("=" * 70)
        click.echo(f"{'ID':<35} {'Category':<12} {'Conf':<6} {'Source':<10}")
        click.echo("=" * 70)

        for p in combined[:30]:  # Limit to 30
            pid = p.get("id", "unknown")[:34]
            cat = p.get("category", "unknown")[:11]
            conf = f"{p.get('confidence', 0):.2f}"
            source = p.get("source", "unknown")[:9]
            click.echo(f"{pid:<35} {cat:<12} {conf:<6} {source:<10}")

        if len(combined) > 30:
            click.echo(f"... and {len(combined) - 30} more")

        click.echo("")
        click.echo(f"Total: {len(combined)} patterns")

    @cli.command(name="drift-impact")
    @click.argument("project", required=False)
    @click.argument("file_path")
    def drift_impact_cmd(project: str = None, file_path: str = None):
        """Show impact analysis for changing a file.

        Uses Drift's call graph to show what other files would be
        affected by changes to the specified file.

        Examples:
            eri-rpg drift-impact onetrainer training/scheduler.py
            eri-rpg drift-impact src/api/users.ts
        """
        try:
            from erirpg.drift_bridge import DriftBridge
        except ImportError:
            click.echo("Error: drift_bridge module not available", err=True)
            sys.exit(1)

        # Get project path
        if project and ':' in project:
            # No project specified, first arg is the file
            file_path = project
            project_path = os.getcwd()
        elif project:
            proj = registry.get(project)
            if not proj:
                click.echo(f"Error: Project '{project}' not found", err=True)
                sys.exit(1)
            project_path = proj.path
        else:
            project_path = os.getcwd()

        bridge = DriftBridge(project_path)

        if not bridge.is_available():
            click.echo("❌ Drift not available for this project")
            click.echo("   Run 'drift scan' first")
            return

        click.echo(f"Analyzing impact of changes to: {file_path}")
        click.echo("")

        impact = bridge.impact_analysis(file_path)

        click.echo(f"Risk Level: {impact.risk_level.upper()}")
        click.echo(f"Coupling Score: {impact.coupling_score:.2f}")
        click.echo("")

        if impact.affected_files:
            click.echo(f"Affected Files ({len(impact.affected_files)}):")
            for f in impact.affected_files[:15]:
                click.echo(f"   - {f}")
            if len(impact.affected_files) > 15:
                click.echo(f"   ... and {len(impact.affected_files) - 15} more")
        else:
            click.echo("No other files affected (isolated change)")

        if impact.affected_functions:
            click.echo("")
            click.echo(f"Affected Functions ({len(impact.affected_functions)}):")
            for f in impact.affected_functions[:10]:
                click.echo(f"   - {f}")
            if len(impact.affected_functions) > 10:
                click.echo(f"   ... and {len(impact.affected_functions) - 10} more")
