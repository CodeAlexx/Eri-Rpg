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
    python -m erirpg.scripts.lint_skills [--verbose] [--json]
"""

import json
import re
import sys
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
    "remove-project.md",
    "quick.md",
    "pause.md",
    "clone-behavior.md",
    "discuss-phase.md",
    "map-codebase.md",
    "plan-milestone-gaps.md",
    "add-gaps.md",
    "integrate-work.md",
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
    "linter.md",
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


def _resolve_skills_dir(skills_dir: Path | None = None) -> Path:
    """Resolve the skills directory path."""
    return skills_dir or (Path(__file__).parent.parent / "skills")


def collect_lint_results(skills_dir: Path | None = None) -> dict:
    """Collect lint results in a structured format."""
    resolved_skills_dir = _resolve_skills_dir(skills_dir)
    if not resolved_skills_dir.exists():
        raise FileNotFoundError(f"Skills directory not found: {resolved_skills_dir}")

    results: list[LintResult] = []
    skipped: list[str] = []

    for skill_file in sorted(resolved_skills_dir.glob("*.md")):
        if skill_file.name not in STATE_CHANGING_SKILLS:
            skipped.append(skill_file.name)
            continue
        results.append(lint_skill(skill_file))

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    return {
        "ok": len(failed) == 0,
        "skills_dir": str(resolved_skills_dir),
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "state_changing_skills": sorted(STATE_CHANGING_SKILLS),
        "failed_skills": [
            {"skill": r.skill, "missing": r.missing}
            for r in failed
        ],
        "passed_skills": [r.skill for r in passed],
        "checked_skills": [
            {
                "skill": r.skill,
                "passed": r.passed,
                "missing": r.missing,
            }
            for r in results
        ],
        "skipped_skills": skipped,
    }


def print_human_report(report: dict, verbose: bool = False) -> None:
    """Print a human-friendly report to stdout."""
    if verbose:
        for skill in sorted(report["skipped_skills"]):
            print(f"SKIP: {skill} (not state-changing)")

    print(f"\n{'='*60}")
    print("SKILL COMPLETION LINTER")
    print(f"{'='*60}\n")

    if report["failed_skills"]:
        print(f"FAILED ({report['failed']} skills):\n")
        for item in report["failed_skills"]:
            print(f"  ✗ {item['skill']}")
            for issue in item["missing"]:
                print(f"      Missing: {issue}")
            print()

    if report["passed"] and verbose:
        print(f"PASSED ({report['passed']} skills):\n")
        for skill in report["passed_skills"]:
            print(f"  ✓ {skill}")
        print()

    print(f"{'='*60}")
    print(f"Total: {report['total']} | Passed: {report['passed']} | Failed: {report['failed']}")
    print(f"{'='*60}\n")

    if report["failed"]:
        print("Run with --verbose to see all results")
        print("See ~/.claude/eri-rpg/references/command-patterns.md for requirements\n")
    else:
        print("All state-changing skills have proper completion sections!\n")


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
    as_json = "--json" in sys.argv

    try:
        report = collect_lint_results()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report, verbose=verbose)

    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
