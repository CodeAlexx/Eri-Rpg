"""
EriRPG Modes - Three ways to work.

- new: Create new project from scratch
- take: Transplant feature from Project A to Project B
- work: Modify existing project
"""

from erirpg.modes.take import run_take
from erirpg.modes.work import run_work
from erirpg.modes.new import run_new, run_next, QUESTIONS

__all__ = ["run_take", "run_work", "run_new", "run_next", "QUESTIONS"]
