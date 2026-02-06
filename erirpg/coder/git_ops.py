"""
Git operations for coder workflow.

Commands:
- rollback: Undo execution using git
- diff: Show changes since checkpoint
- compare: Branch management and comparison
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import re

from . import get_planning_dir, timestamp


def run_git(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a git command.

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def is_clean() -> bool:
    """Check if working directory is clean."""
    code, out, _ = run_git(["status", "--porcelain"])
    return code == 0 and not out.strip()


def get_current_branch() -> str:
    """Get current branch name."""
    code, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if code == 0 else "main"


def get_commit_hash(ref: str = "HEAD") -> str:
    """Get commit hash for a ref."""
    code, out, _ = run_git(["rev-parse", "--short", ref])
    return out.strip() if code == 0 else ""


def find_plan_commits(plan_id: str) -> List[Dict[str, str]]:
    """Find commits for a specific plan.

    Args:
        plan_id: Plan identifier like "2-03" or "02-03"

    Returns:
        List of commit dicts with hash, message, files
    """
    # Normalize plan_id
    if "-" in plan_id:
        parts = plan_id.split("-")
        pattern = f"({parts[0].zfill(2)}-{parts[1].zfill(2)})"
    else:
        pattern = f"({plan_id})"

    # Find commits matching pattern
    code, out, _ = run_git([
        "log", "--oneline", "--all",
        f"--grep={pattern}",
        "--format=%H|%s"
    ])

    if code != 0 or not out.strip():
        return []

    commits = []
    for line in out.strip().split("\n"):
        if "|" in line:
            hash_val, msg = line.split("|", 1)
            # Get files for this commit
            _, files_out, _ = run_git(["show", "--name-only", "--format=", hash_val])
            commits.append({
                "hash": hash_val[:7],
                "full_hash": hash_val,
                "message": msg,
                "files": [f for f in files_out.strip().split("\n") if f],
            })

    return commits


def find_phase_commits(phase_num: int) -> List[Dict[str, str]]:
    """Find all commits for a phase.

    Args:
        phase_num: Phase number

    Returns:
        List of commit dicts
    """
    pattern = f"({phase_num:02d}-"

    code, out, _ = run_git([
        "log", "--oneline", "--all",
        f"--grep={pattern}",
        "--format=%H|%s"
    ])

    if code != 0 or not out.strip():
        return []

    commits = []
    for line in out.strip().split("\n"):
        if "|" in line:
            hash_val, msg = line.split("|", 1)
            _, files_out, _ = run_git(["show", "--name-only", "--format=", hash_val])
            commits.append({
                "hash": hash_val[:7],
                "full_hash": hash_val,
                "message": msg,
                "files": [f for f in files_out.strip().split("\n") if f],
            })

    return commits


def find_last_plan_commits() -> List[Dict[str, str]]:
    """Find commits from the last executed plan."""
    # Look for most recent plan-related commit
    code, out, _ = run_git([
        "log", "--oneline", "-20",
        "--format=%H|%s"
    ])

    if code != 0:
        return []

    # Find first commit that looks like a plan commit
    plan_pattern = re.compile(r"\((\d+-\d+)\)")
    last_plan_id = None

    for line in out.strip().split("\n"):
        if "|" in line:
            _, msg = line.split("|", 1)
            match = plan_pattern.search(msg)
            if match:
                last_plan_id = match.group(1)
                break

    if not last_plan_id:
        return []

    return find_plan_commits(last_plan_id)


def find_untracked_commits(since: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find commits NOT made by the coder workflow.

    These are ad-hoc commits (manual fixes, creative sessions, etc.)
    that don't match plan commit patterns (NN-NN) and don't only
    touch .planning/ files.

    Args:
        since: ISO date string to filter commits after (optional).
              If None, searches last 50 commits.

    Returns:
        List of commit dicts newest-first, each with:
        - hash: short hash
        - full_hash: full hash
        - message: commit message
        - date: ISO date string
        - files: list of changed files
    """
    args = ["log", "--oneline", "--no-merges", "-50", "--format=%H|%s|%aI"]
    if since:
        args.append(f"--since={since}")

    code, out, _ = run_git(args)
    if code != 0 or not out.strip():
        return []

    # Plan commits match pattern like (02-03) in message
    plan_pattern = re.compile(r"\(\d+-\d+\)")

    results = []
    for line in out.strip().split("\n"):
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        full_hash, message, date = parts[0], parts[1], parts[2]

        # Skip plan commits
        if plan_pattern.search(message):
            continue

        # Get files changed by this commit
        _, files_out, _ = run_git(["show", "--name-only", "--format=", full_hash])
        files = [f for f in files_out.strip().split("\n") if f]

        # Skip commits that only touch .planning/ files
        if files and all(f.startswith(".planning/") for f in files):
            continue

        results.append({
            "hash": full_hash[:7],
            "full_hash": full_hash,
            "message": message,
            "date": date,
            "files": files,
        })

    return results


