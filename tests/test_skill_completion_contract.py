"""Contract tests for state-changing coder skills."""

from pathlib import Path

from erirpg.scripts import lint_skills


def test_state_changing_skills_have_completion_tags():
    """State-changing skills must keep strict <completion> sections."""
    skills_dir = Path(lint_skills.__file__).resolve().parent.parent / "skills"
    missing = []

    for skill_name in sorted(lint_skills.STATE_CHANGING_SKILLS):
        skill_path = skills_dir / skill_name
        assert skill_path.exists(), f"Missing required skill file: {skill_name}"

        content = skill_path.read_text()
        if "<completion>" not in content or "</completion>" not in content:
            missing.append(skill_name)

    assert not missing, f"Missing strict completion tags in: {', '.join(missing)}"


def test_skill_completion_linter_passes():
    """The built-in linter report should be green for tracked skills."""
    report = lint_skills.collect_lint_results()
    assert report["failed"] == 0, f"Linter failures: {report['failed_skills']}"
