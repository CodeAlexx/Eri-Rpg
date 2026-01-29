"""
EriRPG CLI Commands - Modular command structure.

This module provides a clean separation of CLI commands into logical groups.
Each submodule registers its commands when imported.

Structure (26 modules, 91+ commands):
    cli_commands/
    ├── __init__.py      # This file - registration
    ├── setup.py         # add, remove, list, index
    ├── mode.py          # init, graduate, mode, info
    ├── modes.py         # take, work, done, research, execute, new, next
    ├── explore.py       # show, find, impact
    ├── orchestration.py # do, status, validate, diagnose, reset
    ├── knowledge.py     # learn, recall, relearn, history, rollback, decide, pattern, patterns
    ├── metadata.py      # describe, todo, notes, decision, decisions, log, knowledge
    ├── spec_group.py    # spec (new, validate, show, list)
    ├── plan_group.py    # plan (generate, show, list, next, step)
    ├── run_group.py     # run (start, resume, list, show, report, step)
    ├── memory_group.py  # memory (status, search, stale, refresh, migrate)
    ├── verify_group.py  # verify (run, config, results)
    ├── quick.py         # quick, quick-done, quick-cancel, quick-status
    ├── cleanup.py       # cleanup, runs
    ├── install.py       # install, uninstall, install-status
    ├── config_cmd.py    # config
    ├── ui.py            # serve
    ├── transplant.py    # extract, transplant-plan, context
    ├── goal.py          # goal-plan, goal-run, goal-status
    ├── discuss.py       # discuss, discuss-answer, discuss-resolve, discuss-show, discuss-clear
    ├── roadmap.py       # roadmap, roadmap-add, roadmap-next, roadmap-edit
    ├── decisions.py     # log-decision, list-decisions, defer, deferred, promote
    ├── session.py       # session, handoff, gaps
    ├── analyze_cmd.py   # analyze, implement, transplant-feature, describe-feature
    ├── persona_cmd.py   # persona, workflow, ctx, commands
    └── drift.py         # drift-status, enrich-learnings, sync-patterns, sync, drift-patterns, drift-impact

Usage:
    from erirpg.cli_commands import register_all

    @click.group()
    def cli():
        pass

    register_all(cli)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import click


def register_all(cli: "click.Group") -> None:
    """Register all command modules with the CLI group.

    Each module has a `register(cli)` function that adds its commands
    to the CLI group using Click decorators.

    Args:
        cli: The Click group to register commands with
    """
    # Import and register each module
    from . import setup
    from . import mode
    from . import explore
    from . import orchestration
    from . import quick
    from . import cleanup
    from . import install
    from . import config_cmd
    from . import ui
    from . import knowledge
    from . import metadata
    from . import spec_group
    from . import plan_group
    from . import run_group
    from . import memory_group
    from . import verify_group
    from . import modes
    from . import transplant
    from . import goal
    from . import discuss
    from . import roadmap
    from . import decisions
    from . import session
    from . import analyze_cmd
    from . import persona_cmd
    from . import drift
    from . import storage_cmd
    from . import debug_cmd

    setup.register(cli)
    mode.register(cli)
    explore.register(cli)
    orchestration.register(cli)
    quick.register(cli)
    cleanup.register(cli)
    install.register(cli)
    config_cmd.register(cli)
    ui.register(cli)
    knowledge.register(cli)
    metadata.register(cli)
    spec_group.register(cli)
    plan_group.register(cli)
    run_group.register(cli)
    memory_group.register(cli)
    verify_group.register(cli)
    modes.register(cli)
    transplant.register(cli)
    goal.register(cli)
    discuss.register(cli)
    roadmap.register(cli)
    decisions.register(cli)
    session.register(cli)
    analyze_cmd.register(cli)
    persona_cmd.register(cli)
    drift.register(cli)
    storage_cmd.register(cli)
    debug_cmd.register(cli)
