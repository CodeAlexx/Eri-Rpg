#!/usr/bin/env python3
"""
Skill Completion Linter

Validates that all state-changing coder skills have proper completion sections
per ~/.claude/eri-rpg/references/command-patterns.md.

Required patterns for state-changing skills:
1. <completion> section exists
2. Contains STATE.md update
3. Contains `switch` command for global state
4. Contains /clear box pattern (━━━ or ═══ border)

Usage:
    python -m erirpg.scripts.lint_skills [--fix] [--verbose]
"""

import sys
import re
from pathlib import Path
from typing import NamedTuple

# Skills that change project state and MUST have completion sections
STATE_CHANGING_SKILLS = {
    "execute-phase.md",
    "plan-phase.md",
    "new-project.md",
    "verify-work.md",
    "complete-milestone.md",
    "add-phase.md",
    "add-feature.md",
    "new-milestone.md",
    "insert-phase.md",
    "remove-phase.md",
    "quick.md",
    "pause.md",
    "clone-behavior.md",
    "discuss-phase.md",
    "map-codebase.md",
    "plan-milestone-gaps.md",
}

# Skills that are read-only or utility (no completion required)
READ_ONLY_SKILLS = {
    "init.md",
    "help.md",
    "progress.md",
    "metrics.md",
    "history.md",
    "settings.md",
    "list-phase-assumptions.md",
    "projects.md",
    "diff.md",
    "compare.md",
    "cost.md",
    "blueprint.md",
    "learn.md",
    "handoff.md",
    "debug.md",
    "add-todo.md",
    "switch-project.md",
    "replay.md",
    "verify-behavior.md",
    "rollback.md",
    "template.md",
    "split.md",
    "meta-edit.md",
    "resume.md",
    "merge.md",
}


class LintResult(NamedTuple):
    skill: str
    has_completion: bool
    has_state_update: bool
    has_switch_cmd: bool
    has_clear_box: bool

    @property
    def passed(self) -> bool:
        return all([
            self.has_completion,
            self.has_state_update,
            self.has_switch_cmd,
            self.has_clear_box,
        ])

    @property
    def missing(self) -> list[str]:
        issues = []
        if not self.has_completion:
            issues.append("<completion> section")
        if not self.has_state_update:
            issues.append("STATE.md update")
        if not self.has_switch_cmd:
            issues.append("switch command")
        if not self.has_clear_box:
            issues.append("/clear box")
        return issues


def lint_skill(path: Path) -> LintResult:
    """Check a skill file for required completion patterns."""
    content = path.read_text()

    # Check for <completion> section
    has_completion = "<completion>" in content and "</completion>" in content

    # Check for STATE.md update (various patterns)
    state_patterns = [
        r"STATE\.md",
        r"Update.*STATE",
        r"state.*update",
    ]
    has_state_update = any(re.search(p, content, re.IGNORECASE) for p in state_patterns)

    # Check for switch command (global state update)
    switch_patterns = [
        r"erirpg\.cli\s+switch",
        r"python3\s+-m\s+erirpg\.cli\s+switch",
        r"Update Global State",
    ]
    has_switch_cmd = any(re.search(p, content) for p in switch_patterns)

    # Check for /clear box (visual border characters)
    clear_box_patterns = [
        r"━━━.*━━━",  # Heavy horizontal lines
        r"═══.*═══",  # Double horizontal lines
        r"╔═.*═╗",    # Box drawing
        r"/clear",    # Direct mention
        r"1\.\s*Type:\s*/clear",  # Instruction format
    ]
    has_clear_box = any(re.search(p, content) for p in clear_box_patterns)

    return LintResult(
        skill=path.name,
        has_completion=has_completion,
        has_state_update=has_state_update,
        has_switch_cmd=has_switch_cmd,
        has_clear_box=has_clear_box,
    )


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # Find skills directory
    skills_dir = Path(__file__).parent.parent / "skills"
    if not skills_dir.exists():
        print(f"ERROR: Skills directory not found: {skills_dir}")
        sys.exit(1)

    # Lint all state-changing skills
    results: list[LintResult] = []
    for skill_file in sorted(skills_dir.glob("*.md")):
        if skill_file.name not in STATE_CHANGING_SKILLS:
            if verbose:
                print(f"SKIP: {skill_file.name} (not state-changing)")
            continue

        result = lint_skill(skill_file)
        results.append(result)

    # Report results
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(f"\n{'='*60}")
    print(f"SKILL COMPLETION LINTER")
    print(f"{'='*60}\n")

    if failed:
        print(f"FAILED ({len(failed)} skills):\n")
        for r in failed:
            print(f"  ✗ {r.skill}")
            for issue in r.missing:
                print(f"      Missing: {issue}")
            print()

    if passed and verbose:
        print(f"PASSED ({len(passed)} skills):\n")
        for r in passed:
            print(f"  ✓ {r.skill}")
        print()

    # Summary
    total = len(results)
    print(f"{'='*60}")
    print(f"Total: {total} | Passed: {len(passed)} | Failed: {len(failed)}")
    print(f"{'='*60}\n")

    if failed:
        print("Run with --verbose to see all results")
        print("See ~/.claude/eri-rpg/references/command-patterns.md for requirements\n")
        sys.exit(1)
    else:
        print("All state-changing skills have proper completion sections!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
