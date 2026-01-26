"""
UX utilities for EriRPG CLI.

Provides consistent formatting, progress indicators, and clear
next-step guidance across all CLI commands.

Usage:
    from erirpg.ux import print_success, print_error, print_step

    print_success("Operation completed")
    print_error("Something went wrong")
    print_step("Processing files...", current=5, total=10)
"""

from typing import Any, List, Optional
import sys


# =============================================================================
# Status Icons
# =============================================================================

ICONS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "pending": "○",
    "in_progress": "◐",
    "completed": "●",
    "failed": "✗",
    "skipped": "○",
    "paused": "⏸",
    "cancelled": "○",
    "arrow": "→",
    "bullet": "•",
    "check": "✓",
    "cross": "✗",
}

# ANSI color codes (optional, can be disabled)
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}

# Global flag for color support
_use_colors = sys.stdout.isatty()


def set_colors(enabled: bool) -> None:
    """Enable or disable color output."""
    global _use_colors
    _use_colors = enabled


def _color(text: str, color: str) -> str:
    """Apply color if colors are enabled."""
    if _use_colors and color in COLORS:
        return f"{COLORS[color]}{text}{COLORS['reset']}"
    return text


# =============================================================================
# Message Formatting
# =============================================================================

def print_success(message: str) -> None:
    """Print a success message."""
    icon = _color(ICONS["success"], "green")
    print(f"{icon} {message}")


def print_error(message: str, file=sys.stderr) -> None:
    """Print an error message."""
    icon = _color(ICONS["error"], "red")
    print(f"{icon} {message}", file=file)


