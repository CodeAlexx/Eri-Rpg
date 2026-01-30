"""
Level 1 Verification: Existence.

Checks:
- File exists
- File is not empty
- File meets minimum line requirements
"""

import os
from typing import Optional

from erirpg.models.verification_models import ArtifactVerification


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists.

    Args:
        file_path: Absolute path to file

    Returns:
        True if file exists
    """
    return os.path.exists(file_path) and os.path.isfile(file_path)


def check_file_not_empty(file_path: str) -> bool:
    """Check if a file is not empty.

    Args:
        file_path: Absolute path to file

    Returns:
        True if file has content
    """
    if not check_file_exists(file_path):
        return False

    try:
        with open(file_path, "r", errors="replace") as f:
            content = f.read()
        return len(content.strip()) > 0
    except Exception:
        return False


def get_line_count(file_path: str) -> int:
    """Get the number of lines in a file.

    Args:
        file_path: Absolute path to file

    Returns:
        Number of lines (0 if file doesn't exist or can't be read)
    """
    if not check_file_exists(file_path):
        return 0

    try:
        with open(file_path, "r", errors="replace") as f:
            return len(f.readlines())
    except Exception:
        return 0


def verify_artifact_existence(
    file_path: str,
    verification: ArtifactVerification,
) -> None:
    """Verify artifact existence and update verification result.

    Args:
        file_path: Absolute path to file
        verification: ArtifactVerification to update
    """
    verification.exists = check_file_exists(file_path)

    if verification.exists:
        verification.is_empty = not check_file_not_empty(file_path)
        verification.line_count = get_line_count(file_path)
    else:
        verification.is_empty = True
        verification.line_count = 0


def check_minimum_lines(file_path: str, min_lines: int = 10) -> bool:
    """Check if a file has at least the minimum number of lines.

    Stubs typically have < 10 lines.

    Args:
        file_path: Absolute path to file
        min_lines: Minimum line count

    Returns:
        True if file has at least min_lines
    """
    return get_line_count(file_path) >= min_lines


def check_directory_exists(dir_path: str) -> bool:
    """Check if a directory exists.

    Args:
        dir_path: Absolute path to directory

    Returns:
        True if directory exists
    """
    return os.path.exists(dir_path) and os.path.isdir(dir_path)


def check_files_exist_in_directory(
    dir_path: str,
    patterns: list[str] = None,
) -> dict:
    """Check for files in a directory.

    Args:
        dir_path: Absolute path to directory
        patterns: Optional list of glob patterns to match

    Returns:
        Dict with file existence info
    """
    import glob

    result = {
        "directory_exists": check_directory_exists(dir_path),
        "file_count": 0,
        "files": [],
    }

    if not result["directory_exists"]:
        return result

    if patterns:
        for pattern in patterns:
            full_pattern = os.path.join(dir_path, pattern)
            result["files"].extend(glob.glob(full_pattern))
    else:
        result["files"] = [
            f for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
        ]

    result["file_count"] = len(result["files"])
    return result
