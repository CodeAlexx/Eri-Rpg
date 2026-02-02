"""
Review Command - CRITIC persona code review.

Commands:
- review <path>: Review file, directory, or glob with structured output
- review <file> --for-clone --target <project> [--focus <symbol>]: Pre-clone checklist
"""

import json
import os
import click


def register(cli):
    """Register review command with CLI."""
    
    @cli.command("review")
    @click.argument("path")
    @click.option("--full", is_flag=True, help="Use raw source instead of learnings")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    @click.option("--no-cache", "skip_cache", is_flag=True, help="Force re-review even if unchanged")
    @click.option("-p", "--project", default=None, help="Project path for .eri-rpg/")
    @click.option("--for-clone", "for_clone", is_flag=True, help="Clone preparation mode")
    @click.option("--target", "target_project", default="", help="Target project for clone")
    @click.option("--focus", "focus_symbol", default="", help="Focus on specific symbol (class/function)")
    def review_cmd(path: str, full: bool, as_json: bool, skip_cache: bool, project: str,
                   for_clone: bool, target_project: str, focus_symbol: str):
        """Review code with CRITIC persona.
        
        Analyzes target path for risks, contracts, debt, and decisions.
        Outputs structured items tagged [RISK] [CONTRACT] [DEBT] [DECISION].
        
        Saves to .eri-rpg/reviews/<timestamp>.json
        
        \b
        Token discipline:
        - MAX_INPUT_TOKENS = 8000 (what gets analyzed)
        - MAX_OUTPUT_TOKENS = 4000 (output budget)
        - Uses learnings by default for compression
        - Hash-based skip for unchanged files
        
        \b
        Examples:
            eri-rpg review src/auth.py           # single file
            eri-rpg review src/                  # directory
            eri-rpg review "src/**/*.py"         # glob
            eri-rpg review src/auth.py --full    # raw source
            eri-rpg review src/ --json           # JSON output
            eri-rpg review src/ --no-cache       # force re-review
        
        \b
        Clone mode (pre-clone checklist):
            eri-rpg review src/utils.py --for-clone
            eri-rpg review src/utils.py --for-clone --target new-project
            eri-rpg review src/utils.py --for-clone --focus MyClass
        """
        project_path = project or os.getcwd()
        
        # Clone preparation mode
        if for_clone:
            from erirpg.review import review_for_clone
            
            result = review_for_clone(
                source_file=path,
                target_project=target_project,
                focus_symbol=focus_symbol,
                project_path=project_path,
            )
            
            if as_json:
                click.echo(json.dumps(result.to_dict(), indent=2))
            else:
                click.echo(result.to_markdown())
            return
        
        # Standard review mode
        from erirpg.review import review_path
        
        result = review_path(
            path=path,
            use_full=full,
            skip_cache=skip_cache,
            project_path=project_path,
        )
        
        # Output
        if as_json:
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            click.echo(result.to_markdown())
            
            # Show save location
            if not result.skipped_unchanged:
                from erirpg.review import get_reviews_dir
                reviews_dir = get_reviews_dir(project_path)
                click.echo("")
                click.echo(f"Saved to: {reviews_dir}/")
