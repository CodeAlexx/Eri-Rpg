"""
Verification system for EriRPG.

Executes verification commands (lint, test, etc.) and collects results
to gate runner progress and ensure code quality.

Usage:
    verifier = Verifier(config)
    result = verifier.run_step_verification(step)
    if not result.passed:
        print(f"Verification failed: {result.output}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json
import os
import subprocess
import shlex

if TYPE_CHECKING:
    from erirpg.graph import Graph


class VerificationStatus(Enum):
    """Status of a verification run."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class VerificationCommand:
    """A single verification command to run."""
    name: str
    command: str
    working_dir: str = ""
    timeout: int = 300  # 5 minutes default
    required: bool = True  # If false, failure doesn't block progress
    run_on: List[str] = field(default_factory=list)  # Step types to run on, empty = all

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "working_dir": self.working_dir,
            "timeout": self.timeout,
            "required": self.required,
            "run_on": self.run_on,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationCommand":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            command=data.get("command", ""),
            working_dir=data.get("working_dir", ""),
            timeout=data.get("timeout", 300),
            required=data.get("required", True),
            run_on=data.get("run_on", []),
        )


@dataclass
class CommandResult:
    """Result of running a single verification command."""
    name: str
    command: str
    status: str = "pending"  # VerificationStatus value
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandResult":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            command=data.get("command", ""),
            status=data.get("status", "pending"),
            exit_code=data.get("exit_code", 0),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message", ""),
        )

    @property
    def passed(self) -> bool:
        """Check if command passed."""
        return self.status == VerificationStatus.PASSED.value

    @property
    def duration(self) -> Optional[float]:
        """Get command duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class VerificationResult:
    """Result of running all verification commands for a step."""
    step_id: str
    status: str = "pending"  # VerificationStatus value
    command_results: List[CommandResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "command_results": [r.to_dict() for r in self.command_results],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Deserialize from dictionary."""
        return cls(
            step_id=data.get("step_id", ""),
            status=data.get("status", "pending"),
            command_results=[CommandResult.from_dict(r) for r in data.get("command_results", [])],
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )

    @property
    def passed(self) -> bool:
        """Check if all required commands passed."""
        return self.status == VerificationStatus.PASSED.value

    @property
    def failed_commands(self) -> List[CommandResult]:
        """Get list of failed command results."""
        return [r for r in self.command_results if r.status == VerificationStatus.FAILED.value]

    def format_report(self) -> str:
        """Format a human-readable report."""
        lines = [
            f"Verification Report: {self.step_id}",
            "=" * 50,
            f"Status: {self.status}",
        ]

        if self.started_at:
            lines.append(f"Started: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.completed_at:
            lines.append(f"Completed: {self.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        lines.append("")
        lines.append("Commands:")

        for result in self.command_results:
            status_icon = {
                "passed": "✓",
                "failed": "✗",
                "skipped": "○",
                "error": "!",
                "pending": "?",
            }.get(result.status, "?")

            lines.append(f"  {status_icon} {result.name}")
            lines.append(f"    Command: {result.command}")
            lines.append(f"    Exit code: {result.exit_code}")

            if result.duration:
                lines.append(f"    Duration: {result.duration:.2f}s")

            if result.error_message:
                lines.append(f"    Error: {result.error_message}")

            if result.stdout.strip():
                lines.append("    Output:")
                for line in result.stdout.strip().split("\n")[:10]:  # First 10 lines
                    lines.append(f"      {line}")
                if len(result.stdout.strip().split("\n")) > 10:
                    lines.append("      ... (truncated)")

            if result.stderr.strip():
                lines.append("    Errors:")
                for line in result.stderr.strip().split("\n")[:10]:
                    lines.append(f"      {line}")
                if len(result.stderr.strip().split("\n")) > 10:
                    lines.append("      ... (truncated)")

        return "\n".join(lines)


@dataclass
class VerificationConfig:
    """Configuration for verification commands."""
    commands: List[VerificationCommand] = field(default_factory=list)
    run_after_each_step: bool = False
    run_at_checkpoints: bool = True
    stop_on_failure: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "commands": [c.to_dict() for c in self.commands],
            "run_after_each_step": self.run_after_each_step,
            "run_at_checkpoints": self.run_at_checkpoints,
            "stop_on_failure": self.stop_on_failure,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationConfig":
        """Deserialize from dictionary."""
        return cls(
            commands=[VerificationCommand.from_dict(c) for c in data.get("commands", [])],
            run_after_each_step=data.get("run_after_each_step", False),
            run_at_checkpoints=data.get("run_at_checkpoints", True),
            stop_on_failure=data.get("stop_on_failure", True),
        )

    def validate(self) -> List[str]:
        """Validate the configuration."""
        errors = []
        for i, cmd in enumerate(self.commands):
            if not cmd.name:
                errors.append(f"Command {i}: name is required")
            if not cmd.command:
                errors.append(f"Command {i}: command is required")
            if cmd.timeout <= 0:
                errors.append(f"Command {i}: timeout must be positive")
        return errors

    def get_commands_for_step(self, step_type: str) -> List[VerificationCommand]:
        """Get commands that should run for a given step type."""
        return [
            cmd for cmd in self.commands
            if not cmd.run_on or step_type in cmd.run_on
        ]


class Verifier:
    """Executes verification commands."""

    def __init__(self, config: VerificationConfig, project_path: str):
        self.config = config
        self.project_path = project_path

    def run_command(self, cmd: VerificationCommand) -> CommandResult:
        """Run a single verification command."""
        result = CommandResult(
            name=cmd.name,
            command=cmd.command,
            started_at=datetime.now(),
        )

        # Determine working directory
        working_dir = cmd.working_dir or self.project_path
        if not os.path.isabs(working_dir):
            working_dir = os.path.join(self.project_path, working_dir)

        try:
            # Run the command
            process = subprocess.run(
                cmd.command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=cmd.timeout,
            )

            result.exit_code = process.returncode
            result.stdout = process.stdout
            result.stderr = process.stderr
            result.completed_at = datetime.now()

            if process.returncode == 0:
                result.status = VerificationStatus.PASSED.value
            else:
                result.status = VerificationStatus.FAILED.value

        except subprocess.TimeoutExpired:
            result.status = VerificationStatus.ERROR.value
            result.error_message = f"Command timed out after {cmd.timeout} seconds"
            result.completed_at = datetime.now()

        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.error_message = str(e)
            result.completed_at = datetime.now()

        return result

    def run_verification(
        self,
        step_id: str,
        step_type: str = "",
    ) -> VerificationResult:
        """Run all applicable verification commands for a step.

        Args:
            step_id: ID of the step being verified
            step_type: Type of step (used to filter commands)

        Returns:
            VerificationResult with all command results
        """
        result = VerificationResult(
            step_id=step_id,
            started_at=datetime.now(),
        )

        # Get applicable commands
        commands = self.config.get_commands_for_step(step_type) if step_type else self.config.commands

        if not commands:
            result.status = VerificationStatus.SKIPPED.value
            result.completed_at = datetime.now()
            return result

        # Run each command
        all_passed = True
        for cmd in commands:
            cmd_result = self.run_command(cmd)
            result.command_results.append(cmd_result)

            # Check if this failure should stop progress
            if not cmd_result.passed and cmd.required:
                all_passed = False
                if self.config.stop_on_failure:
                    break

        result.completed_at = datetime.now()
        result.status = VerificationStatus.PASSED.value if all_passed else VerificationStatus.FAILED.value

        return result

    def should_run_for_step(self, is_checkpoint: bool = False) -> bool:
        """Determine if verification should run based on config."""
        if self.config.run_after_each_step:
            return True
        if is_checkpoint and self.config.run_at_checkpoints:
            return True
        return False


# =============================================================================
# Verification Storage
# =============================================================================

def save_verification_result(
    project_path: str,
    run_id: str,
    result: VerificationResult,
) -> str:
    """Save verification result to run directory.

    Args:
        project_path: Path to the project
        run_id: ID of the run
        result: VerificationResult to save

    Returns:
        Path to the saved file
    """
    from erirpg.runs import get_run_dir

    verification_dir = os.path.join(get_run_dir(project_path, run_id), "verification")
    os.makedirs(verification_dir, exist_ok=True)

    file_path = os.path.join(verification_dir, f"{result.step_id}.json")
    with open(file_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    return file_path


def load_verification_result(
    project_path: str,
    run_id: str,
    step_id: str,
) -> Optional[VerificationResult]:
    """Load verification result from run directory.

    Args:
        project_path: Path to the project
        run_id: ID of the run
        step_id: ID of the step

    Returns:
        VerificationResult or None if not found
    """
    from erirpg.runs import get_run_dir

    file_path = os.path.join(
        get_run_dir(project_path, run_id),
        "verification",
        f"{step_id}.json"
    )

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    return VerificationResult.from_dict(data)


def list_verification_results(
    project_path: str,
    run_id: str,
) -> List[VerificationResult]:
    """List all verification results for a run.

    Args:
        project_path: Path to the project
        run_id: ID of the run

    Returns:
        List of VerificationResults
    """
    from erirpg.runs import get_run_dir

    verification_dir = os.path.join(get_run_dir(project_path, run_id), "verification")

    if not os.path.exists(verification_dir):
        return []

    results = []
    for filename in os.listdir(verification_dir):
        if filename.endswith(".json"):
            step_id = filename[:-5]  # Remove .json
            result = load_verification_result(project_path, run_id, step_id)
            if result:
                results.append(result)

    return results


def format_verification_summary(results: List[VerificationResult]) -> str:
    """Format a summary of all verification results.

    Args:
        results: List of verification results

    Returns:
        Formatted summary string
    """
    if not results:
        return "No verification results."

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if r.status == VerificationStatus.FAILED.value)
    skipped = sum(1 for r in results if r.status == VerificationStatus.SKIPPED.value)

    lines = [
        "Verification Summary",
        "=" * 40,
        f"Total: {len(results)}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        f"Skipped: {skipped}",
        "",
    ]

    if failed > 0:
        lines.append("Failed Steps:")
        for result in results:
            if result.status == VerificationStatus.FAILED.value:
                lines.append(f"  • {result.step_id}")
                for cmd_result in result.failed_commands:
                    lines.append(f"    - {cmd_result.name}: {cmd_result.error_message or 'exit code ' + str(cmd_result.exit_code)}")

    return "\n".join(lines)


# =============================================================================
# Config Loading
# =============================================================================

def load_verification_config(project_path: str) -> Optional[VerificationConfig]:
    """Load verification config from project.

    Looks for .eri-rpg/verification.json or verification section in project config.

    Args:
        project_path: Path to the project

    Returns:
        VerificationConfig or None if not found
    """
    # Try dedicated verification config
    config_path = os.path.join(project_path, ".eri-rpg", "verification.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)
        return VerificationConfig.from_dict(data)

    # Try project config
    project_config_path = os.path.join(project_path, ".eri-rpg", "config.json")
    if os.path.exists(project_config_path):
        with open(project_config_path, "r") as f:
            project_data = json.load(f)
        if "verification" in project_data:
            return VerificationConfig.from_dict(project_data["verification"])

    return None


def save_verification_config(project_path: str, config: VerificationConfig) -> str:
    """Save verification config to project.

    Args:
        project_path: Path to the project
        config: VerificationConfig to save

    Returns:
        Path to the saved file
    """
    config_dir = os.path.join(project_path, ".eri-rpg")
    os.makedirs(config_dir, exist_ok=True)

    config_path = os.path.join(config_dir, "verification.json")
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)

    return config_path


# =============================================================================
# Default Configurations
# =============================================================================

def get_default_python_config() -> VerificationConfig:
    """Get default verification config for Python projects."""
    return VerificationConfig(
        commands=[
            VerificationCommand(
                name="lint",
                command="ruff check .",
                required=False,
            ),
            VerificationCommand(
                name="type-check",
                command="mypy .",
                required=False,
            ),
            VerificationCommand(
                name="test",
                command="pytest",
                required=True,
            ),
        ],
        run_after_each_step=False,
        run_at_checkpoints=True,
        stop_on_failure=True,
    )


def get_default_node_config() -> VerificationConfig:
    """Get default verification config for Node.js projects."""
    return VerificationConfig(
        commands=[
            VerificationCommand(
                name="lint",
                command="npm run lint",
                required=False,
            ),
            VerificationCommand(
                name="type-check",
                command="npm run typecheck",
                required=False,
            ),
            VerificationCommand(
                name="test",
                command="npm test",
                required=True,
            ),
        ],
        run_after_each_step=False,
        run_at_checkpoints=True,
        stop_on_failure=True,
    )


# =============================================================================
# Smart Test Selection
# =============================================================================

def find_relevant_tests(
    changed_files: List[str],
    project_path: str,
    test_dirs: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Find test files that import any of the changed files.

    This enables running only relevant tests instead of the full suite,
    significantly speeding up verification on large projects.

    Args:
        changed_files: List of changed file paths (relative to project)
        project_path: Root path of the project
        test_dirs: Optional list of test directories to search.
                   Defaults to ["tests", "test", "spec"]

    Returns:
        List of relevant test file paths, or None to run all tests
        (None means no relevant tests found OR couldn't determine)
    """
    from pathlib import Path
    import re

    if not changed_files:
        return None  # Run all tests

    if test_dirs is None:
        test_dirs = ["tests", "test", "spec"]

    project = Path(project_path)
    relevant_tests = set()

    # Extract module names from changed files
    # e.g., "src/auth/login.py" -> ["login", "auth.login", "auth"]
    module_patterns = []
    for changed in changed_files:
        changed_path = Path(changed)
        stem = changed_path.stem  # filename without extension

        # Skip __init__ files
        if stem == "__init__":
            continue

        # Add the base module name
        module_patterns.append(stem)

        # Add parent.module pattern (e.g., auth.login)
        if len(changed_path.parts) > 1:
            parent = changed_path.parts[-2]
            if parent not in ("src", "lib", "app"):
                module_patterns.append(f"{parent}.{stem}")
                module_patterns.append(parent)

    if not module_patterns:
        return None  # Can't determine relevant tests

    # Build regex pattern for import detection
    # Matches: import X, from X import, from X.Y import
    import_patterns = []
    for mod in module_patterns:
        escaped = re.escape(mod)
        import_patterns.extend([
            rf'\bimport\s+{escaped}\b',
            rf'\bfrom\s+{escaped}\b',
            rf'\bfrom\s+\w+\.{escaped}\b',
            rf'["\']\.?\/?{escaped}["\']',  # JS/TS imports
        ])

    combined_pattern = re.compile('|'.join(import_patterns), re.IGNORECASE)

    # Search test directories
    for test_dir_name in test_dirs:
        test_dir = project / test_dir_name
        if not test_dir.exists():
            continue

        # Find test files (Python, JS, TS, Rust)
        test_patterns = [
            "test_*.py", "*_test.py",
            "*.test.js", "*.test.ts", "*.test.tsx",
            "*.spec.js", "*.spec.ts", "*.spec.tsx",
            "*_test.rs",
        ]

        for pattern in test_patterns:
            for test_file in test_dir.rglob(pattern):
                try:
                    content = test_file.read_text(errors='replace')
                    if combined_pattern.search(content):
                        # Convert to relative path
                        rel_path = str(test_file.relative_to(project))
                        relevant_tests.add(rel_path)
                except Exception:
                    continue  # Skip unreadable files

    if not relevant_tests:
        return None  # No relevant tests found, run all

    return sorted(relevant_tests)


def build_smart_test_command(
    changed_files: List[str],
    project_path: str,
    base_command: str = "pytest",
    fallback_to_all: bool = True,
) -> str:
    """Build a test command that runs only relevant tests.

    Args:
        changed_files: List of changed file paths
        project_path: Root path of the project
        base_command: Base test command (e.g., "pytest", "npm test")
        fallback_to_all: If True, run all tests when no relevant tests found

    Returns:
        Test command string
    """
    relevant = find_relevant_tests(changed_files, project_path)

    if relevant is None:
        # No relevant tests found or couldn't determine
        return base_command if fallback_to_all else ""

    if not relevant:
        return base_command if fallback_to_all else ""

    # Build command based on test runner
    if "pytest" in base_command:
        # pytest can take multiple file paths
        test_files = " ".join(relevant)
        return f"{base_command} {test_files}"
    elif "npm" in base_command or "yarn" in base_command:
        # npm/yarn test with file pattern
        # Most JS test runners support --testPathPattern
        pattern = "|".join(relevant)
        return f"{base_command} -- --testPathPattern=\"{pattern}\""
    elif "cargo" in base_command:
        # Rust - run specific test modules
        # This is approximate; Rust test selection is complex
        return base_command
    else:
        # Unknown runner, just append files
        test_files = " ".join(relevant)
        return f"{base_command} {test_files}"


class SmartVerifier(Verifier):
    """Verifier with smart test selection support.

    Extends the base Verifier to optionally run only tests that are
    relevant to the changed files.
    """

    def __init__(
        self,
        config: VerificationConfig,
        project_path: str,
        changed_files: Optional[List[str]] = None,
        smart_testing: bool = True,
    ):
        super().__init__(config, project_path)
        self.changed_files = changed_files or []
        self.smart_testing = smart_testing
        self._relevant_tests: Optional[List[str]] = None

    def get_relevant_tests(self) -> Optional[List[str]]:
        """Get cached relevant tests, computing if needed."""
        if self._relevant_tests is None and self.changed_files:
            self._relevant_tests = find_relevant_tests(
                self.changed_files,
                self.project_path,
            )
        return self._relevant_tests

    def run_command(self, cmd: VerificationCommand) -> CommandResult:
        """Run command with smart test selection if applicable."""
        # Only apply smart selection to test commands
        if self.smart_testing and self.changed_files and cmd.name == "test":
            relevant = self.get_relevant_tests()
            if relevant:
                # Modify the command to run only relevant tests
                smart_cmd = build_smart_test_command(
                    self.changed_files,
                    self.project_path,
                    cmd.command,
                )
                if smart_cmd != cmd.command:
                    # Create modified command
                    modified_cmd = VerificationCommand(
                        name=f"{cmd.name} (smart: {len(relevant)} files)",
                        command=smart_cmd,
                        working_dir=cmd.working_dir,
                        timeout=cmd.timeout,
                        required=cmd.required,
                        run_on=cmd.run_on,
                    )
                    return super().run_command(modified_cmd)

        return super().run_command(cmd)


# =============================================================================
# Contract Validation
# =============================================================================

@dataclass
class BreakingChange:
    """A breaking change in an interface signature."""
    module: str
    interface_name: str
    before_signature: str
    after_signature: str
    change_type: str = ""  # "removed", "modified", "params_changed"
    details: str = ""

    def format(self) -> str:
        """Format for display."""
        return (
            f"  ✗ {self.module}::{self.interface_name}\n"
            f"    Before: {self.before_signature}\n"
            f"    After:  {self.after_signature}\n"
            f"    Type:   {self.change_type}"
        )


def signatures_compatible(before: str, after: str) -> bool:
    """
    Check if two signatures are compatible.

    Compatible means:
    - Same function/method name
    - Same required parameters (can add optional ones)
    - Same return type (if typed)

    This is a simplified check - real compatibility depends on language.
    """
    if not before or not after:
        return True  # Can't compare empty signatures

    # Exact match is always compatible
    if before == after:
        return True

    # Extract function name (everything before first '(')
    before_name = before.split('(')[0].strip() if '(' in before else before
    after_name = after.split('(')[0].strip() if '(' in after else after

    if before_name != after_name:
        return False  # Name changed = breaking

    # Extract parameters
    def extract_params(sig: str) -> List[str]:
        if '(' not in sig or ')' not in sig:
            return []
        params_str = sig[sig.find('(')+1:sig.rfind(')')]
        if not params_str.strip():
            return []
        # Split by comma, but be careful of nested structures
        params = []
        depth = 0
        current = ""
        for char in params_str:
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
            elif char == ',' and depth == 0:
                params.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            params.append(current.strip())
        return params

    before_params = extract_params(before)
    after_params = extract_params(after)

    # Check required params (those without defaults)
    def is_required(param: str) -> bool:
        # Has no default value
        return '=' not in param and '*' not in param

    before_required = [p for p in before_params if is_required(p)]
    after_required = [p for p in after_params if is_required(p)]

    # All before required params must still exist
    # (simplified: just check count - real check would compare names/types)
    if len(after_required) > len(before_required):
        return False  # Added required params = breaking

    return True


def validate_interface_contracts(
    before_graph: "Graph",
    after_graph: "Graph",
) -> List[BreakingChange]:
    """
    Detect if any interface signatures changed incompatibly.

    Compares interfaces between two versions of a graph to find
    breaking changes that could affect dependent code.

    Args:
        before_graph: Graph before changes
        after_graph: Graph after changes

    Returns:
        List of BreakingChange objects for incompatible changes
    """
    from erirpg.graph import Graph

    breaking = []

    for module_path, before_module in before_graph.modules.items():
        if module_path not in after_graph.modules:
            # Module removed entirely - check if it had public interfaces
            for iface in before_module.interfaces:
                breaking.append(BreakingChange(
                    module=module_path,
                    interface_name=iface.name,
                    before_signature=iface.signature,
                    after_signature="<removed>",
                    change_type="removed",
                    details="Module was removed",
                ))
            continue

        after_module = after_graph.modules[module_path]

        # Build lookup for after interfaces
        after_interfaces = {i.name: i for i in after_module.interfaces}

        for before_iface in before_module.interfaces:
            if before_iface.name not in after_interfaces:
                # Interface removed
                breaking.append(BreakingChange(
                    module=module_path,
                    interface_name=before_iface.name,
                    before_signature=before_iface.signature,
                    after_signature="<removed>",
                    change_type="removed",
                    details="Interface was removed",
                ))
                continue

            after_iface = after_interfaces[before_iface.name]

            # Check signature compatibility
            if not signatures_compatible(before_iface.signature, after_iface.signature):
                # Determine change type
                change_type = "modified"
                if "(" in before_iface.signature and "(" in after_iface.signature:
                    change_type = "params_changed"

                breaking.append(BreakingChange(
                    module=module_path,
                    interface_name=before_iface.name,
                    before_signature=before_iface.signature,
                    after_signature=after_iface.signature,
                    change_type=change_type,
                ))

    return breaking


def format_breaking_changes(changes: List[BreakingChange]) -> str:
    """Format breaking changes for display."""
    if not changes:
        return "✓ No breaking changes detected"

    lines = [
        f"{'═' * 50}",
        f" ⚠️  BREAKING CHANGES DETECTED ({len(changes)})",
        f"{'═' * 50}",
    ]

    for change in changes:
        lines.append(change.format())
        lines.append("")

    lines.append("These changes may break dependent code.")
    lines.append("Review impact zone before proceeding.")

    return "\n".join(lines)
