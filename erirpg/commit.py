"""
Verification-gated commit for EriRPG.

The ONLY way to commit changes in EriRPG:
1. Files are edited
2. Verification runs (tests, lint, etc.)
3. IF verification passes → commit
4. IF verification fails → NO commit, show errors

Usage:
    from erirpg.commit import verify_and_commit

    result = verify_and_commit(project_path)
    if result.committed:
        print(f"Committed: {result.commit_hash}")
    else:
        print(f"Verification failed: {result.error}")
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Where PostToolUse hook stores modified files
MODIFIED_FILES_STORE = "/tmp/erirpg-modified-files.json"


@dataclass
class CommitResult:
    """Result of verify_and_commit operation."""
    committed: bool = False
    commit_hash: Optional[str] = None
    files_committed: List[str] = field(default_factory=list)
    verification_passed: bool = False
    verification_output: str = ""
    error: str = ""


def get_modified_files(project_path: str) -> List[str]:
    """Get files modified in this project since last commit."""
    try:
        if os.path.exists(MODIFIED_FILES_STORE):
            with open(MODIFIED_FILES_STORE, "r") as f:
                data = json.load(f)
                if project_path in data:
                    return data[project_path].get("files", [])
    except Exception:
        pass
    return []


def clear_modified_files(project_path: str) -> None:
    """Clear tracked modified files after commit."""
    try:
        if os.path.exists(MODIFIED_FILES_STORE):
            with open(MODIFIED_FILES_STORE, "r") as f:
                data = json.load(f)
            if project_path in data:
                del data[project_path]
                with open(MODIFIED_FILES_STORE, "w") as f:
                    json.dump(data, f, indent=2)
    except Exception:
        pass


def run_verification(project_path: str) -> tuple[bool, str]:
    """
    Run project verification (tests, lint, etc).

    Returns (passed, output).
    """
    from erirpg.verification import (
        load_verification_config,
        Verifier,
        get_default_python_config,
        get_default_node_config,
    )

    # Load verification config
    config = load_verification_config(project_path)

    # Auto-detect if no config
    if not config:
        if Path(project_path, "pyproject.toml").exists() or \
           Path(project_path, "pytest.ini").exists():
            tests_dir = Path(project_path, "tests")
            if tests_dir.exists():
                config = get_default_python_config()
        elif Path(project_path, "package.json").exists():
            config = get_default_node_config()

    if not config or not config.commands:
        # No verification configured - pass by default
        return True, "No verification configured"

    # Run verification
    verifier = Verifier(config, project_path)
    result = verifier.run_verification(step_id="commit", step_type="commit")

    output_lines = []
    for cmd_result in result.command_results:
        status = "PASS" if cmd_result.status == "passed" else "FAIL"
        output_lines.append(f"[{status}] {cmd_result.name}")
        if cmd_result.status != "passed" and cmd_result.stderr:
            output_lines.append(cmd_result.stderr[:500])

    return result.passed, "\n".join(output_lines)


def git_commit(project_path: str, files: List[str], message: str) -> Optional[str]:
    """
    Stage and commit files.

    Returns commit hash on success, None on failure.
    """
    try:
        # Stage files
        subprocess.run(
            ["git", "add"] + files,
            cwd=project_path,
            capture_output=True,
            check=True,
            timeout=30,
        )

        # Check if there's anything to commit
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=project_path,
            capture_output=True,
            timeout=10,
        )

        if status.returncode == 0:
            return None  # Nothing to commit

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_path,
            capture_output=True,
            check=True,
            timeout=30,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_path,
            capture_output=True,
            check=True,
            timeout=10,
        )

        return result.stdout.decode().strip()

    except subprocess.CalledProcessError:
        return None


def verify_and_commit(
    project_path: str,
    message: Optional[str] = None,
    files: Optional[List[str]] = None,
) -> CommitResult:
    """
    Run verification and commit only if it passes.

    This is the ONLY sanctioned way to commit in EriRPG.

    Args:
        project_path: Project directory
        message: Commit message (auto-generated if not provided)
        files: Files to commit (uses tracked files if not provided)

    Returns:
        CommitResult with status and details
    """
    result = CommitResult()

    # Get files to commit
    if files is None:
        files = get_modified_files(project_path)

    if not files:
        result.error = "No modified files to commit"
        return result

    result.files_committed = files

    # Run verification
    passed, output = run_verification(project_path)
    result.verification_passed = passed
    result.verification_output = output

    if not passed:
        result.error = f"Verification failed:\n{output}"
        return result

    # Generate commit message
    if not message:
        file_count = len(files)
        if file_count == 1:
            rel_path = os.path.relpath(files[0], project_path)
            message = f"Update {rel_path}"
        else:
            message = f"Update {file_count} files"
        message += f"\n\nVerification passed at {datetime.now().strftime('%H:%M')}"

    # Commit
    commit_hash = git_commit(project_path, files, message)

    if commit_hash:
        result.committed = True
        result.commit_hash = commit_hash
        clear_modified_files(project_path)
    else:
        result.error = "Git commit failed (nothing to commit?)"

    return result


def must_verify_before_commit(project_path: str) -> bool:
    """Check if there are uncommitted tracked files requiring verification."""
    files = get_modified_files(project_path)
    return len(files) > 0