def preview_rollback(
    commits: List[Dict[str, str]], project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Preview what a rollback would do.

    Returns:
        Dict with rollback preview information
    """
    if not commits:
        return {"error": "No commits to rollback"}

    # Collect unique files
    all_files = set()
    for commit in commits:
        all_files.update(commit.get("files", []))

    # Determine file actions
    file_actions = []
    for file_path in sorted(all_files):
        # Check if file exists now
        full_path = Path(project_path or Path.cwd()) / file_path
        exists_now = full_path.exists()

        # Check if file existed before these commits
        first_commit = commits[-1]["full_hash"]
        code, _, _ = run_git(["cat-file", "-e", f"{first_commit}^:{file_path}"])
        existed_before = code == 0

        if exists_now and not existed_before:
            action = "delete"
        elif exists_now and existed_before:
            action = "restore"
        else:
            action = "no_change"

        file_actions.append({
            "path": file_path,
            "action": action,
            "exists_now": exists_now,
            "existed_before": existed_before,
        })

    # Find artifacts to update
    planning_dir = get_planning_dir(project_path)
    artifacts = []
    for commit in commits:
        for file_path in commit.get("files", []):
            if file_path.startswith(".planning/"):
                if "SUMMARY.md" in file_path:
                    artifacts.append({"path": file_path, "action": "delete"})

    return {
        "commits": commits,
        "commit_count": len(commits),
        "files": file_actions,
        "file_count": len(all_files),
        "artifacts": artifacts,
    }


def execute_rollback(
    commits: List[Dict[str, str]],
    reason: str = "User requested",
    hard: bool = False,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute a rollback.

    Args:
        commits: List of commits to revert
        reason: Reason for rollback
        hard: Use git reset --hard instead of revert
        project_path: Project path

    Returns:
        Dict with rollback result
    """
    cwd = project_path or Path.cwd()

    # Check for clean state
    if not is_clean():
        return {"error": "Uncommitted changes. Commit or stash first."}

    # Create backup branch
    backup_branch = f"backup-before-rollback-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_git(["branch", backup_branch], cwd=cwd)

    if hard:
        # Find commit before the first commit to revert
        first_commit = commits[-1]["full_hash"]
        code, out, _ = run_git(["rev-parse", f"{first_commit}^"], cwd=cwd)
        if code != 0:
            return {"error": f"Cannot find parent of {first_commit}"}
        target = out.strip()

        code, _, err = run_git(["reset", "--hard", target], cwd=cwd)
        if code != 0:
            return {"error": f"Reset failed: {err}"}

        return {
            "success": True,
            "method": "reset",
            "backup_branch": backup_branch,
            "target": target[:7],
        }
    else:
        # Revert commits (in reverse order)
        hashes = [c["full_hash"] for c in commits]

        # Revert without committing
        code, _, err = run_git(["revert", "--no-commit"] + hashes, cwd=cwd)
        if code != 0:
            # Abort revert on failure
            run_git(["revert", "--abort"], cwd=cwd)
            return {"error": f"Revert failed: {err}"}

        # Create revert commit
        commit_msg = f"""revert: Rollback {len(commits)} commits

Reason: {reason}

Reverted commits:
"""
        for commit in commits:
            commit_msg += f"- {commit['hash']}: {commit['message']}\n"

        commit_msg += "\nCo-Authored-By: Claude <noreply@anthropic.com>"

        code, out, err = run_git(["commit", "-m", commit_msg], cwd=cwd)
        if code != 0:
            return {"error": f"Commit failed: {err}"}

        revert_hash = get_commit_hash("HEAD")

        return {
            "success": True,
            "method": "revert",
            "backup_branch": backup_branch,
            "revert_commit": revert_hash,
            "commits_reverted": len(commits),
        }


def update_state_after_rollback(
    plan_id: Optional[str] = None,
    phase_num: Optional[int] = None,
    project_path: Optional[Path] = None,
) -> None:
    """Update STATE.md and other artifacts after rollback."""
    planning_dir = get_planning_dir(project_path)

    # Delete SUMMARY.md for rolled-back plan
    if plan_id:
        parts = plan_id.split("-")
        phase_num = int(parts[0])
        plan_num = parts[1]

        # Find phase directory
        phases_dir = planning_dir / "phases"
        for d in phases_dir.iterdir() if phases_dir.exists() else []:
            if d.name.startswith(f"{phase_num:02d}-"):
                summary_pattern = f"*-{plan_num}-SUMMARY.md"
                for summary in d.glob(summary_pattern):
                    summary.unlink()

    # Add rollback entry to STATE.md
    state_path = planning_dir / "STATE.md"
    if state_path.exists():
        content = state_path.read_text()
        rollback_entry = f"\n- {timestamp()}: Rolled back"
        if plan_id:
            rollback_entry += f" Plan {plan_id}"
        elif phase_num:
            rollback_entry += f" Phase {phase_num}"

        if "## Rollback History" in content:
            content = content.replace(
                "## Rollback History",
                f"## Rollback History{rollback_entry}"
            )
        else:
            content += f"\n\n## Rollback History{rollback_entry}\n"

        state_path.write_text(content)


def get_diff(
    base: str = "HEAD~1",
    target: str = "HEAD",
    path: Optional[str] = None,
    stat_only: bool = False,
) -> Dict[str, Any]:
    """Get diff between two refs.

    Args:
        base: Base ref (default: HEAD~1)
        target: Target ref (default: HEAD)
        path: Optional path filter
        stat_only: Only return stat summary

    Returns:
        Dict with diff information
    """
    args = ["diff", base, target]
    if stat_only:
        args.append("--stat")
    if path:
        args.extend(["--", path])

    code, out, err = run_git(args)
    if code != 0:
        return {"error": err}

    # Get file list
    _, files_out, _ = run_git(["diff", "--name-only", base, target])
    files = [f for f in files_out.strip().split("\n") if f]

    # Get stats
    _, stats_out, _ = run_git(["diff", "--shortstat", base, target])
    stats = stats_out.strip()

    return {
        "base": base,
        "target": target,
        "diff": out if not stat_only else None,
        "stat": out if stat_only else stats,
        "files": files,
        "file_count": len(files),
    }


def get_diff_since_checkpoint(
    phase: int, plan: Optional[int] = None, project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Get diff since a phase/plan checkpoint.

    Finds the commit at the start of the phase/plan and diffs to HEAD.
    """
    planning_dir = get_planning_dir(project_path)

    # Find checkpoint tag or first commit of phase
    if plan:
        pattern = f"({phase:02d}-{plan:02d})"
    else:
        pattern = f"({phase:02d}-"

    code, out, _ = run_git([
        "log", "--oneline", "--reverse",
        f"--grep={pattern}",
        "--format=%H",
        "-1"
    ])

    if code != 0 or not out.strip():
        return {"error": f"No commits found for phase {phase}"}

    first_commit = out.strip()
    # Get parent of first commit as base
    code, parent, _ = run_git(["rev-parse", f"{first_commit}^"])

    if code != 0:
        return {"error": "Cannot find checkpoint base"}

    return get_diff(base=parent.strip()[:7], target="HEAD")


def compare_branches(branch1: str, branch2: str) -> Dict[str, Any]:
    """Compare two branches.

    Returns:
        Dict with comparison information
    """
    # Get commits unique to each branch
    _, ahead, _ = run_git(["rev-list", "--count", f"{branch2}..{branch1}"])
    _, behind, _ = run_git(["rev-list", "--count", f"{branch1}..{branch2}"])

    # Get diverge point
    _, merge_base, _ = run_git(["merge-base", branch1, branch2])

    # Get diff stats
    _, diff_stat, _ = run_git(["diff", "--stat", branch1, branch2])

    # Get conflicting files (if any)
    _, files_out, _ = run_git(["diff", "--name-only", branch1, branch2])
    files = [f for f in files_out.strip().split("\n") if f]

    return {
        "branch1": branch1,
        "branch2": branch2,
        "ahead": int(ahead.strip()) if ahead.strip().isdigit() else 0,
        "behind": int(behind.strip()) if behind.strip().isdigit() else 0,
        "merge_base": merge_base.strip()[:7] if merge_base else None,
        "diff_stat": diff_stat,
        "files_changed": files,
        "file_count": len(files),
    }


def create_comparison_branch(
    base_branch: str, name: str, project_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Create a new branch for comparison/experimentation."""
    cwd = project_path or Path.cwd()

    # Create branch
    code, _, err = run_git(["checkout", "-b", name, base_branch], cwd=cwd)
    if code != 0:
        return {"error": f"Failed to create branch: {err}"}

    return {
        "success": True,
        "branch": name,
        "base": base_branch,
    }


def list_branches() -> List[Dict[str, Any]]:
    """List all branches with metadata."""
    code, out, _ = run_git([
        "for-each-ref",
        "--sort=-committerdate",
        "refs/heads/",
        "--format=%(refname:short)|%(committerdate:relative)|%(subject)"
    ])

    if code != 0:
        return []

    branches = []
    current = get_current_branch()

    for line in out.strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            name = parts[0]
            branches.append({
                "name": name,
                "current": name == current,
                "last_commit": parts[1] if len(parts) > 1 else "",
                "message": parts[2] if len(parts) > 2 else "",
            })

    return branches