def print_warning(message: str) -> None:
    """Print a warning message."""
    icon = _color(ICONS["warning"], "yellow")
    print(f"{icon} {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    icon = _color(ICONS["info"], "blue")
    print(f"{icon} {message}")


def print_step(
    message: str,
    current: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """Print a step/progress message.

    Args:
        message: Step description
        current: Current step number
        total: Total steps
    """
    if current is not None and total is not None:
        pct = current / total * 100 if total > 0 else 0
        prefix = f"[{current}/{total}] "
    else:
        prefix = ""

    icon = _color(ICONS["arrow"], "cyan")
    print(f"{icon} {prefix}{message}")


# =============================================================================
# Headers and Sections
# =============================================================================

def print_header(title: str, char: str = "=") -> None:
    """Print a section header."""
    title = _color(title, "bold")
    print(title)
    print(char * len(title.replace(COLORS.get("bold", ""), "").replace(COLORS.get("reset", ""), "")))


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    title = _color(title, "cyan")
    print(f"\n{title}")
    print("-" * len(title.replace(COLORS.get("cyan", ""), "").replace(COLORS.get("reset", ""), "")))


def print_section(title: str, items: List[str]) -> None:
    """Print a section with a title and bullet items."""
    print_subheader(title)
    for item in items:
        print(f"  {ICONS['bullet']} {item}")


# =============================================================================
# Status Formatting
# =============================================================================

def format_status(status: str) -> str:
    """Format a status string with icon and color.

    Args:
        status: Status string (pending, completed, failed, etc.)

    Returns:
        Formatted status string
    """
    icon = ICONS.get(status, "?")
    color = {
        "pending": "dim",
        "in_progress": "cyan",
        "completed": "green",
        "failed": "red",
        "skipped": "dim",
        "paused": "yellow",
        "cancelled": "dim",
    }.get(status, "reset")

    return _color(f"{icon} {status}", color)


def format_step_status(step: Any) -> str:
    """Format a plan step with status indicator.

    Args:
        step: PlanStep object

    Returns:
        Formatted status line
    """
    icon = ICONS.get(step.status, "?")
    color = {
        "pending": "dim",
        "in_progress": "cyan",
        "completed": "green",
        "failed": "red",
        "skipped": "dim",
    }.get(step.status, "reset")

    icon = _color(icon, color)

    risk_badge = ""
    if step.risk in ("high", "critical"):
        risk_badge = _color(f" [{step.risk.upper()}]", "red")

    return f"{icon} {step.order:2}. {step.action}{risk_badge}"


def format_run_status(run: Any) -> str:
    """Format a run record status line.

    Args:
        run: RunRecord object

    Returns:
        Formatted status line
    """
    icon = ICONS.get(run.status, "?")
    color = {
        "pending": "dim",
        "in_progress": "cyan",
        "completed": "green",
        "failed": "red",
        "paused": "yellow",
        "cancelled": "dim",
    }.get(run.status, "reset")

    icon = _color(icon, color)
    return f"{icon} {run.id} ({run.status})"


# =============================================================================
# Progress Bars
# =============================================================================

def format_progress_bar(
    current: int,
    total: int,
    width: int = 30,
    fill: str = "█",
    empty: str = "░",
    show_percent: bool = True,
) -> str:
    """Format a text-based progress bar.

    Args:
        current: Current progress
        total: Total
        width: Bar width
        fill: Fill character
        empty: Empty character
        show_percent: Show percentage

    Returns:
        Formatted progress bar
    """
    if total == 0:
        pct = 0
    else:
        pct = min(1.0, current / total)

    filled = int(width * pct)
    bar = fill * filled + empty * (width - filled)

    if show_percent:
        return f"[{bar}] {current}/{total} ({pct:.0%})"
    return f"[{bar}] {current}/{total}"


def print_progress(
    current: int,
    total: int,
    message: str = "",
    width: int = 30,
) -> None:
    """Print a progress bar with optional message.

    Args:
        current: Current progress
        total: Total
        message: Optional message
        width: Bar width
    """
    bar = format_progress_bar(current, total, width)
    if message:
        print(f"{bar} {message}")
    else:
        print(bar)


# =============================================================================
# Next Steps Guidance
# =============================================================================

def print_next_steps(steps: List[str], title: str = "Next Steps") -> None:
    """Print a numbered list of next steps.

    Args:
        steps: List of step descriptions
        title: Section title
    """
    print_subheader(title)
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")


def format_command_hint(command: str) -> str:
    """Format a command as a copyable hint.

    Args:
        command: Command string

    Returns:
        Formatted hint
    """
    return _color(f"  $ {command}", "dim")


def print_command_hint(description: str, command: str) -> None:
    """Print a command hint with description.

    Args:
        description: What the command does
        command: The command to run
    """
    print(f"  {description}:")
    print(format_command_hint(command))


# =============================================================================
# Tables
# =============================================================================

def print_table(
    headers: List[str],
    rows: List[List[str]],
    min_widths: Optional[List[int]] = None,
) -> None:
    """Print a simple table.

    Args:
        headers: Column headers
        rows: Table rows
        min_widths: Minimum column widths
    """
    if not rows:
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    if min_widths:
        widths = [max(w, mw) for w, mw in zip(widths, min_widths)]

    # Print header
    header_line = "  ".join(
        _color(h.ljust(w), "bold")
        for h, w in zip(headers, widths)
    )
    print(header_line)
    print("-" * sum(widths) + "-" * (len(widths) - 1) * 2)

    # Print rows
    for row in rows:
        row_line = "  ".join(
            str(cell).ljust(w)
            for cell, w in zip(row, widths)
        )
        print(row_line)


# =============================================================================
# Confirmation Prompts
# =============================================================================

def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation.

    Args:
        message: Question to ask
        default: Default answer

    Returns:
        True if confirmed
    """
    if default:
        prompt = f"{message} [Y/n] "
    else:
        prompt = f"{message} [y/N] "

    response = input(prompt).strip().lower()

    if not response:
        return default

    return response in ("y", "yes")


# =============================================================================
# Summary Formatting
# =============================================================================

def print_summary(
    title: str,
    stats: dict,
    status: Optional[str] = None,
) -> None:
    """Print a summary with statistics.

    Args:
        title: Summary title
        stats: Dictionary of stat_name -> value
        status: Optional overall status
    """
    print_header(title)

    if status:
        print(f"Status: {format_status(status)}")
        print()

    max_key_len = max(len(k) for k in stats.keys()) if stats else 0
    for key, value in stats.items():
        print(f"  {key.ljust(max_key_len)}: {value}")


def format_duration(seconds: float) -> str:
    """Format a duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
